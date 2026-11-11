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
from html import escape
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
    by_caller = Counter(r["caller"] for r in asked)
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"asked": 0, "unanswered": 0})
    by_repo: dict[str, dict[str, int]] = defaultdict(lambda: {"asked": 0, "unanswered": 0})
    for r in asked:
        for bucket, key in ((daily, r["ts"][:10]), (by_repo, r["repo"] or "unknown")):
            bucket[key]["asked"] += 1
            bucket[key]["unanswered"] += 0 if r["answered"] else 1
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
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "by_repo": dict(by_repo),
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


_CSS = """
:root{--bg:#F5F4EF;--card:#FFFEFA;--line:#DAD8CF;--ink:#14202E;--mute:#5A6572;--ok:#2E7D6B;--gap:#E59F1F;--blue:#3C6E9F;--amber-bg:#FBEBC8}
@media (prefers-color-scheme:dark){:root{--bg:#101C2C;--card:#1A2A3F;--line:#2C405A;--ink:#F5F4EF;--mute:#B7C3D0;--ok:#4FB69E;--gap:#F2B544;--blue:#7DB1E0;--amber-bg:#3A3220}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 Inter,system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:32px 24px 64px}h1{font-size:34px;margin:0 0 4px;letter-spacing:-.5px}h2{font-size:19px;margin:0 0 4px}
.sub{color:var(--mute);margin:0 0 24px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px}.kpi b{display:block;font-size:40px;line-height:1.1;letter-spacing:-1px}
.kpi span{color:var(--mute);font-size:14px}.kpi.hot{background:var(--amber-bg);border-color:var(--gap)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:16px;margin-bottom:16px}@media(max-width:600px){.grid{grid-template-columns:1fr}}
.note{color:var(--mute);font-size:14px;margin:0 0 14px}.row{display:grid;grid-template-columns:minmax(120px,38%) 1fr 48px;gap:10px;align-items:center;margin:7px 0;font-size:14px}
.row .lab{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.track{background:color-mix(in srgb,var(--line) 55%,transparent);border-radius:6px;height:18px;display:flex;overflow:hidden}
.track i{display:block;height:100%}.n{text-align:right;font-variant-numeric:tabular-nums;color:var(--mute)}
.ok{background:var(--ok)}.gap{background:var(--gap)}.blue{background:var(--blue)}.legend{display:flex;gap:16px;font-size:13px;color:var(--mute);margin-top:6px}
.legend b{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}.next{background:var(--amber-bg);border:1px solid var(--gap);border-radius:14px;padding:20px;margin-bottom:16px}
.next ol{margin:8px 0 0;padding-left:22px}.next li{margin:4px 0}svg text{fill:var(--mute);font-size:11px}footer{color:var(--mute);font-size:13px;margin-top:24px}
"""


def _bars(items: list[tuple[str, int, int]], cls: str = "blue", total: bool = False) -> str:
    """Horizontal bars. items = (label, value, second_value); with total=True it is a stacked answered/unanswered bar."""
    if not items:
        return '<p class="note">Nothing yet.</p>'
    top = max((v + w if total else v) for _, v, w in items) or 1
    out = []
    for label, v, w in items:
        if total:
            seg = f'<i class="ok" style="width:{(v) / top * 100:.1f}%"></i><i class="gap" style="width:{w / top * 100:.1f}%"></i>'
            n = v + w
        else:
            seg, n = f'<i class="{cls}" style="width:{v / top * 100:.1f}%"></i>', v
        out.append(f'<div class="row"><span class="lab" title="{escape(label)}">{escape(label)}</span><span class="track">{seg}</span><span class="n">{n}</span></div>')
    return "".join(out)


