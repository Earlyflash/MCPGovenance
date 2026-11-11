"""Run one domain reviewer: detect with deterministic checks, explain with the domain's MCP guidance."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from .stages import applies, severity_at
from .findings import DomainResult, Finding, effective_severity
from .mcp_client import open_domain
from .reviewers.base import Context
from .triage import files_from_triage

ANNOTATION_LEVEL = {"block": "error", "warn": "warning", "info": "notice"}


def _escape(value: str, prop: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def annotate(finding: Finding, mode: str, stage: str = "production") -> str:
    level = ANNOTATION_LEVEL[effective_severity(severity_at(finding.severity_by_stage, finding.severity, stage), mode)]
    props = f"title={_escape(f'{finding.domain} {finding.rule_id}: {finding.title}', True)}"
    if finding.file:
        props = f"file={_escape(finding.file, True)}," + (f"line={finding.line}," if finding.line else "") + props
    return f"::{level} {props}::{_escape(finding.message + ' Fix: ' + finding.remediation)}"


async def review_domain(domain_id: str, root: Path, repo: Path, triage_data: dict[str, Any], full: bool = False) -> DomainResult:
    files = files_from_triage(triage_data)
    module = importlib.import_module(f"governance.reviewers.{domain_id.replace('-', '_')}")
    async with open_domain(domain_id, root) as mcp:
        info = await mcp.call("get_domain_info")
        rules = {r["id"]: r for r in await mcp.call("list_rules")}
        route = await mcp.call("get_deviation_route")
        ctx = Context(repo=repo, files=files, full=full, mcp=mcp, base=triage_data.get("base"))
        hits = await module.run_checks(ctx)

        findings: list[Finding] = []
        seen: set[tuple[Any, ...]] = set()
        guidance_cache: dict[str, dict[str, Any]] = {}
        exemplar_cache: dict[str, str] = {}
        for hit in hits:
            if hit.rule_id not in rules:
                raise RuntimeError(f"reviewer produced unknown rule {hit.rule_id}; code and knowledge have drifted")
            if not ctx.keep(hit):
                continue
            key = (hit.rule_id, hit.file, hit.line, hit.evidence)
            if key in seen:
                continue
            seen.add(key)
            if hit.rule_id not in guidance_cache:
                g = await mcp.call("get_guidance", query=hit.rule_id)
                guidance_cache[hit.rule_id] = g["matches"][0]
                ex = await mcp.call("get_exemplars", rule_id=hit.rule_id)
                exemplar_cache[hit.rule_id] = ex.get("good", "")
            g = guidance_cache[hit.rule_id]
            message = g["summary"] + (f" {hit.detail}" if hit.detail else "")
            findings.append(
                Finding(
                    domain=domain_id,
                    rule_id=hit.rule_id,
                    title=g["title"],
                    severity=g["severity"],
                    message=message,
                    guidance_version=info["guidance_version"],
                    guidance_url=g.get("guidance_url", ""),
                    policy_url=g.get("policy_url", ""),
                    applies_from=g.get("applies_from", "scan"),
                    severity_by_stage=g.get("severity_by_stage"),
                    remediation=g["remediation"],
                    owner=info["owner"],
                    waiver_route=route["waiver_route"],
                    file=hit.file,
                    line=hit.line,
                    evidence=hit.evidence,
                    exemplar_good=exemplar_cache[hit.rule_id],
                    confidence=rules[hit.rule_id].get("confidence") or "medium",
                )
            )
        return DomainResult(
            domain=domain_id,
            mode=info["mode"],
            owner=info["owner"],
            guidance_version=info["guidance_version"],
            status="ok",
            title=info.get("title", ""),
            contact=info.get("contact", ""),
            knowledge_url=info.get("knowledge_url", ""),
            policy_url=info.get("policy_url", ""),
            findings=[f.to_dict() for f in findings],
            stats={"files_considered": len(ctx.live_files()), "rules_available": len(rules), "full_scan": full},
        )


def run_and_write(domain_id: str, root: Path, repo: Path, triage_path: Path, out_dir: Path, full: bool = False, annotate_output: bool = False) -> DomainResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    triage_data = json.loads(triage_path.read_text(encoding="utf-8"))
    full = full or bool(triage_data.get("full_scan"))
    stage = (triage_data.get("stage") or {}).get("stage") or "production"
    try:
        result = asyncio.run(review_domain(domain_id, root, repo, triage_data, full))
    except Exception as exc:  # fail closed: the governor reads status=error and decides per policy
        traceback.print_exc(file=sys.stderr)
        result = DomainResult(domain=domain_id, mode="unknown", owner="unknown", guidance_version="unknown",
                              status="error", error=f"{type(exc).__name__}: {exc}")
    (out_dir / f"findings-{domain_id}.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    if annotate_output or os.environ.get("GITHUB_ACTIONS") == "true":
        for f in result.findings:
            if applies(f.get("applies_from", "scan"), stage):  # guardrails for a later stage do not annotate the diff
                print(annotate(Finding(**f), result.mode, stage))
    return result
