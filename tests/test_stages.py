"""Product stages: declaring one, guardrails that start later, promotion, and the MCP stage filter."""

import asyncio
import json

import pytest

from governance import stages
from governance.findings import Finding
from governance.govern import govern
from governance.policy import load_policy
from governance.render import render_comment
from governance.triage import triage as run_triage
from helpers import ROOT, make_pr, pipeline, rule_ids
from test_governor import TODAY, finding, policy, result
from test_governor import triage as tri
from test_mcp import run

POL = load_policy(ROOT / "policy.yml")
DOCKER_ROOT = "FROM python:3.12-slim\nCMD [\"python\", \"app.py\"]\n"


def detect(tmp_path, base, pr, **kw):
    repo, b, h = make_pr(tmp_path, base, pr)
    return stages.detect_stage(repo, b, POL, kw.get("override"))


def test_ordering_and_applies():
    assert stages.applies("scan", "scan") and stages.applies("scan", "production")
    assert not stages.applies("production", "pilot") and stages.applies("pilot", "production")


def test_undeclared_product_gets_the_strictest_default(tmp_path):
    info = detect(tmp_path, {}, {"x.txt": "1"})
    assert info["stage"] == "production" and "not declared" in info["source"]


def test_stage_from_governance_file_and_readme_marker(tmp_path):
    assert detect(tmp_path / "a", {".governance.yml": "stage: pilot\n"}, {"x": "1"})["stage"] == "pilot"
    marker = "# App\n<!-- governance-stage: scan -->\n"
    assert detect(tmp_path / "b", {"README.md": marker}, {"x": "1"})["stage"] == "scan"


def test_the_file_beats_the_readme_and_the_strictest_declaration_wins(tmp_path):
    base = {".governance.yml": "stage: scan\n", "README.md": "<!-- governance-stage: production -->\n"}
    assert detect(tmp_path / "a", base, {"x": "1"})["stage"] == "scan"
    assert detect(tmp_path / "b", {".governance.yml": "stage: scan\n"}, {"x": "1"}, override="pilot")["stage"] == "pilot"


def test_a_pull_request_can_raise_the_stage_and_that_triggers_a_full_scan(tmp_path):
    repo, b, h = make_pr(tmp_path, {".governance.yml": "stage: pilot\n", "old.py": "x = 1\n"}, {".governance.yml": "stage: production\n"})
    data = run_triage(repo, POL, b, h)
    assert data["stage"]["stage"] == "production" and data["stage"]["promoted"]
    assert data["promotion_scan"] and data["full_scan"]
    assert "old.py" in {f["path"] for f in data["files"]}


def test_a_pull_request_cannot_lower_the_stage(tmp_path):
    info = detect(tmp_path, {".governance.yml": "stage: production\n"}, {".governance.yml": "stage: scan\n"})
    assert info["stage"] == "production" and any("cannot lower" in n for n in info["notes"])


def test_first_declaration_in_a_pr_is_used_but_flagged(tmp_path):
    info = detect(tmp_path, {}, {".governance.yml": "stage: pilot\n"})
    assert info["stage"] == "pilot" and "first declared" in info["source"] and info["notes"]


def test_an_unknown_stage_is_ignored_with_a_note_not_silently_trusted(tmp_path):
    info = detect(tmp_path, {}, {".governance.yml": "stage: prod-ish\n"})
    assert info["stage"] == "production" and any("unknown stage" in n for n in info["notes"])


def test_later_stage_guardrails_are_previewed_but_not_counted(tmp_path):
    f = finding("security", "SEC-005", "block", "Dockerfile", 1, applies_from="production")
    result(tmp_path, "security", "gate", [f])
    pilot = {**tri("security"), "stage": {"stage": "pilot", "source": ".governance.yml", "promoted": False, "notes": []}}
    v = govern(policy(), pilot, tmp_path, today=TODAY)
    assert v["verdict"] == "pass" and v["counts"]["block"] == 0 and v["counts"]["deferred"] == 1
    c = render_comment(v)
    assert "Coming at a higher stage" in c and "Production" in c and "SEC-005" in c
    prod = {**tri("security"), "stage": {"stage": "production", "source": "x", "promoted": False, "notes": []}}
    v = govern(policy(), prod, tmp_path, today=TODAY)
    assert v["verdict"] == "fail" and v["counts"]["block"] == 1 and v["counts"]["deferred"] == 0


def test_deferred_findings_cannot_be_waived_or_escalated(tmp_path):
    f = finding("security", "SEC-005", "block", "Dockerfile", 1, applies_from="production")
    result(tmp_path, "security", "gate", [f])
    t = {**tri("security"), "stage": {"stage": "scan", "source": "x", "promoted": False, "notes": []}}
    v = govern(policy(), t, tmp_path, [{"rule_id": "SEC-005", "reason": "r", "approver": "a", "expires": "2026-12-01"}], None, TODAY)
    assert v["counts"]["waived"] == 0 and v["counts"]["deferred"] == 1


