"""Render the governor's single PR comment: a verdict banner, a per-domain scoreboard, then findings."""

from __future__ import annotations

import json
from typing import Any

from . import stages as st

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


def _stage_note(f: dict[str, Any], stage: str | None) -> str:
    """Tell the author when a guardrail gets stricter with the product's stage."""
    if not stage:
        return ""
    if f.get("escalated") and not f.get("capped"):
        return (f"⏫ **Stricter at this stage:** only a {SEV_LABEL[f['base_severity']].lower()} for products at {st.LABELS[f['applies_from']]}, "
                f"but {SEV_LABEL[f['effective_severity']].lower()} for a {st.LABELS[stage]} product.")
    nxt = f.get("escalates_at")
    if nxt:
        return (f"🔭 **Heads up:** this is a {SEV_LABEL[f['effective_severity']].lower()} for a {st.LABELS[stage]} product. "
                f"At {st.ICONS[nxt['stage']]} {st.LABELS[nxt['stage']]} it becomes {SEV_LABEL[nxt['severity']].lower()}.")
    return ""


def _quote(lines: list[str]) -> list[str]:
    return [("> " + part) if part else ">" for l in lines for part in l.split("\n")]


def _finding_md(f: dict[str, Any], show_exemplar: bool, stage: str | None = None) -> list[str]:
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
    stage_note = _stage_note(f, stage)
    if stage_note:
        body += ["", stage_note]
    links = []
    if f.get("policy_url"):
        links.append(f"📘 [Read the policy ({f['rule_id']})]({f['policy_url']})")
    if f.get("guidance_url"):
        links.append(f"📖 [Rule definition]({f['guidance_url']})")
    if links:
        body += ["", "**Guidance:** " + " · ".join(links)]
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

    stage = (v.get("stage") or {}).get("stage")
    if stage:
        info = v["stage"]
        out += [f"**Product stage:** {st.ladder(stage)}  ", f"<sub>{st.MEANING[stage]}. Declared by: {info.get('source', 'unknown')}. "
                f"Guardrails for a later stage are previewed below but do not count yet.</sub>", ""]
        if v.get("promotion_scan"):
            out += ["> [!IMPORTANT]", "> **Stage promotion.** This pull request raises the product's stage, so the whole repository was checked, not only the changed lines.", ""]
        for n in info.get("notes", []):
            if v.get("promotion_scan") and "raises the stage" in n:
                continue  # the promotion alert above already says this
            out += ["> [!NOTE]", f"> {n}", ""]

    if not v["domains"]:
        out += ["No governance domains apply to the files in this pull request.", ""]
    else:
        scope = "the whole repository (full scan)" if v.get("full_scan") else f"{v.get('changed_files', 0)} changed file(s)"
        out += [
            f"| ⛔ Blocking | ⚠️ Warnings | ℹ️ Notes | 🧾 Waived | ⏭️ Later stages | 🔎 Reviewed |",
            "| :---: | :---: | :---: | :---: | :---: | :---: |",
            f"| **{c['block']}** | **{c['warn']}** | **{c['info']}** | **{c['waived']}** | **{c.get('deferred', 0)}** | {len(v['domains'])} domain(s), {scope} |",
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
        mine = [f for f in v["findings"] if f["domain"] == name and not f["waived"] and not f.get("deferred")]
        title = d.get("title") or name
        out.append(f"## {_domain_status(d).split(' ')[0]} {title}")
        out.append(f"<sub>`{name}` · `{d['mode']}` · owner: {d['owner']}" + (f" · {d['contact']}" if d.get("contact") else "") + f" · guidance `{d['guidance_version']}`" + (f" · [📘 policy]({d['policy_url']})" if d.get("policy_url") else "") + (f" · [📖 rules]({d['knowledge_url']})" if d.get("knowledge_url") else "") + "</sub>")
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
            md = _finding_md(f, show, stage)
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
        out += ["## 🧾 Waived", "", "| Rule | Where | Approver | Expires | Status | Reason |", "| --- | --- | --- | --- | --- | --- |"]
        for f in waived:
            w = f["waiver"]
            status = "⏳ New in this PR" if w.get("new_in_pr") else "✅ Already on the base branch"
            out.append(f"| `{f['rule_id']}` | {_loc(f) or 'n/a'} | {w['approver']} | {w['expires']} | {status} | {w['reason']} |")
        out.append("")
        if any(f["waiver"].get("new_in_pr") for f in waived):
            out += ["> [!IMPORTANT]", "> A waiver in this pull request is applied provisionally. It only becomes permanent when the governance code owner approves the change to the waivers file and the PR merges.", ""]
        out += ["<sub>Waived findings stay visible until they expire.</sub>", ""]

    later = [f for f in v["findings"] if f.get("deferred")]
    if later and stage:
        nxt = st.STAGES[min(st.rank(stage) + 1, len(st.STAGES) - 1)]
        out += ["## ⏭️ Coming at a higher stage", "",
                f"These are real problems in this change, but the guardrail starts to apply at a later stage than **{st.LABELS[stage]}**, "
                "so they do not count towards the result today. They will when the product moves up.", "",
                "| Applies from | Rule | Where | Effect then | Policy |", "| --- | --- | --- | --- | --- |"]
        for f in sorted(later, key=lambda x: (st.rank(x["applies_from"]), x["rule_id"])):
            mode_sev = SEV_LABEL[f["effective_severity"]]
            pol = f"[read]({f['policy_url']})" if f.get("policy_url") else ""
            out.append(f"| {st.ICONS[f['applies_from']]} {st.LABELS[f['applies_from']]} | `{f['rule_id']}` {f['title']} | {_loc(f) or 'n/a'} | {mode_sev} | {pol} |")
        out += ["", f"<sub>Moving to {st.LABELS[nxt]} adds guardrails; set the stage in `.governance.yml`.</sub>" if nxt != stage else "", ""]

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
            json.dumps({"verdict": v["verdict"], "stage": stage, "findings": compact}, indent=2), "```", "", "</details>", ""]

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
