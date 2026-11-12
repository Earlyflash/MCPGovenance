"""Governor logic on synthetic reviewer results: modes, fail-closed, waivers, rollout, rendering, schema."""

import datetime as dt
import json

import jsonschema
import pytest

from governance.findings import Finding
from governance.govern import govern, load_waivers
from governance.policy import load_policy
from governance.render import MARKER, render_comment
from helpers import ROOT, make_pr, pipeline

TODAY = dt.date(2026, 11, 11)


def finding(domain="security", rule="SEC-003", severity="block", file="app.py", line=3, **kw):
    f = Finding(domain=domain, rule_id=rule, title="T", severity=severity, message="why", guidance_version="v1",
                remediation="fix it", owner="owner", waiver_route="route", file=file, line=line, evidence="e")
    d = f.to_dict()
    d.update(kw)
    return d


def result(tmp_path, domain, mode, findings=(), status="ok", error=""):
    (tmp_path / f"findings-{domain}.json").write_text(json.dumps({
        "schema": 1, "domain": domain, "mode": mode, "owner": "owner", "guidance_version": "v1",
        "status": status, "findings": list(findings), "stats": {}, "error": error}))


def policy(**overrides):
    p = load_policy(ROOT / "policy.yml")
    for k, v in overrides.items():
        p[k] = {**p[k], **v} if isinstance(v, dict) and k in ("enforcement", "waivers") else v
    return p


def triage(*domains):
    return {"domains": list(domains), "files": []}


def test_gate_blocks_and_advise_never_does(tmp_path):
    result(tmp_path, "security", "gate", [finding()])
    result(tmp_path, "accessibility", "advise", [finding("accessibility", "A11Y-001", "block", "a.html", 1)])
    v = govern(policy(), triage("security", "accessibility"), tmp_path, today=TODAY)
    by = {f["domain"]: f for f in v["findings"]}
    assert by["security"]["effective_severity"] == "block"
    assert by["accessibility"]["effective_severity"] == "warn" and by["accessibility"]["capped"]
    assert v["verdict"] == "fail" and v["counts"] == {"block": 1, "warn": 1, "info": 0, "waived": 0, "deferred": 0}


def test_advise_only_gives_warnings(tmp_path):
    result(tmp_path, "accessibility", "advise", [finding("accessibility", "A11Y-001", "block", "a.html", 1)])
    v = govern(policy(), triage("accessibility"), tmp_path, today=TODAY)
    assert v["verdict"] == "pass-with-warnings"


def test_clean_run_passes(tmp_path):
    result(tmp_path, "security", "gate")
    assert govern(policy(), triage("security"), tmp_path, today=TODAY)["verdict"] == "pass"


def test_no_domains_passes(tmp_path):
    v = govern(policy(), triage(), tmp_path, today=TODAY)
    assert v["verdict"] == "pass" and v["domains"] == []
    assert "No governance domains apply" in render_comment(v)


def test_missing_required_reviewer_fails_closed_but_optional_only_warns(tmp_path):
    v = govern(policy(), triage("security"), tmp_path, today=TODAY)
    assert v["verdict"] == "fail" and v["findings"][0]["rule_id"] == "GOV-001"
    v2 = govern(policy(), triage("accessibility"), tmp_path, today=TODAY)  # required: false in policy.yml
    assert v2["verdict"] == "pass-with-warnings"


def test_crashed_reviewer_is_reported_not_hidden(tmp_path):
    result(tmp_path, "security", "gate", status="error", error="RuntimeError: boom")
    v = govern(policy(), triage("security"), tmp_path, today=TODAY)
    assert v["verdict"] == "fail"
    assert v["findings"][0]["rule_id"] == "GOV-002" and "boom" in v["findings"][0]["message"]


def test_warn_only_rollout_reports_but_does_not_fail(tmp_path):
    result(tmp_path, "security", "gate", [finding()])
    v = govern(policy(enforcement={"mode": "warn-only"}), triage("security"), tmp_path, today=TODAY)
    assert v["verdict"] == "pass-with-warnings" and v["would_fail"] is True
    assert "warn-only" in render_comment(v)


