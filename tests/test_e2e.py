"""The real CLI, as the workflows call it, against real git repositories."""

import json
import subprocess
import sys

from governance.__main__ import main
from helpers import ROOT, make_pr


def run_cli(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "-m", "governance", *args], cwd=cwd, capture_output=True, text=True)


def test_local_command_blocks_an_unsafe_change(tmp_path, capsys):
    repo, base, head = make_pr(tmp_path, {}, {"app.py": 'DB_PASSWORD = "hunter2hunter2"\n'})
    code = main(["local", "--repo", str(repo), "--base", base, "--head", head, "--out", str(tmp_path / "o")])
    out = capsys.readouterr().out
    assert code == 1
    assert "Governance review: Blocked" in out and "SEC-001" in out
    assert "hunter2hunter2" not in out
    assert (tmp_path / "o" / "verdict.json").is_file() and (tmp_path / "o" / "comment.md").is_file()


def test_local_command_passes_a_clean_change(tmp_path, capsys):
    repo, base, head = make_pr(tmp_path, {}, {"notes.md": "just words\n"})
    code = main(["local", "--repo", str(repo), "--base", base, "--head", head, "--out", str(tmp_path / "o")])
    assert code == 0 and "Governance review: Passed" in capsys.readouterr().out


def test_separate_workflow_steps_triage_review_govern(tmp_path):
    """The exact sequence the composite actions run, each as its own process."""
    repo, base, head = make_pr(tmp_path, {}, {
        "app.py": "result = eval(expr)\n", "index.html": "<html><body><img src='a.png'></body></html>\n"})
    out = tmp_path / "gov"
    gh_out = tmp_path / "github_output"
    env_args = dict(cwd=ROOT)

    t = subprocess.run([sys.executable, "-m", "governance", "triage", "--repo", str(repo), "--base", base, "--head", head,
                        "--out", str(out / "triage.json")], capture_output=True, text=True,
                       env={**__import__("os").environ, "GITHUB_OUTPUT": str(gh_out)}, **env_args)
    assert t.returncode == 0, t.stderr
    outputs = dict(line.split("=", 1) for line in gh_out.read_text().splitlines())
    assert json.loads(outputs["domains"]) == ["security", "accessibility"] and outputs["applies"] == "true"

    for d in json.loads(outputs["domains"]):
        r = run_cli("review", "--domain", d, "--repo", str(repo), "--triage", str(out / "triage.json"), "--out", str(out))
        assert r.returncode == 0, r.stderr
    assert (out / "findings-security.json").is_file() and (out / "findings-accessibility.json").is_file()

    summary = tmp_path / "summary.md"
    g = subprocess.run([sys.executable, "-m", "governance", "govern", "--triage", str(out / "triage.json"),
                        "--results", str(out), "--repo", str(repo), "--out", str(out)], capture_output=True, text=True,
                       env={**__import__("os").environ, "GITHUB_STEP_SUMMARY": str(summary), "GITHUB_OUTPUT": str(gh_out)}, **env_args)
    assert g.returncode == 1, g.stdout + g.stderr  # eval() is a blocking security finding
    assert "verdict=fail" in g.stdout
    assert "Governance review: Blocked" in summary.read_text()
    assert "verdict=fail" in gh_out.read_text()


def test_github_annotations_are_emitted_in_actions(tmp_path):
    repo, base, head = make_pr(tmp_path, {}, {"app.py": "requests.get(u, verify=False)\n"})
    out = tmp_path / "gov"
    run_cli("triage", "--repo", str(repo), "--base", base, "--head", head, "--out", str(out / "triage.json"))
    import os
    r = subprocess.run([sys.executable, "-m", "governance", "review", "--domain", "security", "--repo", str(repo),
                        "--triage", str(out / "triage.json"), "--out", str(out)], cwd=ROOT, capture_output=True, text=True,
                       env={**os.environ, "GITHUB_ACTIONS": "true"})
    assert "::error file=app.py,line=1,title=security SEC-003" in r.stdout


def test_a_crashing_reviewer_writes_an_error_result_and_exits_nonzero(tmp_path):
    repo, base, head = make_pr(tmp_path, {}, {"x.md": "x\n"})
    out = tmp_path / "gov"
    run_cli("triage", "--repo", str(repo), "--base", base, "--head", head, "--out", str(out / "triage.json"))
    r = run_cli("review", "--domain", "no-such-domain", "--repo", str(repo), "--triage", str(out / "triage.json"), "--out", str(out))
    assert r.returncode == 1
    res = json.loads((out / "findings-no-such-domain.json").read_text())
    assert res["status"] == "error" and res["error"]  # the governor turns this into a failing GOV-002 finding


def test_unreadable_triage_input_is_an_error_not_a_silent_pass(tmp_path):
    repo, _b, _h = make_pr(tmp_path, {}, {"x.md": "x\n"})
    r = run_cli("review", "--domain", "security", "--repo", str(repo), "--triage", str(tmp_path / "missing.json"), "--out", str(tmp_path))
    assert r.returncode != 0
