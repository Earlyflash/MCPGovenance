"""Render the governor's single PR comment: a verdict banner, a per-domain scoreboard, then findings."""

from __future__ import annotations

import json
from typing import Any

MARKER = "<!-- governance-governor:v1 -->"
MAX_COMMENT_CHARS = 60_000
MAX_EXEMPLARS = 8
OPEN_WARNINGS = 6  # warnings beyond this per domain are folded away

HEADLINES = {
    "fail": "Blocked",
    "pass-with-warnings": "Passed with warnings",
    "pass": "Passed",
}
BANNER = {
    "fail": ("⛔", "CAUTION", "This pull request cannot merge until the blocking findings below are fixed or formally waived."),
    "pass-with-warnings": ("⚠️", "WARNING", "This pull request can merge. The warnings below are worth fixing while the code is fresh."),
    "pass": ("✅", "TIP", "Every applicable domain reviewed this change and found nothing to act on."),
}
SEV_ICON = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
SEV_LABEL = {"block": "Blocking", "warn": "Warning", "info": "Note"}
MODE_HELP = {
    "gate": "can block a merge",
    "advise": "advice only, never blocks",
    "evidence": "checks that evidence exists",
}


def _loc(f: dict[str, Any]) -> str:
    if not f.get("file"):
        return ""
    return f"`{f['file']}:{f['line']}`" if f.get("line") else f"`{f['file']}`"


def _cell(n: int, icon: str = "") -> str:
    return f"**{n}**" if n else "·"


def _domain_status(d: dict[str, Any]) -> str:
    c = d.get("counts", {})
    if d["status"] != "ok":
        return "⛔ Did not report" if d["status"] == "missing" else "⛔ Failed"
    if c.get("block"):
        return "⛔ Blocked"
    if c.get("warn"):
        return "⚠️ Warnings"
    if c.get("info"):
        return "ℹ️ Notes"
    return "✅ Clear"


def _quote(lines: list[str]) -> list[str]:
    return [("> " + part) if part else ">" for l in lines for part in l.split("\n")]


def _finding_md(f: dict[str, Any], show_exemplar: bool) -> list[str]:
    sev = f["effective_severity"]
    loc = _loc(f)
    body = [f"**{SEV_ICON[sev]} {SEV_LABEL[sev]} · `{f['rule_id']}` · {f['title']}**  "]
    if loc:
        body += [f"📍 {loc}"]
    if f.get("capped"):
        body += ["", "_Advice-only domain: declared as blocking, shown as a warning._"]
    body += [""]
    if f.get("evidence"):
        body += [f"**Found:** `{f['evidence']}`".replace("``", "`"), ""]
    body += [f"**Why it matters:** {f['message']}", "", f"**How to fix:** {f['remediation']}"]
    if f.get("guidance_url"):
        body += ["", f"📖 **Guidance:** [{f['rule_id']} in the {f['domain']} guidance]({f['guidance_url']})"]
    if show_exemplar and f.get("exemplar_good"):
        body += ["", "<details><summary>What good looks like</summary>", "", "```", *f["exemplar_good"].rstrip().splitlines(), "```", "", "</details>"]
    alert = {"block": "CAUTION", "warn": "WARNING", "info": "NOTE"}[sev]
    return [f"> [!{alert}]", *_quote(body), ""]


