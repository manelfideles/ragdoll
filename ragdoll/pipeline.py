import os
from dataclasses import dataclass

import polars as pl
import pymupdf as pdf
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

EMBEDDING_MODEL = ""
CHAT_MODEL = "gemini-3.5-flash-lite"
LLM_API_KEY = os.getenv("GEMINI_API_KEY")
KEYWORD_SYSTEM_PROMPT = """
Extract keywords from the input: {query}.
Prefer literal terms the corpus is likely to use: {glossary}.
Guidelines:
- Don't augment or generate new ones from the query
- Output 1 to 3 keywords maximum - strictly no more than that
- Drop the question framing
- Reply **only** with the keywords
- Return the text separated by \n - not a simple whitespace or \t.
"""


def llm_client() -> genai.Client:
    client = genai.Client(api_key=LLM_API_KEY)
    return client


def open_document(path: str) -> pdf.Document:
    return pdf.open(path)


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    query: str

    @property
    def normalized_query(self) -> str:
        """
        The normalized query.
        """
        return self.query.strip().lower()

    def get_keywords(
        self,
        client: genai.Client,
        glossary: dict[str, str],
        system_prompt: str = KEYWORD_SYSTEM_PROMPT,
    ) -> list[str]:
        """
        The most useful keywords for searching a document.
        Short phrases the document is likely to contain,
        not necessarily the literal words of the question.
        """
        # Calls a LLM to fetch the keywords
        prompt = system_prompt.format(
            query=self.normalized_query,
            glossary=glossary,
        )
        contents = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
        ).text
        keywords = contents.split("\n")[:3]
        return keywords


def parse_query(raw_query: str, client: genai.Client) -> list[str]:
    query = ParsedQuery(raw_query)
    keywords = query.get_keywords(client, glossary={})
    return keywords


def parse_document(document: pdf.Document) -> pl.DataFrame:
    """
    Outputs a dataframe where each row contains the text
    and positioning metadata for each line in the document.
    This doesn’t:
    - Detect tables (Table 1 page 4, Table 3 page 9 flatten into plain lines);
    - Reconstruct headings, footnotes, or cross-references;
    - Handle multi-column layouts.
    """
    data = []
    for page_idx, page in enumerate(document):
        blocks = page.get_text("dict").get("blocks", [])
        line_num = 0
        for block in blocks:
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            for line in lines:
                spans = line.get("spans", [])
                if not spans:
                    continue

                text = "".join(s["text"] for s in spans)
                rect = pdf.Rect(spans[0]["bbox"])
                for span in spans[1:]:
                    rect |= pdf.Rect(span["bbox"])

                data.append(
                    {
                        "page_num": page_idx + 1,
                        "line_num": line_num + 1,
                        "text": text,
                        "x0": float(rect.x0),
                        "y0": float(rect.y0),
                        "x1": float(rect.x1),
                        "y1": float(rect.y1),
                    }
                )
                line_num += 1
    return pl.DataFrame(data)


def get_document_pages(document_lines: pl.DataFrame) -> pl.DataFrame:
    """
    Returns the contents of each page, concatenated.
    """
    return document_lines.group_by(
        "page_num",
        maintain_order=True,
    ).agg(pl.col("text").str.join(" ").str.to_lowercase())


def keyword_retrieval(
    pages: pl.DataFrame,
    lines: pl.DataFrame,
    keywords: list[str],
    k: int = 5,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Applies simple keyword matching
    to fetch the `k` most relevant pages in the document.
    """
    counts = []
    for keyword in keywords:
        matches = pages.with_columns(
            match_count=pl.col("text").str.count_matches(
                keyword,
                literal=True,
            ),
            matched_keyword=pl.lit(keyword),
        ).filter(pl.col("match_count") > 0)
        if matches.height:
            counts.append(matches)

    if counts:
        retrieved_pages: pl.DataFrame = (
            pl.concat(counts).sort(by="match_count", descending=True).head(k)
        )
        retrieved_lines = lines.filter(
            pl.col("page_num").is_in(retrieved_pages.get_column("page_num").implode())
        )
        return (retrieved_pages, retrieved_lines)
    return pl.DataFrame(), pl.DataFrame()


class Answer(BaseModel):
    text: str = Field(...)
    start_page_num: int | None
    start_line_num: int | None
    end_page_num: int | None
    end_line_num: int | None
    confidence: float = Field(..., ge=0.0, le=1.0)
    justification: str = Field(...)
    quotes: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)

    def __str__(self):
        return f"""
Answer: {self.text}
Confidence: {self.confidence}
Justification: {self.justification}
Evidence: {self.quotes}
Coordinates: {self.start_line_num} (p. {self.start_page_num}) - {self.end_line_num} (p. {self.end_page_num})
"""


def llm_answer(query: str, relevant_lines: str, client: genai.Client) -> Answer:
    resp = client.models.generate_content(
        model=CHAT_MODEL,
        contents=f"Lines:\n{relevant_lines}\n\nQuestion:\n{query}\n\nPick a contiguous evidence span.",
        config=genai.types.GenerateContentConfig(
            system_instruction="Answer using **only** the provided lines.",
            response_mime_type="application/json",
            response_schema=Answer,
            temperature=0,
        ),
    )
    return resp.parsed


def pipeline(query: str, path: str):
    client = llm_client()
    keywords = parse_query(query, client)
    print()
    print(" --- Keywords:", keywords, "---")
    # keywords = ["feeling the water", "learning how to swim"]
    doc = open_document(path)
    lines = parse_document(doc)
    pages = get_document_pages(lines)
    _, relevant_lines = keyword_retrieval(pages, lines, keywords)
    print(relevant_lines)
    answer = llm_answer(query, relevant_lines, client)
    print(answer)


if __name__ == "__main__":
    query = "What does feeling the water mean in the context of learning how to swim?"
    path = "/Users/fideles/Desktop/learning/ragdoll/corpus/swim-smooth.pdf"
    pipeline(query, path)
