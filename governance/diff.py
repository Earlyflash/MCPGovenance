"""Work out what a PR changed, including which line numbers it added, using plain git.

Reviewers use ``added_lines`` so a PR is only judged on what it changed ("diff mode").
``added_lines is None`` means "the whole file counts" (used for full scans).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass
class ChangedFile:
    path: str
    status: str  # added | modified | deleted
    added_lines: list[int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_new_line(self, line: int | None) -> bool:
        if self.added_lines is None:
            return True
        return line is not None and line in set(self.added_lines)


def _path_from_header(rest: str) -> str:
    # "a/<path> b/<path>" - with --no-renames both halves are identical.
    length = (len(rest) - 5) // 2
    if length > 0 and rest == f"a/{rest[2:2 + length]} b/{rest[2:2 + length]}":
        return rest[2:2 + length]
    m = re.match(r'^"?a/(.*?)"? "?b/(.*?)"?$', rest)
    return m.group(2) if m else ""


def parse_unified_diff(text: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    cur: ChangedFile | None = None
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            path = _path_from_header(raw[len("diff --git "):])
            cur = ChangedFile(path=path, status="modified", added_lines=[]) if path else None
            if cur:
                files.append(cur)
        elif cur is None:
            continue
        elif raw.startswith("new file mode"):
            cur.status = "added"
        elif raw.startswith("deleted file mode"):
            cur.status = "deleted"
        elif raw.startswith("@@"):
            m = HUNK.match(raw)
            if m and cur.added_lines is not None:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                cur.added_lines.extend(range(start, start + count))
    return files


def _git(repo: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def git_changed_files(repo: Path, base: str, head: str) -> list[ChangedFile]:
    opts = ["diff", "--unified=0", "--no-color", "--no-ext-diff", "--no-renames"]
    try:
        out = _git(repo, *opts, f"{base}...{head}")
    except RuntimeError:
        out = _git(repo, *opts, base, head)  # no merge base (shallow clone): plain comparison
    return parse_unified_diff(out)


def all_files(repo: Path) -> list[ChangedFile]:
    try:
        names = [n for n in _git(repo, "ls-files").splitlines() if n]
    except RuntimeError:
        names = [
            p.relative_to(repo).as_posix()
            for p in repo.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(repo).parts
        ]
    return [ChangedFile(path=n, status="added", added_lines=None) for n in names]