def _daily_svg(daily: list[dict[str, Any]]) -> str:
    if not daily:
        return '<p class="note">Nothing yet.</p>'
    w, h, pad = 560, 190, 24
    top = max(d["asked"] for d in daily) or 1
    bw = (w - pad) / len(daily)
    bars = []
    for i, d in enumerate(daily):
        x = pad + i * bw
        ans, gap = d["asked"] - d["unanswered"], d["unanswered"]
        ha, hg = ans / top * (h - 30), gap / top * (h - 30)
        bars.append(f'<rect x="{x + 1:.1f}" y="{h - 20 - ha:.1f}" width="{max(bw - 2, 1):.1f}" height="{ha:.1f}" fill="var(--ok)"><title>{d["date"]}: {d["asked"]} asked, {d["unanswered"]} unanswered</title></rect>'
                    f'<rect x="{x + 1:.1f}" y="{h - 20 - ha - hg:.1f}" width="{max(bw - 2, 1):.1f}" height="{hg:.1f}" fill="var(--gap)"><title>{d["date"]}: {d["unanswered"]} unanswered</title></rect>')
    step = max(len(daily) // 6, 1)
    labels = "".join(f'<text x="{pad + i * bw:.1f}" y="{h - 4}">{daily[i]["date"][5:]}</text>' for i in range(0, len(daily), step))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Questions per day">'
            f'<line x1="{pad}" y1="{h - 20}" x2="{w}" y2="{h - 20}" stroke="var(--line)"/><text x="0" y="12">{top}</text>{"".join(bars)}{labels}</svg>')


def render_html(s: dict[str, Any], title: str = "What people and agents ask the knowledge layer") -> str:
    pct = round(100 * s["unanswered"] / s["asked"]) if s["asked"] else 0
    areas = [(d, v["asked"] - v["unanswered"], v["unanswered"]) for d, v in sorted(s["by_domain"].items(), key=lambda kv: -kv[1]["asked"])]
    repos = [(r, v["asked"] - v["unanswered"], v["unanswered"]) for r, v in sorted(s["by_repo"].items(), key=lambda kv: -kv[1]["asked"])]
    gaps = [(f"{g['question']}  ·  {g['domain']}", g["count"], 0) for g in s["gaps"]]
    rules = [(f"{r['rule_id']}  ·  {r['domain']}", r["count"], 0) for r in s["top_rules"]]
    callers = [(c, n, 0) for c, n in sorted(s["by_caller"].items(), key=lambda kv: -kv[1])]
    nxt = "".join(f"<li><b>{escape(g['question'])}</b> <span style='color:var(--mute)'>({escape(g['domain'])}, asked {g['count']} times by {len(g['repos'])} repos)</span></li>" for g in s["gaps"][:3])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Demand report</title><style>{_CSS}</style></head><body><main>
<h1>{escape(title)}</h1><p class="sub">The demand layer: every question asked of the guidance, and what we could not answer. Counts exclude our own reviewers ({s['automated']} automated calls).</p>
<div class="kpis"><div class="card kpi"><b>{s['asked']:,}</b><span>questions asked</span></div>
<div class="card kpi hot"><b>{s['unanswered']:,}</b><span>with no answer ({pct}%)</span></div>
<div class="card kpi"><b>{len(s['by_repo'])}</b><span>repos asking</span></div>
<div class="card kpi"><b>{len(s['by_caller'])}</b><span>people and agents' tools</span></div></div>
<div class="next"><h2>Write these first</h2><p class="note" style="margin:0">The most-asked questions we have no guidance for.</p><ol>{nxt or '<li>Nothing: every question had an answer.</li>'}</ol></div>
<div class="grid"><section class="card"><h2>Questions per day</h2><p class="note">Teal was answered. Amber had no answer.</p>{_daily_svg(s['daily'])}
<div class="legend"><span><b class="ok"></b>Answered</span><span><b class="gap"></b>No answer</span></div></section>
<section class="card"><h2>By area</h2><p class="note">Where the gaps are.</p>{_bars(areas, total=True)}<div class="legend"><span><b class="ok"></b>Answered</span><span><b class="gap"></b>No answer</span></div></section></div>
<div class="grid"><section class="card"><h2>Asked for, with no answer</h2><p class="note">The backlog, ranked by how often it was asked.</p>{_bars(gaps, 'gap')}</section>
<section class="card"><h2>Most looked-up guidance</h2><p class="note">Heavily read rules may need clearer wording or examples.</p>{_bars(rules, 'blue')}</section></div>
<div class="grid"><section class="card"><h2>Who is asking</h2><p class="note">By assistant or tool.</p>{_bars(callers, 'blue')}</section>
<section class="card"><h2>By repo</h2><p class="note">Teal answered, amber not.</p>{_bars(repos, total=True)}</section></div>
<footer>Generated by <code>python -m governance demand --html</code>. Records hold no file contents. Report by team or repo, never by person.</footer></main></body></html>"""