def render_comment(v: dict[str, Any], ctx: dict[str, Any] | None = None) -> str:
    ctx = ctx or {}
    c = v["counts"]
    headline = HEADLINES[v["verdict"]]
    icon, _, blurb = BANNER[v["verdict"]]
    if v["enforcement"] == "warn-only" and v["would_fail"]:
        headline, icon = "Would be blocked (warn-only rollout)", "⚠️"
        blurb = "Enforcement is in warn-only rollout, so nothing fails yet. Once enforced, the blocking findings below would stop this merge."

    out = [MARKER, f"# {icon} Governance review: {headline}", "", f"_{blurb}_", ""]

    if not v["domains"]:
        out += ["No governance domains apply to the files in this pull request.", ""]
    else:
        scope = "the whole repository (full scan)" if v.get("full_scan") else f"{v.get('changed_files', 0)} changed file(s)"
        out += [
            f"| ⛔ Blocking | ⚠️ Warnings | ℹ️ Notes | 🧾 Waived | 🔎 Reviewed |",
            "| :---: | :---: | :---: | :---: | :---: |",
            f"| **{c['block']}** | **{c['warn']}** | **{c['info']}** | **{c['waived']}** | {len(v['domains'])} domain(s), {scope} |",
            "",
            "Each domain reviews independently against its own guidance. This comment only collates the results.",
            "",
            "### Scoreboard",
            "",
            "| Domain | Result | ⛔ | ⚠️ | ℹ️ | 🧾 | Role | Owner |",
            "| --- | --- | :---: | :---: | :---: | :---: | --- | --- |",
        ]
        for d in v["domains"]:
            dc = d.get("counts", {})
            out.append(
                f"| **{d['domain']}** | {_domain_status(d)} | {_cell(dc.get('block', 0), '')} | {_cell(dc.get('warn', 0), '')} | "
                f"{_cell(dc.get('info', 0), '')} | {_cell(dc.get('waived', 0), '')} | `{d['mode']}` · {MODE_HELP.get(d['mode'], '')} | {d['owner']} |"
            )
        out.append("")

    if v["enforcement"] == "warn-only" and v["verdict"] != "fail":
        out += ["> [!NOTE]", "> Enforcement is `warn-only`: findings are reported but do not fail the check yet.", ""]

    exemplars_left = MAX_EXEMPLARS
    for d in v["domains"]:
        name = d["domain"]
        mine = [f for f in v["findings"] if f["domain"] == name and not f["waived"]]
        title = d.get("title") or name
        out.append(f"## {_domain_status(d).split(' ')[0]} {title}")
        out.append(f"<sub>`{name}` · `{d['mode']}` · owner: {d['owner']}" + (f" · {d['contact']}" if d.get("contact") else "") + f" · guidance `{d['guidance_version']}`" + (f" ([read it]({d['knowledge_url']}))" if d.get("knowledge_url") else "") + "</sub>")
        out.append("")
        if not mine:
            out += ["No findings. Nothing to do here.", ""]
            continue
        warns_shown = 0
        folded: list[str] = []
        for f in mine:
            show = exemplars_left > 0 and f["effective_severity"] in ("block", "warn")
            if show:
                exemplars_left -= 1
            md = _finding_md(f, show)
            if f["effective_severity"] == "warn":
                warns_shown += 1
                if warns_shown > OPEN_WARNINGS:
                    folded += md
                    continue
            out += md
        if folded:
            out += [f"<details><summary>{warns_shown - OPEN_WARNINGS} more warning(s) in {name}</summary>", "", *folded, "</details>", ""]

    waived = [f for f in v["findings"] if f["waived"]]
    if waived:
        out += ["## 🧾 Waived", "", "| Rule | Where | Approved by | Expires | Reason |", "| --- | --- | --- | --- | --- |"]
        for f in waived:
            w = f["waiver"]
            out.append(f"| `{f['rule_id']}` | {_loc(f) or 'n/a'} | {w['approver']} | {w['expires']} | {w['reason']} |")
        out += ["", "<sub>Waived findings stay visible until they expire.</sub>", ""]

    if v["waiver_problems"]:
        out += ["> [!IMPORTANT]", "> **Waivers that did not apply**", ">"]
        out += [f"> - `{p['rule_id']}`: {p['problem']}" for p in v["waiver_problems"]]
        out.append("")

    if v["escalations"]:
        out += ["> [!IMPORTANT]", "> **Review together.** More than one domain flagged the same line. A person should decide how to reconcile them.", ">"]
        out += [f"> - `{e['file']}:{e['line']}`: {', '.join(e['domains'])} ({', '.join(e['rules'])})" for e in v["escalations"]]
        out.append("")

    # What to do next
    steps: list[str] = []
    if c["block"]:
        steps.append("Fix each ⛔ blocking finding (the **How to fix** line says how), then push. This comment updates itself.")
    if c["warn"]:
        steps.append("Fix the ⚠️ warnings if you can, or note in the PR why they are acceptable.")
    if c["block"] or c["warn"]:
        steps.append("If a finding is a genuine exception, request a waiver (see below) rather than ignoring it.")
    if steps:
        out += ["### What to do next", ""] + [f"{i}. {s}" for i, s in enumerate(steps, 1)] + [""]

    routes = {d["domain"]: d["waiver_route"] for d in v["domains"] if d.get("waiver_route") and any(
        f["domain"] == d["domain"] and not f["waived"] for f in v["findings"])}
    if routes:
        out += ["<details><summary>How to ask for a waiver or get help</summary>", ""]
        for k, r in routes.items():
            row = next(d for d in v["domains"] if d["domain"] == k)
            who = f" Ask: {row['owner']}" + (f", {row['contact']}" if row.get("contact") else "") + "."
            out.append(f"- **{k}**: {r}{who}")
        out += ["", "</details>", ""]

    compact = [
        {"domain": f["domain"], "rule": f["rule_id"], "severity": f["effective_severity"], "file": f.get("file"),
         "line": f.get("line"), "fix": f["remediation"]}
        for f in v["findings"] if not f["waived"] and f["effective_severity"] in ("block", "warn")
    ][:50]
    out += ["<details><summary>🤖 Machine-readable findings (for agents fixing this PR)</summary>", "", "```json",
            json.dumps({"verdict": v["verdict"], "findings": compact}, indent=2), "```", "", "</details>", ""]

    foot = []
    if v["not_triggered"]:
        foot.append(f"Not triggered by this change: {', '.join(v['not_triggered'])}")
    if ctx.get("head"):
        foot.append(f"commit `{ctx['head']}`")
    if ctx.get("run_url"):
        foot.append(f"[workflow run]({ctx['run_url']})")
    foot.append("PR governance PoC")
    out += ["---", "<sub>" + " · ".join(foot) + "</sub>"]

    text = "\n".join(out)
    if len(text) > MAX_COMMENT_CHARS:
        text = text[:MAX_COMMENT_CHARS] + "\n\n_Comment truncated. See the workflow run for the full verdict._"
    return text
