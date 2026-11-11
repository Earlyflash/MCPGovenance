"""The demand layer: a record of what people and agents ask the knowledge layer for.

Every domain MCP server can append one small JSON line per tool call to the file named by
``GOVERNANCE_DEMAND_LOG``. With the variable unset nothing is written. The report turns those lines into
a ranked backlog: what is asked often, and above all what is asked but not answered (a gap in the guidance).

What is recorded: when, which domain and tool, who asked (a caller label), the repo and stage if known, the
question (rule id, topic or technology name), and whether the server had an answer. Never file contents.
Callers named in ``AUTOMATED`` (our own reviewers) are shown separately: they are not demand.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

LOG_ENV = "GOVERNANCE_DEMAND_LOG"
CONTEXT_ENVS = ("GOVERNANCE_CALLER", "GOVERNANCE_REPO", "GOVERNANCE_STAGE")
AUTOMATED = {"reviewer"}
QUESTION_ARGS = ("query", "rule_id", "name", "status", "severity", "stage")


def _question(args: dict[str, Any]) -> str:
    parts = [str(args[k]) for k in QUESTION_ARGS if args.get(k)]
    return " / ".join(parts)[:200]


def _answered(tool: str, result: Any) -> bool:
    if not isinstance(result, dict):
        return bool(result)
    if result.get("error"):
        return False
    if "matches" in result:
        return bool(result["matches"])
    if "found" in result:
        return bool(result["found"])
    return True


def _matched(result: Any) -> list[str]:
    if isinstance(result, dict):
        if "matches" in result:
            return [m["id"] for m in result["matches"]]
        if result.get("id"):
            return [result["id"]]
        if result.get("rule_id"):
            return [result["rule_id"]]
    return []


def record(domain: str, tool: str, args: dict[str, Any], result_text: str, now: dt.datetime | None = None) -> None:
    """Append one record. Never raises: losing a demand record must not break an answer."""
    path = os.environ.get(LOG_ENV)
    if not path:
        return
    try:
        try:
            result = json.loads(result_text)
        except (TypeError, ValueError):
            result = None
        row = {
            "ts": (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "domain": domain,
            "tool": tool,
            "question": _question(args),
            "answered": _answered(tool, result),
            "matched": _matched(result),
            "caller": os.environ.get("GOVERNANCE_CALLER", "unknown"),
            "repo": os.environ.get("GOVERNANCE_REPO", ""),
            "stage": os.environ.get("GOVERNANCE_STAGE", ""),
        }
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - deliberately silent, see docstring
        pass


def load(paths: list[Path]) -> list[dict[str, Any]]:
    files: list[Path] = []
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"no such log or folder: {p}")
        files += sorted(p.rglob("demand*.jsonl")) if p.is_dir() else [p]
    rows = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def summarise(rows: list[dict[str, Any]], top: int = 10) -> dict[str, Any]:
    asked = [r for r in rows if r["caller"] not in AUTOMATED]
    gaps: dict[tuple[str, str], dict[str, Any]] = {}
    lookups: Counter[tuple[str, str]] = Counter()
    for r in asked:
        q = r["question"].strip().lower()
        if not r["answered"]:
            g = gaps.setdefault((r["domain"], q), {"domain": r["domain"], "question": r["question"], "count": 0,
                                                    "repos": set(), "callers": set()})
            g["count"] += 1
            g["repos"].add(r["repo"] or "unknown")
            g["callers"].add(r["caller"])
        for rid in r["matched"]:
            lookups[(r["domain"], rid)] += 1
    by_caller = Counter(r["caller"] for r in rows)
    by_domain: dict[str, dict[str, int]] = defaultdict(lambda: {"asked": 0, "unanswered": 0})
    for r in asked:
        by_domain[r["domain"]]["asked"] += 1
        by_domain[r["domain"]]["unanswered"] += 0 if r["answered"] else 1
    return {
        "total": len(rows),
        "automated": len(rows) - len(asked),
        "asked": len(asked),
        "unanswered": sum(1 for r in asked if not r["answered"]),
        "by_domain": dict(by_domain),
        "by_caller": dict(by_caller),
        "gaps": sorted(({**g, "repos": sorted(g["repos"]), "callers": sorted(g["callers"])} for g in gaps.values()),
                       key=lambda g: (-g["count"], g["question"]))[:top],
        "top_rules": [{"domain": d, "rule_id": rid, "count": n} for (d, rid), n in lookups.most_common(top)],
    }


def render(s: dict[str, Any]) -> str:
    out = ["# Demand report", "",
           f"**{s['asked']}** questions asked of the knowledge layer, **{s['unanswered']}** with no answer. "
           f"({s['automated']} further calls came from our own reviewers and are not counted as demand.)", ""]
    if s["by_domain"]:
        out += ["## By area", "", "| Area | Asked | No answer |", "| --- | ---: | ---: |"]
        out += [f"| {d} | {v['asked']} | {v['unanswered']} |" for d, v in sorted(s["by_domain"].items())]
        out.append("")
    out += ["## Asked for, but we have no answer (build these first)", ""]
    if s["gaps"]:
        out += ["| Area | Question | Times | Repos |", "| --- | --- | ---: | --- |"]
        out += [f"| {g['domain']} | {g['question']} | {g['count']} | {', '.join(g['repos'])} |" for g in s["gaps"]]
    else:
        out.append("None. Every question had an answer.")
    out += ["", "## Most looked-up guidance (candidates for clearer wording or examples)", ""]
    if s["top_rules"]:
        out += ["| Area | Rule or technology | Times |", "| --- | --- | ---: |"]
        out += [f"| {r['domain']} | {r['rule_id']} | {r['count']} |" for r in s["top_rules"]]
    else:
        out.append("None yet.")
    return "\n".join(out) + "\n"
