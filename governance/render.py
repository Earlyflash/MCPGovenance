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
BANNER_ICON = {"fail": "⛔", "pass-with-warnings": "⚠️", "pass": "✅"}
SEV_ICON = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
SEV_LABEL = {"block": "Blocking", "warn": "Warning", "info": "Note"}
SEV_TITLE = {"block": "Needs fixing before this can merge", "warn": "Worth a look", "info": "Good to know"}
SEV_PHRASE = {"block": "a blocker", "warn": "a warning", "info": "a note"}
MODE_HELP = {
    "gate": "can hold a merge",
    "advise": "advice only, never blocks",
    "evidence": "checks the paperwork exists",
}


def _things(n: int) -> str:
    return "one thing" if n == 1 else f"{n} things"


def _blurb(v: dict[str, Any]) -> str:
    """The opening words: warm, specific, and never about the person."""
    c = v["counts"]
    real = [f for f in v["findings"] if not f["waived"] and not f.get("deferred") and f["effective_severity"] == "block" and not f["rule_id"].startswith("GOV-")]
    crashed = any(f["rule_id"].startswith("GOV-") for f in v["findings"] if not f["waived"])
    if v["enforcement"] == "warn-only" and v["would_fail"]:
        return ("Good news: nothing is stopping you today, because we are rolling this out gently. The items below would hold this "
                "merge once enforcement starts, so it is kind to your future self to look at them now.")
    if v["verdict"] == "fail" and crashed and not real:
        return ("One of our checks could not finish, so we cannot give you a clear answer yet. That is on us, not you. Running the "
                "workflow again usually sorts it, and if it does not, the governance team will gladly help.")
    if v["verdict"] == "fail":
        n = len(real) or c["block"]
        return (f"You are nearly there. There {'is' if n == 1 else 'are'} {_things(n)} we would love your help with before this can merge. "
                "It is simply what our shared guidance asks of every change, and each item below comes with a way forward.")
    if v["verdict"] == "pass-with-warnings":
        n = c["warn"]
        return (f"Good news: this can merge. We noticed {_things(n)} that would make it even better for the people who use what you are building. "
                "Tackle them now while it is fresh in your mind, or leave them; that is your call.")
    return "Lovely work. We looked through your change and there is nothing you need to do. Thank you for taking care of this. 💛"


def _loc(f: dict[str, Any]) -> str:
    if not f.get("file"):
        return ""
    return f"`{f['file']}:{f['line']}`" if f.get("line") else f"`{f['file']}`"


def _cell(n: int, icon: str = "") -> str:
    return f"**{n}**" if n else "·"


def _domain_status(d: dict[str, Any]) -> str:
    c = d.get("counts", {})
    if d["status"] != "ok":
        return "⛔ Did not finish" if d["status"] == "missing" else "⛔ Hit a problem"
    if c.get("block"):
        return "⛔ Needs attention"
    if c.get("warn"):
        return "⚠️ Worth a look"
    if c.get("info"):
        return "ℹ️ Good to know"
    return "✅ All clear"


def _stage_note(f: dict[str, Any], stage: str | None) -> str:
    """Tell the author when a guardrail gets stricter with the product's stage."""
    if not stage:
        return ""
    if f.get("escalated") and not f.get("capped"):
        return (f"⏫ **A bit stricter at this stage:** for products at {st.LABELS[f['applies_from']]} this is {SEV_PHRASE[f['base_severity']]}, "
                f"but for a {st.LABELS[stage]} product it is {SEV_PHRASE[f['effective_severity']]}.")
    nxt = f.get("escalates_at")
    if nxt:
        return (f"🔭 **A heads-up for later:** for a {st.LABELS[stage]} product this is {SEV_PHRASE[f['effective_severity']]} today. "
                f"At {st.ICONS[nxt['stage']]} {st.LABELS[nxt['stage']]} it becomes {SEV_PHRASE[nxt['severity']]}, so it is kind to your future self to look at it now.")
    return ""


