"""Render the governor's single PR comment."""

from __future__ import annotations

import json
from typing import Any

MARKER = "<!-- governance-governor:v1 -->"
MAX_COMMENT_CHARS = 60_000
MAX_EXEMPLARS = 8

HEADLINES = {
    "fail": "Blocked",
    "pass-with-warnings": "Passed with warnings",
    "pass": "Passed",
}


def _loc(f: dict[str, Any]) -> str:
    if not f.get("file"):
        return ""
    return f" - `{f['file']}:{f['line']}`" if f.get("line") else f" - `{f['file']}`"


def _finding_md(f: dict[str, Any], show_exemplar: bool) -> str:
    sev = f["effective_severity"].upper()
    cap = " (advise-only domain: declared block, shown as warn)" if f.get("capped") else ""
    lines = [f"- **{sev}** `{f['rule_id']}` {f['title']}{_loc(f)}{cap}"]
    if f.get("evidence"):
        lines.append(f"  - Found: {f['evidence']}")
    lines.append(f"  - Why: {f['message']}")
    lines.append(f"  - Fix: {f['remediation']}")
    if show_exemplar and f.get("exemplar_good"):
        lines += ["", "  <details><summary>What good looks like</summary>", "", "  ```", *("  " + l for l in f["exemplar_good"].rstrip().splitlines()), "  ```", "", "  </details>", ""]
    return "\n".join(lines)


def render_comment(v: dict[str, Any]) -> str:
    c = v["counts"]
    headline = HEADLINES[v["verdict"]]
    if v["enforcement"] == "warn-only" and v["would_fail"]:
        headline = "Would be blocked (warn-only rollout)"
    out = [MARKER, f"## Governance review: {headline}", ""]

    if not v["domains"]:
        out += ["No governance domains apply to the files in this pull request.", ""]
    else:
        out += [f"**{c['block']} blocking · {c['warn']} warnings · {c['info']} notes · {c['waived']} waived** "
                f"across {len(v['domains'])} domain(s). Each domain reviews independently; this comment only collates their results.", ""]

    if v["enforcement"] == "warn-only":
        out += ["> Enforcement is `warn-only`: findings are reported but do not fail the check yet.", ""]

    exemplars_left = MAX_EXEMPLARS
    for d in v["domains"]:
        name = d["domain"]
        mine = [f for f in v["findings"] if f["domain"] == name and not f["waived"]]
        out.append(f"### {name} · {d['mode']} · owner: {d['owner']} · guidance `{d['guidance_version']}`")
        if not mine:
            out += ["", "No findings.", ""]
            continue
        out.append("")
        for f in mine:
            show = exemplars_left > 0 and f["effective_severity"] in ("block", "warn")
            if show:
                exemplars_left -= 1
            out.append(_finding_md(f, show))
        out.append("")

    waived = [f for f in v["findings"] if f["waived"]]
    if waived:
        out += ["### Waived", ""]
        for f in waived:
            w = f["waiver"]
            out.append(f"- `{f['rule_id']}`{_loc(f)} waived by {w['approver']} until {w['expires']}: {w['reason']}")
        out.append("")

    if v["waiver_problems"]:
        out += ["### Waivers that did not apply", ""]
        out += [f"- `{p['rule_id']}`: {p['problem']}" for p in v["waiver_problems"]]
        out.append("")

    if v["escalations"]:
        out += ["### Review together", "", "More than one domain flagged the same line. A person should decide how to reconcile them:", ""]
        out += [f"- `{e['file']}:{e['line']}` - {', '.join(e['domains'])} ({', '.join(e['rules'])})" for e in v["escalations"]]
        out.append("")

    routes = {d["domain"]: d["waiver_route"] for d in v["domains"] if d.get("waiver_route") and any(
        f["domain"] == d["domain"] and not f["waived"] for f in v["findings"])}
    if routes:
        out += ["<details><summary>How to ask for a waiver</summary>", ""]
        out += [f"- **{k}**: {r}" for k, r in routes.items()]
        out += ["", "</details>", ""]

    if v["not_triggered"]:
        out += [f"_Not triggered by this change: {', '.join(v['not_triggered'])}._", ""]

    compact = [
        {"domain": f["domain"], "rule": f["rule_id"], "severity": f["effective_severity"], "file": f.get("file"),
         "line": f.get("line"), "fix": f["remediation"]}
        for f in v["findings"] if not f["waived"] and f["effective_severity"] in ("block", "warn")
    ][:50]
    out += ["<details><summary>Machine-readable findings (for agents fixing this PR)</summary>", "", "```json",
            json.dumps({"verdict": v["verdict"], "findings": compact}, indent=2), "```", "", "</details>"]

    text = "\n".join(out)
    if len(text) > MAX_COMMENT_CHARS:
        text = text[:MAX_COMMENT_CHARS] + "\n\n_Comment truncated. See the workflow run for the full verdict._"
    return text
