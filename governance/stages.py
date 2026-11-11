"""Product stages. A product declares how mature it is; each guardrail declares the stage it starts to apply in,
and it then applies to that stage and every later one.

    scan  ->  pilot  ->  production      (each stage keeps every guardrail of the stages before it)

Where a product declares its stage (the strictest declaration wins, and a pull request can raise the stage but
never lower it):
  1. the workflow input ``stage`` (set from a repository variable, so a PR cannot change it),
  2. ``.governance.yml`` with ``stage: pilot``,
  3. a marker in README.md such as ``<!-- governance-stage: pilot -->``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

STAGES = ("scan", "pilot", "production")
ICONS = {"scan": "🔍", "pilot": "🧪", "production": "🚀"}
LABELS = {"scan": "Scan", "pilot": "Pilot", "production": "Production"}
MEANING = {
    "scan": "exploring an idea; only the must-never-happen guardrails apply",
    "pilot": "real users, limited scope; the everyday guardrails apply",
    "production": "relied upon; every guardrail applies",
}
DEFAULT_STAGE_FILE = ".governance.yml"
README_MARKER = re.compile(r"governance-stage:\s*([A-Za-z]+)")


def rank(stage: str) -> int:
    return STAGES.index(stage)


def parse(value: Any) -> str | None:
    v = str(value or "").strip().lower()
    return v if v in STAGES else None


def applies(applies_from: str, stage: str) -> bool:
    """A guardrail applies at its own stage and every later one."""
    return rank(stage) >= rank(applies_from)


def ladder(stage: str | None = None) -> str:
    parts = []
    for s in STAGES:
        label = f"{ICONS[s]} {LABELS[s]}"
        parts.append(f"**{label}**" if s == stage else label)
    return " → ".join(parts)


def _declared_in(text_of, stage_file: str) -> tuple[str | None, str, str | None]:
    """Return (stage, where, problem) from the first place that declares one."""
    raw = text_of(stage_file)
    if raw is not None:
        try:
            doc = yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            doc = {}
        value = doc.get("stage") if isinstance(doc, dict) else None
        if value is not None:
            s = parse(value)
            return (s, stage_file, None) if s else (None, stage_file, f"`{stage_file}` has an unknown stage '{value}'")
    readme = text_of("README.md")
    if readme:
        m = README_MARKER.search(readme)
        if m:
            s = parse(m.group(1))
            return (s, "README.md", None) if s else (None, "README.md", f"README.md has an unknown stage '{m.group(1)}'")
    return None, "", None


def _git_show(repo: Path, rev: str, path: str) -> str | None:
    res = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=repo, capture_output=True, text=True, check=False)
    return res.stdout if res.returncode == 0 else None


def _read_head(repo: Path, path: str) -> str | None:
    p = Path(repo) / path
    try:
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 200_000:
            return None
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def detect_stage(repo: Path, base: str | None, policy: dict[str, Any], override: str | None = None) -> dict[str, Any]:
    """Work out the stage this change is judged at. See the module docstring for the rules."""
    cfg = policy.get("stages", {})
    stage_file = cfg.get("file", DEFAULT_STAGE_FILE)
    default = parse(cfg.get("default")) or "production"
    notes: list[str] = []

    from_input = parse(override)
    if override and not from_input:
        notes.append(f"The `stage` setting '{override}' is not one of {', '.join(STAGES)}; it was ignored.")

    head, head_where, head_problem = _declared_in(lambda p: _read_head(repo, p), stage_file)
    if base:
        base_stage, base_where, base_problem = _declared_in(lambda p: _git_show(repo, base, p), stage_file)
    else:
        base_stage, base_where, base_problem = None, "", None
    for problem in (head_problem, base_problem):
        if problem:
            notes.append(problem + "; it was ignored.")

    candidates = [(s, w) for s, w in ((from_input, "the repository `stage` setting"),
                                      (base_stage, f"{base_where} on the base branch")) if s]
    floor = max(candidates, key=lambda c: rank(c[0])) if candidates else None

    promoted = False
    if floor is None:
        if head:
            stage, source = head, f"{head_where} (first declared in this pull request)"
            notes.append("The stage is declared for the first time in this pull request. It needs code owner approval to merge.")
        else:
            stage, source = default, f"not declared, so the default ({default}) applies"
    else:
        stage, source = floor[0], floor[1]
        if head and rank(head) > rank(stage):
            stage, source, promoted = head, f"{head_where} (raised in this pull request)", True
            notes.append(f"This pull request raises the stage from {floor[0]} to {head}, so the whole product is re-checked against the guardrails it adds.")
        elif head and rank(head) < rank(stage):
            notes.append(f"This pull request tries to lower the stage to {head}. A pull request cannot lower the stage, so {stage} still applies.")
    return {"stage": stage, "source": source, "promoted": promoted, "notes": notes}


SEVERITY_ORDER = ("info", "warn", "block")


def severity_by_stage(base: str, applies_from: str, escalate: dict[str, str] | None, rule_id: str = "?") -> dict[str, str | None]:
    """Severity of a guardrail at each stage: None before it applies, ``base`` from ``applies_from``, then any
    escalation (for example warn at pilot, block at production). Severity may rise with maturity, never fall."""
    escalate = escalate or {}
    for stage, sev in escalate.items():
        if stage not in STAGES:
            raise ValueError(f"{rule_id}: escalate has unknown stage '{stage}'")
        if sev not in SEVERITY_ORDER:
            raise ValueError(f"{rule_id}: escalate to unknown severity '{sev}'")
        if rank(stage) <= rank(applies_from):
            raise ValueError(f"{rule_id}: escalate stage '{stage}' must be later than applies_from '{applies_from}'")
    out: dict[str, str | None] = {}
    current: str | None = None
    for s in STAGES:
        if rank(s) < rank(applies_from):
            out[s] = None
            continue
        nxt = escalate.get(s, current or base)
        if current and SEVERITY_ORDER.index(nxt) < SEVERITY_ORDER.index(current):
            raise ValueError(f"{rule_id}: severity cannot fall from {current} to {nxt} at {s}")
        current = out[s] = nxt
    return out


def severity_at(by_stage: dict[str, str | None] | None, base: str, stage: str) -> str:
    """The severity in force at ``stage``. Before the guardrail applies, the severity it will start with."""
    return (by_stage or {}).get(stage) or base


def next_escalation(by_stage: dict[str, str | None] | None, base: str, stage: str) -> tuple[str, str] | None:
    """The next stage at which this guardrail gets stricter than it is at ``stage``, if any."""
    here = severity_at(by_stage, base, stage)
    for s in STAGES[rank(stage) + 1:]:
        sev = (by_stage or {}).get(s)
        if sev and SEVERITY_ORDER.index(sev) > SEVERITY_ORDER.index(here):
            return s, sev
    return None
