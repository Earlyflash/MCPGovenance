"""Decide which domain reviewers a PR needs, from the changed paths and labels."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .diff import ChangedFile, all_files, git_changed_files
from .globs import match_any


def triage(
    repo: Path,
    policy: dict[str, Any],
    base: str | None = None,
    head: str | None = None,
    labels: list[str] | None = None,
    full_scan: bool = False,
) -> dict[str, Any]:
    labels = labels or []
    if full_scan:
        files = all_files(repo)
    else:
        if not base or not head:
            raise ValueError("base and head are required unless full_scan is set")
        files = git_changed_files(repo, base, head)

    ignore = policy.get("ignore_paths", [])
    files = [f for f in files if not match_any(f.path, ignore)]
    live = [f for f in files if f.status != "deleted"]

    domains: list[str] = []
    for name, cfg in policy["domains"].items():
        cfg = cfg or {}
        by_path = any(match_any(f.path, cfg.get("paths", [])) for f in live)
        by_label = bool(set(labels) & set(cfg.get("labels", [])))
        if cfg.get("always") or by_path or by_label:
            domains.append(name)

    return {
        "base": base,
        "head": head,
        "labels": labels,
        "full_scan": full_scan,
        "domains": domains,
        "files": [f.to_dict() for f in files],
    }


def files_from_triage(data: dict[str, Any]) -> list[ChangedFile]:
    return [ChangedFile(**f) for f in data["files"]]
