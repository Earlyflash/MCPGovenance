"""Small gitignore-style glob matching.

- A pattern with no "/" matches the file's base name at any depth (``*.html``, ``Dockerfile*``).
- A pattern with a "/" is anchored at the repo root. ``**/`` matches any number of directories
  (including none), ``**`` matches anything, ``*`` and ``?`` never cross a "/".
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable


@lru_cache(maxsize=1024)
def _compile(pattern: str) -> re.Pattern[str]:
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def match(path: str, pattern: str) -> bool:
    if path.startswith("./"):
        path = path[2:]
    if "/" not in pattern:
        return bool(_compile(pattern).match(path.rsplit("/", 1)[-1]))
    return bool(_compile(pattern).match(path))


def match_any(path: str, patterns: Iterable[str]) -> bool:
    return any(match(path, p) for p in patterns)
