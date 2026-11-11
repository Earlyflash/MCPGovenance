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
    data = triage(Path(a.repo), policy, a.base, a.head, _labels(a.labels), a.full_scan, a.stage or None)
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
    data = triage(repo, policy, a.base, a.head, _labels(a.labels), a.full_scan, a.stage or None)
    a.full_scan = a.full_scan or data["full_scan"]
    triage_path = out / "triage.json"
    triage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    for d in data["domains"]:
        run_and_write(d, ROOT, repo, triage_path, out, a.full_scan)
    verdict = _govern(a.policy, triage_path, out, repo, out, False, None, None)
    print((out / "comment.md").read_text(encoding="utf-8"))
    return 1 if verdict["verdict"] == "fail" else 0


def cmd_docs(a: argparse.Namespace) -> int:
    from . import docs_gen
    if a.check:
        bad = docs_gen.stale(ROOT)
        for p in bad:
            print(f"out of date: {p.relative_to(ROOT)} (run: python -m governance docs)")
        return 1 if bad else 0
    for p in docs_gen.write(ROOT):
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


def cmd_ask(a: argparse.Namespace) -> int:
    """Ask a domain's knowledge layer a question the way an agent would. The call is recorded as demand."""
    import asyncio
    from .mcp_client import open_domain

    async def go() -> Any:
        async with open_domain(a.domain, ROOT, caller=a.caller) as mcp:
            if a.technology:
                return await mcp.call("check_technology", name=a.question, ecosystem=a.ecosystem or None)
            return await mcp.call("get_guidance", query=a.question)

    print(json.dumps(asyncio.run(go()), indent=2))
    return 0


def cmd_demand(a: argparse.Namespace) -> int:
    from . import demand
    try:
        rows = demand.load([Path(p) for p in a.logs])
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    summary = demand.summarise(rows, a.top)
    text = json.dumps(summary, indent=2) if a.json else demand.render(summary)
    print(text)
    if a.out:
        Path(a.out).write_text(demand.render(summary), encoding="utf-8")
    if a.html:
        Path(a.html).write_text(demand.render_html(summary), encoding="utf-8")
        print(f"wrote {a.html}", file=sys.stderr)
    return 0


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
    t.add_argument("--stage", default=os.environ.get("GOV_STAGE", ""), help="stage from a trusted setting: scan, pilot or production")
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
    l.add_argument("--stage", default="", help="stage from a trusted setting: scan, pilot or production")
    l.add_argument("--policy", default=default_policy)
    l.add_argument("--out", default=".governance-out")
    l.set_defaults(fn=cmd_local)

    d = sub.add_parser("docs", help="regenerate the guardrail documentation from the rules")
    d.add_argument("--check", action="store_true", help="fail if the generated pages are out of date")
    d.set_defaults(fn=cmd_docs)

    q = sub.add_parser("ask", help="ask a domain's guidance a question, as an agent would (recorded as demand when GOVERNANCE_DEMAND_LOG is set)")
    q.add_argument("--domain", required=True)
    q.add_argument("--caller", default="cli", help="label for who is asking, for example copilot or a team name")
    q.add_argument("--technology", action="store_true", help="ask whether a technology is approved (enterprise-alignment)")
    q.add_argument("--ecosystem", default="", help="pip, npm or docker (with --technology)")
    q.add_argument("question")
    q.set_defaults(fn=cmd_ask)

    dm = sub.add_parser("demand", help="report what has been asked of the knowledge layer, and what had no answer")
    dm.add_argument("logs", nargs="+", help="demand*.jsonl files or folders containing them")
    dm.add_argument("--top", type=int, default=10)
    dm.add_argument("--json", action="store_true")
    dm.add_argument("--out", help="also write the markdown report here")
    dm.add_argument("--html", help="write a self-contained, visual HTML report here")
    dm.set_defaults(fn=cmd_demand)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