def test_findings_follow_policy_precedence(tmp_path):
    result(tmp_path, "accessibility", "advise", [finding("accessibility", "A11Y-004", "warn", "a.html", 1)])
    result(tmp_path, "security", "gate", [finding(severity="warn")])
    v = govern(policy(), triage("accessibility", "security"), tmp_path, today=TODAY)
    assert [f["domain"] for f in v["findings"]] == ["security", "accessibility"]


def test_co_located_findings_from_two_domains_are_escalated(tmp_path):
    result(tmp_path, "security", "gate", [finding(severity="warn", file="x.html", line=4)])
    result(tmp_path, "accessibility", "advise", [finding("accessibility", "A11Y-004", "warn", "x.html", 4)])
    v = govern(policy(), triage("security", "accessibility"), tmp_path, today=TODAY)
    assert v["escalations"] == [{"file": "x.html", "line": 4, "domains": ["accessibility", "security"], "rules": ["A11Y-004", "SEC-003"]}]
    assert "Better looked at together" in render_comment(v)


# ---------- waivers ----------

def waiver(**kw):
    return {"rule_id": "SEC-002", "reason": "constant command", "approver": "octocat", "expires": "2026-12-01", **kw}


def waived(tmp_path, w, *, rule="SEC-002", severity="warn", pol=None, approvals=None):
    result(tmp_path, "security", "gate", [finding(rule=rule, severity=severity, file="scripts/run.py")])
    return govern(pol or policy(), triage("security"), tmp_path, [w], approvals, TODAY)


def test_valid_waiver_suppresses_a_finding_and_stays_visible(tmp_path):
    v = waived(tmp_path, waiver(path="scripts/**"))
    assert v["counts"]["warn"] == 0 and v["counts"]["waived"] == 1 and v["verdict"] == "pass"
    assert "## 🧾 Waived" in render_comment(v) and "octocat" in render_comment(v)


def test_waiver_path_scoping(tmp_path):
    v = waived(tmp_path, waiver(path="other/**"))
    assert v["counts"]["warn"] == 1 and v["counts"]["waived"] == 0


@pytest.mark.parametrize("bad,why", [
    ({"expires": "2026-11-01"}, "expired"),
    ({"expires": "2027-06-01"}, "maximum"),
    ({"expires": "soon"}, "not a date"),
    ({"reason": ""}, "missing reason"),
])
def test_invalid_waivers_do_not_apply_and_are_reported(tmp_path, bad, why):
    v = waived(tmp_path, waiver(**bad))
    assert v["counts"]["warn"] == 1
    assert why in v["waiver_problems"][0]["problem"]
    assert "We could not apply these exceptions" in render_comment(v)


def test_secrets_can_never_be_waived(tmp_path):
    v = waived(tmp_path, waiver(rule_id="SEC-001"), rule="SEC-001", severity="block")
    assert v["verdict"] == "fail" and "never be waived" in v["waiver_problems"][0]["problem"]


def test_waiver_approval_can_be_required(tmp_path):
    pol = policy(waivers={"require_approval": True})
    assert waived(tmp_path, waiver(), pol=pol, approvals=set())["counts"]["waived"] == 0
    assert waived(tmp_path, waiver(), pol=pol, approvals={"OctoCat"})["counts"]["waived"] == 1


def test_load_waivers_file(tmp_path):
    p = tmp_path / ".governance-waivers.yml"
    p.write_text("waivers:\n  - rule_id: SEC-002\n    reason: r\n    approver: a\n    expires: 2026-12-01\n")
    ws = load_waivers(p)
    assert len(ws) == 1 and ws[0]["rule_id"] == "SEC-002"
    assert load_waivers(tmp_path / "missing.yml") == []


# ---------- rendering and schema ----------

def test_comment_has_marker_machine_block_and_fix_guidance(tmp_path):
    result(tmp_path, "security", "gate", [finding(exemplar_good="requests.get(u)")])
    v = govern(policy(), triage("security"), tmp_path, today=TODAY)
    c = render_comment(v)
    assert c.startswith(MARKER) and "Blocked" in c and "fix it" in c and "See an example that works" in c
    block = c.split("```json")[1].split("```")[0]
    assert json.loads(block)["findings"][0]["rule"] == "SEC-003"


