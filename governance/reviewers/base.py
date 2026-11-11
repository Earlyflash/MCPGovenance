from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from ..diff import ChangedFile
from ..globs import match_any
from ..mcp_client import DomainClient

MAX_FILE_BYTES = 1_000_000
MAX_LINE_CHARS = 2_000


@dataclass
class Hit:
    """A raw detection. The runner turns it into a Finding using the domain's MCP guidance."""

    rule_id: str
    file: str | None
    line: int | None
    evidence: str = ""
    detail: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class Context:
    def __init__(self, repo: Path, files: list[ChangedFile], full: bool, mcp: DomainClient, base: str | None = None):
        self.repo = Path(repo).resolve()
        self.files = files
        self.full = full
        self.mcp = mcp
        self.base = base
        self._by_path = {f.path: f for f in files}

    def base_text(self, path: str) -> str | None:
        """The file as it was at the PR's base commit, or None (new file, full scan, or unavailable)."""
        if self.full or not self.base:
            return None
        res = subprocess.run(["git", "show", f"{self.base}:{path}"], cwd=self.repo, capture_output=True, text=True, check=False)
        return res.stdout if res.returncode == 0 else None

    def live_files(self, patterns: list[str] | None = None) -> list[ChangedFile]:
        out = [f for f in self.files if f.status != "deleted"]
        if patterns is not None:
            out = [f for f in out if match_any(f.path, patterns)]
        return out

    def read(self, f: ChangedFile) -> str | None:
        """Read a changed file as text. Returns None for symlinks, binary, oversized or unreadable
        files, and for anything that resolves outside the repo. PR content is untrusted input."""
        p = (self.repo / f.path)
        try:
            if p.is_symlink() or not p.is_file():
                return None
            resolved = p.resolve()
            if self.repo not in resolved.parents:
                return None
            if resolved.stat().st_size > MAX_FILE_BYTES:
                return None
            return resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def lines(self, f: ChangedFile) -> Iterator[tuple[int, str]]:
        text = self.read(f)
        if text is None:
            return
        for n, line in enumerate(text.splitlines(), start=1):
            if len(line) <= MAX_LINE_CHARS:
                yield n, line

    def is_new(self, path: str | None, line: int | None) -> bool:
        if self.full or path is None:
            return True
        f = self._by_path.get(path)
        return bool(f and f.is_new_line(line))

    def keep(self, hit: Hit) -> bool:
        return self.is_new(hit.file, hit.line)
