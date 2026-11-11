"""Generate the guardrail documentation from the rules, so the stage pictures can never drift from the code.

    python -m governance docs          # rewrite docs/policy/*.md and docs/guardrails.md
    python -m governance docs --check  # fail if they are out of date (a test does this)

In a real deployment the human-written policy lives on the documentation site and is not generated; these pages
show the shape that policy should take and keep the stage pictures honest.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from . import stages as st

DOMAINS = ["security", "enterprise-alignment", "accessibility"]
MODE_TEXT = {
    "gate": "rules marked *Blocks the merge* stop a pull request until fixed or waived.",
    "advise": "advice only; nothing here blocks a merge.",
    "evidence": "checks that the required evidence exists; people judge whether the decision is right.",
}


def _load(root: Path, domain: str) -> tuple[dict, list[dict]]:
    base = root / "domains" / domain
    info = yaml.safe_load((base / "domain.yml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((base / "knowledge" / "rules.yml").read_text(encoding="utf-8"))["rules"]
    for r in rules:
        r.setdefault("applies_from", "scan")
        r["by_stage"] = st.severity_by_stage(r["severity"], r["applies_from"], r.get("escalate"), r["id"])
    return info, rules


SEV_ICON = {"block": "⛔", "warn": "⚠️", "info": "ℹ️", None: "▫️"}
SEV_WORD = {"block": "blocks the merge", "warn": "warning", "info": "note", None: "not yet"}


def _sev(info: dict, r: dict, stage: str) -> str | None:
    """What the guardrail does at a stage. Advice-only areas never block, so their blocks show as warnings."""
    sev = r["by_stage"][stage]
    return "warn" if sev == "block" and info["mode"] == "advise" else sev


def _cells(info: dict, r: dict) -> list[str]:
    return [SEV_ICON[_sev(info, r, s)] for s in st.STAGES]


def _strip(info: dict, r: dict) -> str:
    return " → ".join(f"{st.ICONS[s]} {st.LABELS[s]}: {SEV_ICON[_sev(info, r, s)]} {SEV_WORD[_sev(info, r, s)]}" for s in st.STAGES)


KEY = "⛔ blocks the merge · ⚠️ warning · ℹ️ note · ▫️ does not apply yet"


def _legend() -> list[str]:
    return ["| Stage | Meaning |", "| --- | --- |", *(f"| {st.ICONS[s]} **{st.LABELS[s]}** | {st.MEANING[s]} |" for s in st.STAGES), ""]


def policy_page(root: Path, domain: str) -> str:
    info, rules = _load(root, domain)
    title = {"security": "Security policy", "accessibility": "Accessibility policy",
             "enterprise-alignment": "Enterprise technology alignment policy"}[domain]
    out = [f"# {title}", "",
           "> **PoC example.** In a real deployment this page is the human-written policy, owned by the domain team and "
           "published on the documentation site. This copy is generated from "
           f"[`rules.yml`](../../domains/{domain}/knowledge/rules.yml) by `python -m governance docs`, so the stage tables "
           "always match what the pipeline enforces.", "",
           f"**Owner:** {info['owner']} · **Contact:** {info.get('contact', '')} · **Enforcement:** {MODE_TEXT[info['mode']]}", "",
           "**Exceptions:** " + " ".join(info["waiver_route"].split()), "",
           "## Which guardrails apply to your product", "",
           "A product declares its stage (see [guardrails by stage](../guardrails.md)). A guardrail applies from the stage "
           "shown and to every later stage, so a production product has all of them.", "",
           "| Rule | 🔍 Scan | 🧪 Pilot | 🚀 Production |", "| --- | :---: | :---: | :---: |"]
    for r in rules:
        out.append(f"| [{r['id']} {r['title']}](#{_anchor(r)}) | " + " | ".join(_cells(info, r)) + " |")
    out += ["", KEY, ""]
    for r in rules:
        out += [f"## {r['id']} {r['title']}", "",
                f"**Applies from:** {st.ICONS[r['applies_from']]} {st.LABELS[r['applies_from']]}  ",
                f"**By stage:** {_strip(info, r)}", "",
                r.get("summary", "").strip(), "",
                "**Why:** " + " ".join(r.get("guidance", "").split()), "",
                "**What to do:** " + r.get("remediation", "").strip(), ""]
        ex = r.get("exemplars") or {}
        if ex.get("bad"):
            out += ["Avoid:", "", "```", ex["bad"].rstrip(), "```", ""]
        if ex.get("good"):
            out += ["Prefer:", "", "```", ex["good"].rstrip(), "```", ""]
    return "\n".join(out)


def _anchor(r: dict) -> str:
    import re
    return re.sub(r"[^a-z0-9 \-_]", "", f"{r['id']} {r['title']}".lower()).replace(" ", "-")


def overview(root: Path) -> str:
    per: dict[str, list[tuple[str, dict]]] = {s: [] for s in st.STAGES}
    esc: dict[str, list[tuple[str, dict, str]]] = {s: [] for s in st.STAGES}
    rows: list[str] = []
    for d in DOMAINS:
        info, rules = _load(root, d)
        for r in rules:
            per[r["applies_from"]].append((d, r))
            for s_ in st.STAGES:
                if s_ != r["applies_from"] and _sev(info, r, s_) and _sev(info, r, s_) != _sev(info, r, st.STAGES[st.rank(s_) - 1]):
                    esc[s_].append((d, r, _sev(info, r, s_)))
            rows.append(f"| `{r['id']}` | {r['title']} | {d} | " + " | ".join(_cells(info, r)) + " |")
    cumulative = 0
    boxes, arrows, counts = [], [], []
    for i, s in enumerate(st.STAGES):
        new = per[s]
        cumulative += len(new)
        ids = "<br/>".join(f"{r['id']} {r['title']}" for _, r in new) or "nothing new"
        up = "".join(f"<br/>⏫ {r['id']} now {SEV_WORD[sev]}" for _, r, sev in esc[s])
        boxes.append(f'    {s}["{st.ICONS[s]} {st.LABELS[s]}<br/><b>+{len(new)} new · {cumulative} in force</b><br/>{ids}{up}"]')
        counts.append(f"| {st.ICONS[s]} {st.LABELS[s]} | {len(new)} | {cumulative} | {len(esc[s])} |")
        if i:
            arrows.append(f"    {st.STAGES[i - 1]} -->|keeps all of these, adds more| {s}")
    out = ["# Guardrails by product stage", "",
           "A product says how mature it is. The more mature, the more guardrails it must meet, and some get stricter. Each "
           "guardrail names the stage it **starts** to apply in, and it then applies to that stage and every later one.", "",
           "```mermaid", "flowchart LR", *boxes, *arrows, "```", "",
           "## What each stage means", "", *_legend(),
           "## How many guardrails apply", "", "| Stage | Added at this stage | In force | Made stricter at this stage |", "| --- | :---: | :---: | :---: |", *counts, "",
           "## Every guardrail, by stage", "",
           "| Rule | Name | Area | 🔍 Scan | 🧪 Pilot | 🚀 Production |", "| --- | --- | --- | :---: | :---: | :---: |", *rows, "",
           KEY, "",
           "A guardrail can get **stricter** as a product matures: for example a warning at pilot that blocks in production "
           "(`escalate: { production: block }` in the rule). Severity can rise with the stage but never fall.", "",
           "Each area also has its own page with the full wording: " + ", ".join(f"[{d}](policy/{d}.md)" for d in DOMAINS) + ".", "",
           "## Declaring your stage", "",
           "Add a `.governance.yml` file to the root of your repository:", "",
           "```yaml", "stage: pilot   # scan | pilot | production", "```", "",
           "Or, if you prefer, put a marker in your `README.md`:", "",
           "```markdown", "<!-- governance-stage: pilot -->", "```", "",
           "A platform team can also set it as a repository setting (the `stage` input of the workflow, from a repository "
           "variable), which a pull request cannot change.", "",
           "| Rule | What it means |", "| --- | --- |",
           "| Strictest wins | If it is declared in more than one place, the highest stage applies. |",
           "| A PR can raise it, never lower it | Raising the stage in a pull request re-checks the **whole product**, not only the changed lines. Lowering it has no effect until the lower stage is merged with code owner approval. |",
           "| Not declared | The strictest stage (production) applies, so forgetting never makes a product look safer than it is. |",
           "| Seeing ahead | Findings for guardrails from a later stage are shown in the PR comment under *Coming at a higher stage*, but do not count. |", ""]
    return "\n".join(out)


def generate(root: Path) -> dict[Path, str]:
    files = {root / "docs" / "guardrails.md": overview(root)}
    for d in DOMAINS:
        files[root / "docs" / "policy" / f"{d}.md"] = policy_page(root, d) + "\n"
    files[root / "docs" / "guardrails.md"] += "\n"
    return files


def write(root: Path) -> list[Path]:
    out = []
    for path, text in generate(root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        out.append(path)
    return out


def stale(root: Path) -> list[Path]:
    return [p for p, text in generate(root).items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
