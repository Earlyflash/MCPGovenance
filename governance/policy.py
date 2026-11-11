"""policy.yml is the governor's brain: which domains run where, precedence, waiver and rollout rules.

The policy lives in the governance repo, never in the PR being reviewed, so a PR author cannot
loosen the rules that judge their own change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "enforcement": {"mode": "enforce"},
    "ignore_paths": [],
    "precedence": [],
    "domains": {},
    "waivers": {
        "file": ".governance-waivers.yml",
        "max_days": 90,
        "require_approval": False,
        "never_waivable": [],
    },
}


def load_policy(path: str | Path) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    policy = {**DEFAULTS, **raw}
    policy["enforcement"] = {**DEFAULTS["enforcement"], **(raw.get("enforcement") or {})}
    policy["waivers"] = {**DEFAULTS["waivers"], **(raw.get("waivers") or {})}
    if policy["enforcement"]["mode"] not in ("enforce", "warn-only"):
        raise ValueError("enforcement.mode must be 'enforce' or 'warn-only'")
    if not policy["domains"]:
        raise ValueError("policy has no domains")
    return policy
