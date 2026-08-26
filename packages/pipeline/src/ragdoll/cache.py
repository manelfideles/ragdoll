"""A tiny on-disk cache for parse and count results.

Parsing 613 pages takes real seconds and counting its tokens costs a real API call.
Neither answer changes unless the file does, so both are cached under ``.ragdoll/``
in the project root and keyed by the file's size and modification time.

This is not a clever cache. It is here because the weekly budget for this project is
small, and re-parsing the same four books every run would spend it on nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CACHE_DIRNAME = ".ragdoll"
CACHE_FILENAME = "ingest-cache.json"


def _fingerprint(path: Path) -> str:
    """Identity of a file's contents, cheaply. Size plus modification time."""
    stat = path.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}"


@dataclass(slots=True)
class IngestCache:
    root: Path
    _data: dict[str, Any]

    @classmethod
    def load(cls, root: Path) -> IngestCache:
        file = root / CACHE_DIRNAME / CACHE_FILENAME
        if file.exists():
            try:
                return cls(root=root, _data=json.loads(file.read_text()))
            except (json.JSONDecodeError, OSError):
                pass  # a corrupt cache is not worth a crash; rebuild it
        return cls(root=root, _data={})

    def save(self) -> None:
        directory = self.root / CACHE_DIRNAME
        directory.mkdir(parents=True, exist_ok=True)
        (directory / CACHE_FILENAME).write_text(json.dumps(self._data, indent=2, sort_keys=True))

    def get(self, path: Path) -> dict[str, Any] | None:
        entry = self._data.get(str(path))
        if entry is None or entry.get("fingerprint") != _fingerprint(path):
            return None
        return entry

    def put(self, path: Path, *, pages: int, chars: int, tokens: int, exact: bool) -> None:
        self._data[str(path)] = {
            "fingerprint": _fingerprint(path),
            "pages": pages,
            "chars": chars,
            "tokens": tokens,
            "exact": exact,
        }
