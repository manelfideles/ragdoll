"""The ragdoll command line.

Stage one of ingestion only: parse each document, count its tokens, and report the
routing decision for the project as a whole. No chunking and no indexing yet, because
neither can be scored until there is a golden set to score them against.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ragdoll import golden as golden_set
from ragdoll import routing, tokens
from ragdoll.cache import IngestCache
from ragdoll.config import load_env
from ragdoll.parse import find_pdfs, parse_pdf

app = typer.Typer(add_completion=False, help="ragdoll — build and measure RAG pipelines locally.")
golden_app = typer.Typer(
    add_completion=False, help="Build and review the golden set of scoring questions."
)
app.add_typer(golden_app, name="golden")
console = Console()


@app.callback()
def main() -> None:
    """Load local configuration before any command runs."""
    load_env()


@dataclass(frozen=True, slots=True)
class DocumentStat:
    """One document's measurements, whether freshly computed or read from cache."""

    path: Path
    pages: int
    chars: int
    tokens: int
    exact: bool
    cached: bool

    @property
    def tokens_per_page(self) -> int | None:
        return self.tokens // self.pages if self.pages else None


@app.command()
def ingest(
    directory: Annotated[
        Path, typer.Argument(help="Directory of PDFs to treat as one project.")
    ] = Path("corpus"),
    offline: Annotated[
        bool, typer.Option("--offline", help="Skip the API and use approximate token counts.")
    ] = False,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Re-parse and re-count everything.")
    ] = False,
) -> None:
    """Parse a project's documents, count tokens, and print the routing decision."""
    if not directory.is_dir():
        console.print(f"[red]No such directory:[/red] {directory}")
        raise typer.Exit(1)

    pdfs = find_pdfs(directory)
    if not pdfs:
        console.print(f"[yellow]No PDFs found in[/yellow] {directory}")
        raise typer.Exit(1)

    if not offline and not tokens.has_credentials():
        console.print(
            "[yellow]No ANTHROPIC_API_KEY found.[/yellow] Falling back to approximate counts.\n"
            "Approximate counts must not decide a route. Set a key, or pass --offline to "
            "silence this.\n"
        )

    cache = IngestCache.load(Path.cwd())
    stats: list[DocumentStat] = []

    for pdf in pdfs:
        cached = None if no_cache else cache.get(pdf)
        if cached is not None:
            stats.append(
                DocumentStat(
                    path=pdf,
                    pages=int(cached["pages"]),
                    chars=int(cached["chars"]),
                    tokens=int(cached["tokens"]),
                    exact=bool(cached["exact"]),
                    cached=True,
                )
            )
            continue

        with console.status(f"parsing {pdf.name}"):
            document = parse_pdf(pdf)
        with console.status(f"counting tokens in {pdf.name}"):
            count = tokens.count_or_estimate(document.text, allow_api=not offline)

        cache.put(
            pdf,
            pages=document.pages,
            chars=document.chars,
            tokens=count.tokens,
            exact=count.exact,
        )
        stats.append(
            DocumentStat(
                path=pdf,
                pages=document.pages,
                chars=document.chars,
                tokens=count.tokens,
                exact=count.exact,
                cached=False,
            )
        )

    cache.save()
    _report(directory, stats)


