"""The knowledge layer: one small MCP server per domain, all with the same tool contract.

Contract (every domain):
  get_domain_info()            -> id, title, mode, owner, contact, guidance_version, knowledge_url
  list_rules(severity?)        -> every rule with id, title, severity, summary, tags
  get_guidance(query)          -> the rule(s) matching an id or free-text topic: guidance + remediation
  get_exemplars(rule_id)       -> a "bad" and a "good" example
  get_deviation_route()        -> how to request a waiver, who owns the domain

A domain's knowledge is plain YAML in ``domains/<id>/knowledge`` so its owners can change it with an
ordinary pull request. Domains may register extra tools (see enterprise-alignment).

Tools return JSON text so every MCP client can use them. Stdout belongs to the protocol: never print.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .stages import STAGES, applies, parse as parse_stage, severity_at, severity_by_stage
from mcp.server.mcpserver import MCPServer


class Knowledge:
    def __init__(self, domain_dir: Path):
        self.dir = Path(domain_dir)
        self.info: dict[str, Any] = yaml.safe_load((self.dir / "domain.yml").read_text(encoding="utf-8"))
        rules_doc = yaml.safe_load((self.dir / "knowledge" / "rules.yml").read_text(encoding="utf-8"))
        self.rules: list[dict[str, Any]] = rules_doc["rules"]
        self._lines = {
            m.group(1).upper(): n
            for n, line in enumerate((self.dir / "knowledge" / "rules.yml").read_text(encoding="utf-8").splitlines(), start=1)
            if (m := re.match(r"\s*-\s*id:\s*(\S+)", line))
        }
        for r in self.rules:
            r.setdefault("applies_from", "scan")
            if r["applies_from"] not in STAGES:
                raise ValueError(f"{r['id']}: applies_from must be one of {', '.join(STAGES)}")
            r["severity_by_stage"] = severity_by_stage(r["severity"], r["applies_from"], r.get("escalate"), r["id"])
        self.version = self._version()

    def _version(self) -> str:
        h = hashlib.sha256()
        files = [self.dir / "domain.yml", *sorted((self.dir / "knowledge").rglob("*"))]
        for p in files:
            if p.is_file():
                h.update(p.relative_to(self.dir).as_posix().encode())
                h.update(p.read_bytes())
        return f"{self.info.get('knowledge_version', '0')}+{h.hexdigest()[:8]}"

    def domain_info(self) -> dict[str, Any]:
        i = self.info
        return {
            "id": i["id"],
            "title": i["title"],
            "mode": i["mode"],
            "owner": i["owner"],
            "contact": i.get("contact", ""),
            "guidance_version": self.version,
            "knowledge_url": i.get("knowledge_url", ""),
            "policy_url": i.get("policy_url", ""),
            "rule_count": len(self.rules),
        }

    def guidance_url(self, rule_id: str) -> str:
        """A link to the rule's own lines in the knowledge file (empty if the domain has no knowledge_url)."""
        base = self.info.get("knowledge_url", "")
        line = self._lines.get(rule_id.upper())
        return f"{base}#L{line}" if base and line else base

    def policy_url(self, rule_id: str) -> str:
        """Link to the human-readable policy for this rule (rule-specific if set, else its section on the domain page)."""
        r = self.rule(rule_id) or {}
        if r.get("policy_url"):
            return r["policy_url"]
        base = self.info.get("policy_url", "")
        if not base:
            return ""
        heading = f"{r.get('id', rule_id)} {r.get('title', '')}".lower()
        anchor = re.sub(r"[^a-z0-9 \-_]", "", heading).replace(" ", "-")
        return f"{base}#{anchor}" if r else base

    def rule(self, rule_id: str) -> dict[str, Any] | None:
        for r in self.rules:
            if r["id"].lower() == rule_id.strip().lower():
                return r
        return None

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        exact = self.rule(query)
        if exact:
            return [exact]
        terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
        scored: list[tuple[int, dict[str, Any]]] = []
        for r in self.rules:
            hay = " ".join([r["id"], r["title"], r.get("summary", ""), " ".join(r.get("tags", []))]).lower()
            score = sum(1 for t in terms if t in hay)
            if score:
                scored.append((score, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def build_server(domain_dir: Path) -> tuple[MCPServer, Knowledge]:
    k = Knowledge(domain_dir)
    mcp = MCPServer(f"{k.info['id']}-guidance", log_level="WARNING")

    @mcp.tool()
    def get_domain_info() -> str:
        """Describe this governance domain: owner, mode (gate, advise or evidence), and the current
        guidance_version. Call first to see who owns the guidance and how strictly it is enforced."""
        return _j(k.domain_info())

    @mcp.tool()
    def list_rules(severity: str | None = None, stage: str | None = None) -> str:
        """List every rule in this domain (id, title, severity, applies_from, summary, tags). Optionally filter
        by severity (block, warn, info) and/or by product stage (scan, pilot, production) to see only the
        guardrails that apply to a product at that stage, with the severity they have at that stage. A rule
        applies from its stage onward, and some get stricter later (see severity_by_stage)."""
        wanted = parse_stage(stage) if stage else None
        rules = [
            {**{key: r.get(key) for key in ("id", "title", "severity", "applies_from", "severity_by_stage", "summary", "tags", "confidence")},
             "severity": severity_at(r["severity_by_stage"], r["severity"], wanted) if wanted else r["severity"]}
            for r in k.rules
            if (wanted is None or applies(r["applies_from"], wanted))
            and (severity is None or (severity_at(r["severity_by_stage"], r["severity"], wanted) if wanted else r["severity"]) == severity)
        ]
        return _j(rules)

    @mcp.tool()
    def get_guidance(query: str) -> str:
        """Get the guidance for a rule id (for example SEC-001) or a free-text topic. Returns the rule,
        why it exists, how to fix a violation, and the guidance_version the answer came from. Call this
        BEFORE designing or changing something this domain governs."""
        matches = k.search(query)
        return _j(
            {
                "query": query,
                "guidance_version": k.version,
                "owner": k.info["owner"],
                "matches": [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "severity": r["severity"],
                        "summary": r.get("summary", ""),
                        "guidance": r.get("guidance", ""),
                        "remediation": r.get("remediation", ""),
                        "tags": r.get("tags", []),
                        "guidance_url": k.guidance_url(r["id"]),
                        "policy_url": k.policy_url(r["id"]),
                        "applies_from": r["applies_from"],
                        "severity_by_stage": r["severity_by_stage"],
                    }
                    for r in matches
                ],
            }
        )

    @mcp.tool()
    def get_exemplars(rule_id: str) -> str:
        """Show what bad and good look like for a rule, so the fix follows the organisation's pattern."""
        r = k.rule(rule_id)
        if not r:
            return _j({"error": "not_found", "rule_id": rule_id})
        ex = r.get("exemplars", {})
        return _j({"rule_id": r["id"], "bad": ex.get("bad", ""), "good": ex.get("good", ""), "guidance_version": k.version})

    @mcp.tool()
    def get_deviation_route() -> str:
        """How to request a waiver or deviation in this domain, and who decides."""
        return _j(
            {
                "waiver_route": k.info.get("waiver_route", ""),
                "owner": k.info["owner"],
                "contact": k.info.get("contact", ""),
                "guidance_version": k.version,
            }
        )

    return mcp, k
