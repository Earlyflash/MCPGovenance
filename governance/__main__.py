"""CLI: python -m governance {triage,review,govern,local}"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import github_api
from .govern import govern, load_waivers, load_waivers_at
from .policy import load_policy
from .render import MARKER, render_comment
from .review import run_and_write
from .triage import triage

ROOT = Path(__file__).resolve().parent.parent


def _github_output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for k, v in values.items():
                fh.write(f"{k}={v}\n")


def _labels(raw: str | None) -> list[str]:
    return [x.strip() for x in (raw or "").split(",") if x.strip()]


def cmd_triage(a: argparse.Namespace) -> int:
    policy = load_policy(a.policy)
    data = triage(Path(a.repo), policy, a.base, a.head, _labels(a.labels), a.full_scan)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"changed files: {len(data['files'])}; domains: {data['domains'] or 'none'}")
    _github_output(domains=json.dumps(data["domains"]), applies=str(bool(data["domains"])).lower())
    return 0


def cmd_review(a: argparse.Namespace) -> int:
    result = run_and_write(a.domain, ROOT, Path(a.repo), Path(a.triage), Path(a.out), a.full_scan)
    print(f"{a.domain}: status={result.status} findings={len(result.findings)}")
    return 0 if result.status == "ok" else 1


def _govern(a_policy: str, triage_path: Path, results: Path, repo: Path, out: Path,
            post: bool, pr: int | None, slug: str | None, today=None) -> dict[str, Any]:
    policy = load_policy(a_policy)
    triage_data = json.loads(triage_path.read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN", "")
    waivers = load_waivers(repo / policy["waivers"]["file"])
    approvals: set[str] | None = None
    if policy["waivers"]["require_approval"] and waivers and token and slug and pr:
        try:
            approvals = github_api.approvers(slug, pr, token)
        except github_api.GitHubError as exc:
            print(f"warning: could not read PR approvals: {exc}", file=sys.stderr)
    base_waivers = None if triage_data.get("full_scan") else load_waivers_at(repo, triage_data.get("base"), policy["waivers"]["file"])
    verdict = govern(policy, triage_data, results, waivers, approvals, today, base_waivers)
    server, run_id = os.environ.get("GITHUB_SERVER_URL", "https://github.com"), os.environ.get("GITHUB_RUN_ID")
    run_url = f"{server}/{slug}/actions/runs/{run_id}" if slug and run_id else ""
    comment = render_comment(verdict, {"run_url": run_url, "head": (triage_data.get("head") or "")[:7]})
    out.mkdir(parents=True, exist_ok=True)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    (out / "comment.md").write_text(comment, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(comment + "\n")
    if post and token and slug and pr:
        try:
            print(f"PR comment {github_api.upsert_comment(slug, pr, comment, token, MARKER)}")
        except github_api.GitHubError as exc:  # the check result is the source of truth; the comment is a convenience
            print(f"warning: could not post PR comment: {exc}", file=sys.stderr)
    _github_output(verdict=verdict["verdict"])
    return verdict


def cmd_govern(a: argparse.Namespace) -> int:
    pr = int(a.pr) if a.pr else None
    verdict = _govern(a.policy, Path(a.triage), Path(a.results), Path(a.repo), Path(a.out),
                      a.post_comment, pr, a.github_repository)
    c = verdict["counts"]
    print(f"verdict={verdict['verdict']} block={c['block']} warn={c['warn']} info={c['info']} waived={c['waived']}")
    return 1 if verdict["verdict"] == "fail" else 0


def cmd_local(a: argparse.Namespace) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    repo = Path(a.repo).resolve()
    policy = load_policy(a.policy)
    data = triage(repo, policy, a.base, a.head, _labels(a.labels), a.full_scan)
    triage_path = out / "triage.json"
    triage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    for d in data["domains"]:
        run_and_write(d, ROOT, repo, triage_path, out, a.full_scan)
    verdict = _govern(a.policy, triage_path, out, repo, out, False, None, None)
    print((out / "comment.md").read_text(encoding="utf-8"))
    return 1 if verdict["verdict"] == "fail" else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="governance")
    sub = p.add_subparsers(dest="cmd", required=True)
    default_policy = str(ROOT / "policy.yml")

    t = sub.add_parser("triage", help="decide which domains a change needs")
    t.add_argument("--repo", default=".")
    t.add_argument("--base")
    t.add_argument("--head")
    t.add_argument("--labels", default="")
    t.add_argument("--full-scan", action="store_true")
    t.add_argument("--policy", default=default_policy)
    t.add_argument("--out", default=".governance-out/triage.json")
    t.set_defaults(fn=cmd_triage)

    r = sub.add_parser("review", help="run one domain reviewer")
    r.add_argument("--domain", required=True)
    r.add_argument("--repo", default=".")
    r.add_argument("--triage", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--full-scan", action="store_true")
    r.set_defaults(fn=cmd_review)

    g = sub.add_parser("govern", help="collate findings into one verdict")
    g.add_argument("--policy", default=default_policy)
    g.add_argument("--triage", required=True)
    g.add_argument("--results", required=True)
    g.add_argument("--repo", default=".")
    g.add_argument("--out", required=True)
    g.add_argument("--pr")
    g.add_argument("--github-repository", default=os.environ.get("GITHUB_REPOSITORY"))
    g.add_argument("--post-comment", action="store_true")
    g.set_defaults(fn=cmd_govern)

    l = sub.add_parser("local", help="run the whole pipeline locally against a git repo")
    l.add_argument("--repo", default=".")
    l.add_argument("--base")
    l.add_argument("--head", default="HEAD")
    l.add_argument("--labels", default="")
    l.add_argument("--full-scan", action="store_true")
    l.add_argument("--policy", default=default_policy)
    l.add_argument("--out", default=".governance-out")
    l.set_defaults(fn=cmd_local)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