def _report(directory: Path, stats: list[DocumentStat]) -> None:
    table = Table(title=f"Project: {directory}", title_justify="left", header_style="bold")
    table.add_column("Document")
    table.add_column("Pages", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Tok/page", justify="right")
    table.add_column("Alone", justify="left")

    total = sum(stat.tokens for stat in stats)
    all_exact = all(stat.exact for stat in stats)

    for stat in stats:
        alone = routing.decide(stat.tokens)
        colour = "cyan" if alone.route is routing.Route.STUFF else "magenta"
        per_page = stat.tokens_per_page
        table.add_row(
            stat.path.name[:44],
            f"{stat.pages:,}",
            f"{stat.tokens:,}" if stat.exact else f"~{stat.tokens:,}",
            f"{per_page:,}" if per_page is not None else "-",
            f"[{colour}]{alone.route}[/{colour}]",
        )

    console.print()
    console.print(table)

    decision = routing.decide(total)
    verdict = "cyan" if decision.route is routing.Route.STUFF else "magenta"
    suffix = "" if all_exact else " (approximate)"
    over = "  (over)" if decision.headroom < 0 else ""
    console.print()
    console.print(f"  Whole project   [bold]{total:,}[/bold] tokens{suffix}")
    console.print(f"  Threshold       {decision.threshold:,}")
    console.print(f"  Headroom        {decision.headroom:,}{over}")
    console.print(f"  Route           [bold {verdict}]{decision.route.upper()}[/bold {verdict}]")
    console.print(f"  Because         {decision.reason}")
    if not all_exact:
        console.print(
            "\n  [yellow]These counts are approximate, so this route is a guess.[/yellow]"
        )
    console.print()


@app.command()
def route(
    total_tokens: Annotated[int, typer.Argument(help="Project size in tokens.")],
    indexed: Annotated[
        bool, typer.Option("--indexed", help="Project already has an index (applies hysteresis).")
    ] = False,
) -> None:
    """Ask the routing rule a hypothetical. Useful for probing the boundary."""
    decision = routing.decide(total_tokens, already_indexed=indexed)
    console.print(f"[bold]{decision.route.upper()}[/bold] — {decision.reason}")
    console.print(f"headroom: {decision.headroom:,}")


@golden_app.command("generate")
def golden_generate(
    directory: Annotated[
        Path, typer.Argument(help="Directory of PDFs to sample pages from.")
    ] = Path("corpus"),
    limit: Annotated[
        int, typer.Option("--limit", help="How many pages to take from the sample order.")
    ] = golden_set.TARGET_ACCEPTED,
    seed: Annotated[int, typer.Option("--seed", help="Sampling seed.")] = golden_set.DEFAULT_SEED,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print the sampled pages and stop. No API calls.")
    ] = False,
) -> None:
    """Sample pages and write question candidates. Never writes the reviewed set."""
    if not directory.is_dir():
        console.print(f"[red]No such directory:[/red] {directory}")
        raise typer.Exit(1)

    with console.status(f"parsing {directory}"):
        pages_by_document = golden_set.collect_pages(directory)
    if not pages_by_document:
        console.print(f"[yellow]No PDFs found in[/yellow] {directory}")
        raise typer.Exit(1)

    eligible = {name: golden_set.eligible_pages(pages) for name, pages in pages_by_document.items()}
    order = golden_set.sample_pages(eligible, seed=seed)
    chosen = order[:limit]

    if dry_run:
        _report_sample(pages_by_document, eligible, order, chosen, seed)
        return

    if not tokens.has_credentials():
        console.print(
            "[red]No ANTHROPIC_API_KEY found.[/red] Generation needs the API. "
            "Use --dry-run to see the sample without it."
        )
        raise typer.Exit(1)

    from anthropic import Anthropic

    target = golden_set.candidates_path()
    console.print(f"\n  Writing to      [bold]{target}[/bold]")
    console.print(f"  Model           {golden_set.GENERATOR_MODEL}")
    console.print(f"  Prompt          {golden_set.PROMPT_VERSION}\n")

    kept: list[golden_set.Candidate] = []
    dropped: list[golden_set.Outcome] = []
    client = Anthropic()

    for position, outcome in enumerate(
        golden_set.generate(client, pages_by_document, chosen, seed=seed, path=target), start=1
    ):
        prefix = (
            f"  {position:>3}/{len(chosen)}  {outcome.ref.document[:28]:<28} p{outcome.ref.page:<5}"
        )
        if outcome.candidate is None:
            dropped.append(outcome)
            console.print(f"{prefix} [yellow]dropped — {outcome.reason}[/yellow]")
            continue
        kept.append(outcome.candidate)
        marks = []
        if outcome.candidate.match_count > 1:
            marks.append(f"[magenta]{outcome.candidate.match_count} matches[/magenta]")
        if outcome.dehyphenated:
            marks.append("[cyan]rejoined[/cyan]")
        suffix = ("  " + " ".join(marks)) if marks else ""
        console.print(
            f"{prefix} [green]kept[/green] echo {outcome.candidate.echo_score:.2f}{suffix}"
        )
        console.print(f"        [dim]Q:[/dim] {outcome.candidate.question}")

    console.print()
    console.print(f"  Kept            [bold]{len(kept)}[/bold] of {len(chosen)}")
    console.print(f"  Dropped         {len(dropped)}")
    console.print()


def _report_sample(
    pages_by_document: dict[str, list[str]],
    eligible: dict[str, list[int]],
    order: list[golden_set.PageRef],
    chosen: list[golden_set.PageRef],
    seed: int,
) -> None:
    strata = Table(title="Eligible pages per document", title_justify="left", header_style="bold")
    strata.add_column("Document")
    strata.add_column("Pages", justify="right")
    strata.add_column("Eligible", justify="right")
    strata.add_column("Skipped", justify="right")
    strata.add_column("Sampled", justify="right")

    for name in sorted(pages_by_document):
        total = len(pages_by_document[name])
        usable = len(eligible[name])
        taken = sum(1 for ref in chosen if ref.document == name)
        strata.add_row(name[:44], f"{total:,}", f"{usable:,}", f"{total - usable:,}", f"{taken:,}")

    console.print()
    console.print(strata)

    sample = Table(title=f"Sample (seed {seed})", title_justify="left", header_style="bold")
    sample.add_column("#", justify="right")
    sample.add_column("Document")
    sample.add_column("Page", justify="right")
    sample.add_column("Chars", justify="right")

    for position, ref in enumerate(chosen, start=1):
        text = pages_by_document[ref.document][ref.page - 1]
        sample.add_row(str(position), ref.document[:44], str(ref.page), f"{len(text):,}")

    console.print()
    console.print(sample)
    console.print()
    console.print(f"  Sample order    {len(order):,} pages, of which {len(chosen):,} taken")
    console.print(f"  Distinct        {len({(r.document, r.page) for r in chosen}):,}")
    console.print()


if __name__ == "__main__":
    app()