def test_a_warning_at_pilot_blocks_in_production(tmp_path):
    repo, b, h = make_pr(tmp_path / "p", {".governance.yml": "stage: pilot\n"}, {"Dockerfile": DOCKER_ROOT})
    v = pipeline(repo, b, h, tmp_path / "po")
    f = next(f for f in v["findings"] if f["rule_id"] == "SEC-005")
    assert f["effective_severity"] == "warn" and not f["deferred"] and v["verdict"] == "pass-with-warnings"
    assert f["escalates_at"] == {"stage": "production", "severity": "block"}
    assert "Heads up" in render_comment(v) and "becomes blocking" in render_comment(v)
    repo, b, h = make_pr(tmp_path / "q", {".governance.yml": "stage: production\n"}, {"Dockerfile": DOCKER_ROOT})
    v = pipeline(repo, b, h, tmp_path / "qo")
    f = next(f for f in v["findings"] if f["rule_id"] == "SEC-005")
    assert f["effective_severity"] == "block" and f["escalated"] and v["verdict"] == "fail"
    assert "Stricter at this stage" in render_comment(v)


def test_a_guardrail_for_a_later_stage_is_a_preview_in_the_pipeline(tmp_path):
    html = '<!doctype html><html lang="en"><head><title>t</title></head><body><a href="/x">click here</a></body></html>'
    repo, b, h = make_pr(tmp_path, {".governance.yml": "stage: pilot\n"}, {"index.html": html})
    v = pipeline(repo, b, h, tmp_path / "o")
    f = next(f for f in v["findings"] if f["rule_id"] == "A11Y-004")
    assert f["deferred"] and v["counts"]["deferred"] == 1 and v["verdict"] == "pass"


def test_escalation_must_rise_and_start_after_the_rule_applies():
    for bad in ({"pilot": "block"}, {"production": "warn"}, {"nope": "block"}, {"production": "fatal"}):
        with pytest.raises(ValueError):
            stages.severity_by_stage("warn" if bad.get("production") != "warn" else "block", "pilot", bad)
    assert stages.severity_by_stage("warn", "pilot", {"production": "block"}) == {"scan": None, "pilot": "warn", "production": "block"}
    assert stages.next_escalation({"scan": None, "pilot": "warn", "production": "block"}, "warn", "pilot") == ("production", "block")
    assert stages.next_escalation({"scan": None, "pilot": "warn", "production": "block"}, "warn", "production") is None


def test_promotion_pr_checks_existing_code(tmp_path):
    repo, b, h = make_pr(tmp_path, {".governance.yml": "stage: pilot\n", "Dockerfile": DOCKER_ROOT}, {".governance.yml": "stage: production\n"})
    v = pipeline(repo, b, h, tmp_path / "o")
    assert v["promotion_scan"] and v["verdict"] == "fail" and "SEC-005" in rule_ids(v)
    assert "Stage promotion" in render_comment(v)


def test_scan_stage_still_stops_secrets(tmp_path):
    repo, b, h = make_pr(tmp_path, {".governance.yml": "stage: scan\n"}, {"a.py": 'PASSWORD = "abcdefgh12345"\nrequests.get(u, verify=False)\n'})
    v = pipeline(repo, b, h, tmp_path / "o")
    live = {f["rule_id"] for f in v["findings"] if not f["deferred"]}
    assert "SEC-001" in live and "SEC-003" not in live and v["verdict"] == "fail"


def test_mcp_can_list_the_guardrails_for_a_stage_with_their_severity():
    def listing(stage):
        return {r["id"]: r["severity"] for r in run("security", lambda m: m.call("list_rules", stage=stage))}
    scan, pilot, prod = listing("scan"), listing("pilot"), listing("production")
    assert set(scan) < set(pilot) and "SEC-001" in scan and "SEC-005" not in scan
    assert pilot["SEC-005"] == "warn" and prod["SEC-005"] == "block"
    blocking = {r["id"] for r in run("security", lambda m: m.call("list_rules", stage="production", severity="block"))}
    assert "SEC-005" in blocking


def test_every_rule_declares_a_valid_stage():
    for d in ("security", "accessibility", "enterprise-alignment"):
        for r in run(d, lambda m: m.call("list_rules")):
            assert r["applies_from"] in stages.STAGES


def test_guardrail_documentation_is_generated_and_up_to_date():
    from governance import docs_gen
    assert docs_gen.stale(ROOT) == [], "run: python -m governance docs"
