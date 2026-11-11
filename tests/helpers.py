from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from governance.__main__ import _govern
from governance.policy import load_policy
from governance.review import run_and_write
from governance.triage import triage

ROOT = Path(__file__).resolve().parent.parent


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def write_files(repo: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def make_pr(tmp_path: Path, base: dict[str, str], pr: dict[str, str], delete: tuple[str, ...] = ()) -> tuple[Path, str, str]:
    """Create a git repo with a base commit and a PR commit. Returns (repo, base_sha, head_sha)."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "tester")
    git(repo, "config", "commit.gpgsign", "false")
    write_files(repo, {"README.md": "# demo\n", **base})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base_sha = git(repo, "rev-parse", "HEAD")
    write_files(repo, pr)
    for rel in delete:
        (repo / rel).unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "pr")
    return repo, base_sha, git(repo, "rev-parse", "HEAD")


def pipeline(
    repo: Path,
    base: str | None,
    head: str | None,
    out: Path,
    policy: Path | None = None,
    labels: list[str] | None = None,
    full: bool = False,
    today: dt.date | None = None,
) -> dict[str, Any]:
    policy_path = Path(policy or ROOT / "policy.yml")
    pol = load_policy(policy_path)
    data = triage(repo, pol, base, head, labels or [], full)
    out.mkdir(parents=True, exist_ok=True)
    tp = out / "triage.json"
    tp.write_text(json.dumps(data), encoding="utf-8")
    for d in data["domains"]:
        run_and_write(d, ROOT, repo, tp, out, full)
    return _govern(str(policy_path), tp, out, repo, out, False, None, None, today)


def rule_ids(verdict: dict[str, Any], domain: str | None = None, include_waived: bool = True) -> set[str]:
    return {
        f["rule_id"] for f in verdict["findings"]
        if (domain is None or f["domain"] == domain) and (include_waived or not f["waived"])
    }
