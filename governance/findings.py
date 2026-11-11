"""The common finding contract every domain reviewer emits. See schemas/finding.schema.json."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SEVERITIES = ("info", "warn", "block")
MODES = ("gate", "advise", "evidence")
SEVERITY_RANK = {"info": 0, "warn": 1, "block": 2}


@dataclass
class Finding:
    domain: str
    rule_id: str
    title: str
    severity: str  # severity declared by the domain's rule
    message: str
    guidance_version: str
    remediation: str
    owner: str
    waiver_route: str
    file: str | None = None
    line: int | None = None
    evidence: str = ""
    exemplar_good: str = ""
    confidence: str = "medium"  # high | medium | low
    check_type: str = "deterministic"  # deterministic | agent
    guidance_url: str = ""  # link to this rule in the domain's guidance
    policy_url: str = ""  # link to the human-readable policy for this rule

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainResult:
    domain: str
    mode: str
    owner: str
    guidance_version: str
    status: str  # ok | error
    findings: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    title: str = ""
    contact: str = ""
    knowledge_url: str = ""
    policy_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema"] = 1
        return d


def effective_severity(declared: str, mode: str) -> str:
    """Advise-mode domains can never block a merge; their blocks are capped at warn."""
    if mode == "advise" and declared == "block":
        return "warn"
    return declared
