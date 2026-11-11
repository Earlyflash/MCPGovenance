"""The demand layer: calls are recorded, gaps are found, and nothing is written unless asked."""

import asyncio
import json

from governance import demand
from governance.mcp_client import open_domain
from helpers import ROOT


def ask(domain, tool, caller, monkeypatch, log, **args):
    monkeypatch.setenv("GOVERNANCE_DEMAND_LOG", str(log))
    monkeypatch.setenv("GOVERNANCE_REPO", "team-a")

    async def go():
        async with open_domain(domain, ROOT, caller=caller) as m:
            return await m.call(tool, **args)

    return asyncio.run(go())


def rows(log):
    return [json.loads(x) for x in log.read_text().splitlines()]


def test_answered_and_unanswered_questions_are_recorded(tmp_path, monkeypatch):
    log = tmp_path / "demand.jsonl"
    ask("security", "get_guidance", "copilot", monkeypatch, log, query="SEC-001")
    ask("security", "get_guidance", "copilot", monkeypatch, log, query="kafka message queue")
    a, b = rows(log)
    assert (a["answered"], a["matched"], a["caller"], a["repo"]) == (True, ["SEC-001"], "copilot", "team-a")
    assert (b["answered"], b["matched"], b["question"]) == (False, [], "kafka message queue")


def test_unknown_technology_is_a_gap_and_known_one_is_not(tmp_path, monkeypatch):
    log = tmp_path / "demand.jsonl"
    ask("enterprise-alignment", "check_technology", "claude", monkeypatch, log, name="celery", ecosystem="pip")
    ask("enterprise-alignment", "check_technology", "claude", monkeypatch, log, name="flask", ecosystem="pip")
    unknown, known = rows(log)
    assert unknown["answered"] is False and known["answered"] is True


def test_nothing_is_written_without_the_setting(tmp_path, monkeypatch):
    monkeypatch.delenv("GOVERNANCE_DEMAND_LOG", raising=False)

    async def go():
        async with open_domain("security", ROOT, caller="copilot") as m:
            return await m.call("get_guidance", query="SEC-001")

    asyncio.run(go())
    assert list(tmp_path.iterdir()) == []


def test_report_ranks_gaps_and_ignores_our_own_reviewers():
    base = {"domain": "security", "tool": "get_guidance", "matched": [], "repo": "r", "stage": "", "ts": "t"}
    data = [
        {**base, "question": "Kafka", "answered": False, "caller": "copilot"},
        {**base, "question": "kafka", "answered": False, "caller": "claude", "repo": "s"},
        {**base, "question": "tls", "answered": False, "caller": "copilot"},
        {**base, "question": "SEC-001", "answered": True, "matched": ["SEC-001"], "caller": "reviewer"},
    ]
    s = demand.summarise(data)
    assert s["asked"] == 3 and s["automated"] == 1 and s["unanswered"] == 3
    assert s["gaps"][0]["count"] == 2 and s["gaps"][0]["repos"] == ["r", "s"]
    assert s["top_rules"] == []  # reviewer lookups are not demand
    assert "Asked for, but we have no answer" in demand.render(s)


def test_review_run_records_reviewer_calls_as_automated(tmp_path, monkeypatch):
    log = tmp_path / "demand.jsonl"
    ask("security", "get_domain_info", "reviewer", monkeypatch, log)
    assert demand.summarise(demand.load([log]))["automated"] == 1


def test_records_hold_no_file_contents(tmp_path, monkeypatch):
    log = tmp_path / "demand.jsonl"
    ask("security", "get_guidance", "copilot", monkeypatch, log, query="SEC-001")
    assert set(rows(log)[0]) == {"ts", "domain", "tool", "question", "answered", "matched", "caller", "repo", "stage"}
