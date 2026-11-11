"""The knowledge layer, exercised over real MCP stdio sessions."""

import asyncio
import json

import pytest

from governance.mcp_client import open_domain
from helpers import ROOT

DOMAINS = ["security", "accessibility", "enterprise-alignment"]
CONTRACT = {"get_domain_info", "list_rules", "get_guidance", "get_exemplars", "get_deviation_route"}


def run(domain, fn):
    async def go():
        async with open_domain(domain, ROOT) as mcp:
            return await fn(mcp)

    return asyncio.run(go())


@pytest.mark.parametrize("domain", DOMAINS)
def test_every_domain_offers_the_same_tool_contract(domain):
    names = set(run(domain, lambda m: m.tool_names()))
    assert CONTRACT <= names


@pytest.mark.parametrize("domain", DOMAINS)
def test_domain_info_and_rules(domain):
    async def go(m):
        return await m.call("get_domain_info"), await m.call("list_rules")

    info, rules = run(domain, go)
    assert info["id"] == domain
    assert info["mode"] in ("gate", "advise", "evidence")
    assert "+" in info["guidance_version"]
    assert info["rule_count"] == len(rules) > 0
    assert all({"id", "title", "severity"} <= set(r) for r in rules)


def test_guidance_version_is_stable_between_runs():
    a = run("security", lambda m: m.call("get_domain_info"))
    b = run("security", lambda m: m.call("get_domain_info"))
    assert a["guidance_version"] == b["guidance_version"]


def test_get_guidance_by_id_and_by_topic():
    async def go(m):
        exact = await m.call("get_guidance", query="sec-001")
        topic = await m.call("get_guidance", query="docker container running as root user")
        return exact, topic

    exact, topic = run("security", go)
    assert exact["matches"][0]["id"] == "SEC-001"
    assert exact["matches"][0]["remediation"]
    assert exact["guidance_version"]
    assert topic["matches"][0]["id"] == "SEC-005"


def test_exemplars_and_unknown_rule():
    async def go(m):
        return await m.call("get_exemplars", rule_id="SEC-003"), await m.call("get_exemplars", rule_id="NOPE-1")

    ex, missing = run("security", go)
    assert "verify=False" in ex["bad"] and "verify=" in ex["good"]
    assert missing["error"] == "not_found"


def test_deviation_route_names_the_owner():
    route = run("security", lambda m: m.call("get_deviation_route"))
    assert "waiver" in route["waiver_route"].lower() and route["owner"]


def test_check_technology_statuses_and_normalisation():
    async def go(m):
        return {
            "flask": await m.call("check_technology", name="Flask", ecosystem="pip"),
            "yaml": await m.call("check_technology", name="PyYAML", ecosystem="pip"),
            "moment": await m.call("check_technology", name="moment", ecosystem="npm"),
            "banned": await m.call("check_technology", name="event-stream", ecosystem="npm"),
            "unknown": await m.call("check_technology", name="left-pad", ecosystem="npm"),
            "wrong_eco": await m.call("check_technology", name="flask", ecosystem="npm"),
            "docker": await m.call("check_technology", name="postgres", ecosystem="docker"),
        }

    r = run("enterprise-alignment", go)
    assert r["flask"]["found"] and r["flask"]["permitted"] and r["flask"]["status"] == "adopt"
    assert r["yaml"]["id"] == "pyyaml"
    assert r["moment"]["status"] == "deprecated" and r["moment"]["preferred_alternative"] == "date-fns"
    assert r["banned"]["status"] == "banned" and not r["banned"]["permitted"]
    assert r["unknown"]["found"] is False and r["unknown"]["permitted"] is False and r["unknown"]["assessment_route"]
    assert r["wrong_eco"]["found"] is False
    assert r["docker"]["id"] == "postgresql"


def test_list_technologies_filters_by_status():
    out = run("enterprise-alignment", lambda m: m.call("list_technologies", status="banned"))
    assert [t["id"] for t in out["technologies"]] == ["event-stream"]
    assert json.dumps(out)