def _quote(lines: list[str]) -> list[str]:
    return [("> " + part) if part else ">" for l in lines for part in l.split("\n")]


def _finding_md(f: dict[str, Any], show_exemplar: bool, stage: str | None = None) -> list[str]:
    sev = f["effective_severity"]
    loc = _loc(f)
    body = [f"**{SEV_ICON[sev]} {SEV_TITLE[sev]} · `{f['rule_id']}` · {f['title']}**  "]
    if loc:
        body += [f"📍 {loc}"]
    if f.get("capped"):
        body += ["", "_This area gives advice only, so what would normally be a blocker is shown as a warning._"]
    body += [""]
    if f.get("evidence"):
        body += [f"**What we noticed:** `{f['evidence']}`".replace("``", "`"), ""]
    if f.get("people_impact"):
        body += [f"**Why it matters:** {f['people_impact']}", "", f"**In more detail:** {f['message']}", ""]
    else:
        body += [f"**Why it matters:** {f['message']}", ""]
    body += [f"**A way forward:** {f['remediation']}"]
    stage_note = _stage_note(f, stage)
    if stage_note:
        body += ["", stage_note]
    links = []
    if f.get("policy_url"):
        links.append(f"📘 [The policy, in plain words ({f['rule_id']})]({f['policy_url']})")
    if f.get("guidance_url"):
        links.append(f"📖 [The exact rule]({f['guidance_url']})")
    if links:
        body += ["", "**Want to read more?** " + " · ".join(links)]
    if show_exemplar and f.get("exemplar_good"):
        body += ["", "<details><summary>See an example that works</summary>", "", "```", *f["exemplar_good"].rstrip().splitlines(), "```", "", "</details>"]
    alert = {"block": "CAUTION", "warn": "WARNING", "info": "NOTE"}[sev]
    return [f"> [!{alert}]", *_quote(body), ""]