def test_pipeline_findings_conform_to_the_published_schema(tmp_path):
    schema = json.loads((ROOT / "schemas" / "finding.schema.json").read_text())
    repo, b, h = make_pr(tmp_path, {}, {"app.py": 'requests.get(u, verify=False)\nPASSWORD = "abcdefgh12345"\n',
                                         "package.json": '{"dependencies": {"moment": "1"}}\n'})
    v = pipeline(repo, b, h, tmp_path / "out")
    assert v["findings"]
    for f in v["findings"]:
        schema_view = {k: f[k] for k in f if k in schema["properties"]}
        jsonschema.validate(schema_view, schema)


def test_comment_has_banner_scoreboard_and_next_steps(tmp_path):
    result(tmp_path, "security", "gate", [finding(exemplar_good="requests.get(u)")])
    v = govern(policy(), triage("security"), tmp_path, today=TODAY)
    c = render_comment(v, {"run_url": "https://example.test/run/1", "head": "abc1234"})
    assert "# ⛔ Governance review: Blocked" in c and "[!CAUTION]" in c
    assert "### Scoreboard" in c and "| **security** |" in c
    assert "### What would help next" in c and "[workflow run](https://example.test/run/1)" in c and "abc1234" in c


def test_every_finding_links_to_its_guidance(tmp_path):
    repo, b, h = make_pr(tmp_path, {}, {"app.py": 'requests.get(u, verify=False)\n'})
    v = pipeline(repo, b, h, tmp_path / "out")
    f = v["findings"][0]
    assert f["guidance_url"].endswith("security/knowledge/rules.yml#L" + f["guidance_url"].rsplit("#L", 1)[1])
    assert "#L" in f["guidance_url"]
    assert f"({f['guidance_url']})" in render_comment(v)


def test_findings_link_to_the_human_readable_policy(tmp_path):
    repo, b, h = make_pr(tmp_path, {}, {"app.py": 'requests.get(u, verify=False)\n'})
    v = pipeline(repo, b, h, tmp_path / "out")
    url = v["findings"][0]["policy_url"]
    assert url.endswith("docs/policy/security.md#sec-003-tls-certificate-verification-disabled")
    assert f"({url})" in render_comment(v)
    policy_page = (ROOT / "docs" / "policy" / "security.md").read_text()
    assert "## SEC-003 TLS certificate verification disabled" in policy_page


def test_new_waivers_are_flagged_until_they_exist_on_the_base_branch(tmp_path):
    pol, tri = policy(), triage("security")
    res = tmp_path / "r2"
    res.mkdir()
    result(res, "security", "gate", [finding(rule="SEC-002", severity="warn", file="scripts/x.py")])
    new = govern(pol, tri, res, [waiver(path="scripts/**")], None, TODAY, base_waivers=[])
    assert new["findings"][0]["waiver"]["new_in_pr"] is True and "Proposed in this PR" in render_comment(new)
    old = govern(pol, tri, res, [waiver(path="scripts/**")], None, TODAY, base_waivers=[waiver(path="scripts/**")])
    assert old["findings"][0]["waiver"]["new_in_pr"] is False and "Proposed in this PR" not in render_comment(old)


def test_comment_speaks_kindly_and_keeps_its_tables(tmp_path):
    f = finding(exemplar_good="requests.get(u)")
    f["people_impact"] = "Someone on the network could read what is sent."
    result(tmp_path, "security", "gate", [f])
    c = render_comment(govern(policy(), triage("security"), tmp_path, today=TODAY))
    assert "thank you for this pull request" in c and "None of it is a judgement on you" in c
    assert "**A way forward:**" in c and "**Why it matters:** Someone on the network could read what is sent." in c
    assert "| Area | Result |" in c and "| ⛔ Needs fixing |" in c  # the detail tables are still there
    assert "violat" not in c.lower() and "you failed" not in c.lower()


def test_a_crashed_check_is_never_blamed_on_the_author(tmp_path):
    v = govern(policy(), triage("security"), tmp_path, today=TODAY)  # no results file: the check never reported
    c = render_comment(v)
    assert v["verdict"] == "fail" and "That is on us, not you" in c