def render_comment(v: dict[str, Any], ctx: dict[str, Any] | None = None) -> str:
    ctx = ctx or {}
    c = v["counts"]
    headline = HEADLINES[v["verdict"]]
    icon = BANNER_ICON[v["verdict"]]
    if v["enforcement"] == "warn-only" and v["would_fail"]:
        headline, icon = "Would be blocked (warn-only rollout)", "⚠️"

    out = [MARKER, f"# {icon} Governance review: {headline}", "", "Hi 👋 and thank you for this pull request. Here is what our review found, written to help and guide you.", "",
           f"> {_blurb(v)}", ""]

    stage = (v.get("stage") or {}).get("stage")
    if stage:
        info = v["stage"]
        out += [f"**Where your product is:** {st.ladder(stage)}  ", f"<sub>{st.MEANING[stage]}. Set by: {info.get('source', 'unknown')}. "
                f"We check against the guardrails for this stage. Ones that start later are shown as a gentle preview and do not count yet.</sub>", ""]
        if v.get("promotion_scan"):
            out += ["> [!IMPORTANT]", "> **You are moving up a stage 🎉** This pull request raises the product's stage, so we looked at the whole repository, "
                    "not only what you changed. That way you get the full list in one go, instead of finding things out bit by bit.", ""]
        for n in info.get("notes", []):
            if v.get("promotion_scan") and "raises the stage" in n:
                continue  # the promotion alert above already says this
            out += ["> [!NOTE]", f"> {n}", ""]

    if not v["domains"]:
        out += ["No governance domains apply to the files in this pull request.", ""]
    else:
        scope = "the whole repository (full scan)" if v.get("full_scan") else f"{v.get('changed_files', 0)} changed file(s)"
        out += [
            f"| ⛔ Needs fixing | ⚠️ Worth a look | ℹ️ Good to know | 🧾 Agreed exceptions | ⏭️ Coming later | 🔎 Looked at |",
            "| :---: | :---: | :---: | :---: | :---: | :---: |",
            f"| **{c['block']}** | **{c['warn']}** | **{c['info']}** | **{c['waived']}** | **{c.get('deferred', 0)}** | {len(v['domains'])} area(s), {scope} |",
            "",
            "Each area looks at your change separately, against guidance its own team wrote. We bring their answers together here so you only have one place to read.",
            "",
            "### Scoreboard",
            "",
            "| Area | Result | ⛔ | ⚠️ | ℹ️ | 🧾 | How it works | Who to ask |",
            "| --- | --- | :---: | :---: | :---: | :---: | --- | --- |",
        ]
        for d in v["domains"]:
            dc = d.get("counts", {})
            out.append(
                f"| **{d['domain']}** | {_domain_status(d)} | {_cell(dc.get('block', 0), '')} | {_cell(dc.get('warn', 0), '')} | "
                f"{_cell(dc.get('info', 0), '')} | {_cell(dc.get('waived', 0), '')} | {MODE_HELP.get(d['mode'], d['mode'])} | {d['owner']} |"
            )
        out.append("")

    if v["enforcement"] == "warn-only" and v["verdict"] != "fail":
        out += ["> [!NOTE]", "> We are rolling this out gently (`warn-only`), so nothing fails yet. Think of what follows as a friendly preview of what will be enforced.", ""]

    exemplars_left = MAX_EXEMPLARS
    for d in v["domains"]:
        name = d["domain"]
        mine = [f for f in v["findings"] if f["domain"] == name and not f["waived"] and not f.get("deferred")]
        title = d.get("title") or name
        out.append(f"## {_domain_status(d).split(' ')[0]} {title}")
        out.append(f"<sub>`{name}` · {MODE_HELP.get(d['mode'], d['mode'])} · questions? ask {d['owner']}" + (f", {d['contact']}" if d.get("contact") else "") + f" · guidance `{d['guidance_version']}`" + (f" · [📘 policy]({d['policy_url']})" if d.get("policy_url") else "") + (f" · [📖 rules]({d['knowledge_url']})" if d.get("knowledge_url") else "") + "</sub>")
        out.append("")
        if not mine:
            out += ["All clear here. Nothing for you to do. 🎉", ""]
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
            out += [f"<details><summary>{warns_shown - OPEN_WARNINGS} more thing(s) worth a look in {name}</summary>", "", *folded, "</details>", ""]

    waived = [f for f in v["findings"] if f["waived"]]
    if waived:
        out += ["## 🧾 Waived: exceptions we have agreed", "", "| Rule | Where | Approver | Expires | Status | Reason |", "| --- | --- | --- | --- | --- | --- |"]
        for f in waived:
            w = f["waiver"]
            status = "⏳ Proposed in this PR" if w.get("new_in_pr") else "✅ Already agreed"
            out.append(f"| `{f['rule_id']}` | {_loc(f) or 'n/a'} | {w['approver']} | {w['expires']} | {status} | {w['reason']} |")
        out.append("")
        if any(f["waiver"].get("new_in_pr") for f in waived):
            out += ["> [!IMPORTANT]", "> Thank you for asking for an exception rather than working around the guidance. It is applied for now, and becomes permanent when the governance code owner approves the change to the waivers file and the PR merges.", ""]
        out += ["<sub>Exceptions stay visible until they expire, so nobody is surprised later.</sub>", ""]

    later = [f for f in v["findings"] if f.get("deferred")]
    if later and stage:
        nxt = st.STAGES[min(st.rank(stage) + 1, len(st.STAGES) - 1)]
        out += ["## ⏭️ A look ahead: coming at a higher stage", "",
                f"Nothing to do about these today. We noticed them while looking, and because they will matter once the product moves up from "
                f"**{st.LABELS[stage]}**, we thought you would like to know early. They do not count towards today's result.", "",
                "| Applies from | Rule | Where | Effect then | Policy |", "| --- | --- | --- | --- | --- |"]
        for f in sorted(later, key=lambda x: (st.rank(x["applies_from"]), x["rule_id"])):
            mode_sev = SEV_LABEL[f["effective_severity"]]
            pol = f"[read]({f['policy_url']})" if f.get("policy_url") else ""
            out.append(f"| {st.ICONS[f['applies_from']]} {st.LABELS[f['applies_from']]} | `{f['rule_id']}` {f['title']} | {_loc(f) or 'n/a'} | {mode_sev} | {pol} |")
        out += ["", f"<sub>When you are ready to move up to {st.LABELS[nxt]}, set the stage in `.governance.yml`.</sub>" if nxt != stage else "", ""]

    if v["waiver_problems"]:
        out += ["> [!IMPORTANT]", "> **We could not apply these exceptions.** Here is why, so you can put it right:", ">"]
        out += [f"> - `{p['rule_id']}`: {p['problem']}" for p in v["waiver_problems"]]
        out.append("")

    if v["escalations"]:
        out += ["> [!IMPORTANT]", "> **Better looked at together.** More than one area flagged the same line, and they may pull in different directions. A person should help decide how to reconcile them.", ">"]
        out += [f"> - `{e['file']}:{e['line']}`: {', '.join(e['domains'])} ({', '.join(e['rules'])})" for e in v["escalations"]]
        out.append("")

    # What to do next
    steps: list[str] = []
    if c["block"]:
        steps.append("Take the ⛔ items one at a time. Each has a **way forward** underneath. When you push a fix, this comment updates by itself, so you will see your progress.")
    if c["warn"]:
        steps.append("When you have a moment, look at the ⚠️ items. If you choose to leave one, a short note in the PR saying why is plenty.")
    if c["block"] or c["warn"]:
        steps.append("If something is a genuine exception, that is okay. Ask for a waiver rather than working around it, so it is agreed and visible.")
    if steps:
        out += ["### What would help next", ""] + [f"{i}. {s}" for i, s in enumerate(steps, 1)] + [""]
        out += ["You are not on your own. If anything here is unclear, or looks wrong to you, please say so: ask the owner shown on each section and tell them what you found. That makes the guidance better for everyone.", ""]

    routes = {d["domain"]: d["waiver_route"] for d in v["domains"] if d.get("waiver_route") and any(
        f["domain"] == d["domain"] and not f["waived"] for f in v["findings"])}
    if routes:
        out += ["<details><summary>Need a hand, or think we have got it wrong?</summary>", ""]
        for k, r in routes.items():
            row = next(d for d in v["domains"] if d["domain"] == k)
            who = f" Please ask {row['owner']}" + (f", {row['contact']}" if row.get("contact") else "") + "."
            out.append(f"- **{k}**: {r}{who}")
        out += ["", "</details>", ""]

    compact = [
        {"domain": f["domain"], "rule": f["rule_id"], "severity": f["effective_severity"], "file": f.get("file"),
         "line": f.get("line"), "fix": f["remediation"]}
        for f in v["findings"] if not f["waived"] and f["effective_severity"] in ("block", "warn")
    ][:50]
    out += ["<details><summary>🤖 For agents helping with this pull request (machine-readable)</summary>", "", "```json",
            json.dumps({"verdict": v["verdict"], "stage": stage, "findings": compact}, indent=2), "```", "", "</details>", ""]

    foot = []
    if v["not_triggered"]:
        foot.append(f"Not needed for this change: {', '.join(v['not_triggered'])}")
    if ctx.get("head"):
        foot.append(f"commit `{ctx['head']}`")
    if ctx.get("run_url"):
        foot.append(f"[workflow run]({ctx['run_url']})")
    foot.append("PR governance PoC · here to help")
    out += ["---", "<sub>" + " · ".join(foot) + "</sub>"]

    text = "\n".join(out)
    if len(text) > MAX_COMMENT_CHARS:
        text = text[:MAX_COMMENT_CHARS] + "\n\n_Comment truncated. See the workflow run for the full verdict._"
    return text
