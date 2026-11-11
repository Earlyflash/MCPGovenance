"""Each domain reviewer, run end to end (git repo -> triage -> reviewer + real MCP -> governor)."""

import json

from helpers import make_pr, pipeline, rule_ids


def run(tmp_path, base, pr, **kw):
    repo, b, h = make_pr(tmp_path, base, pr)
    return pipeline(repo, b, h, tmp_path / "out", **kw)


def tok(*parts):
    # Built at runtime so this repo never contains a literal token-shaped string.
    return "".join(parts)


# ---------- security ----------

BAD_APP = "\n".join([
    "import os, subprocess, requests",
    'DB_PASSWORD = "hunter2hunter2"',
    f'AWS = "{tok("AKIA", "QWERTYUIOP123456")}"',
    "subprocess.run(cmd, shell=True)",
    "requests.get(url, verify=False)",
    "result = eval(expr)",
    "",
])


def test_security_finds_each_violation_with_guidance_from_the_mcp(tmp_path):
    v = run(tmp_path, {}, {"app.py": BAD_APP})
    assert rule_ids(v, "security") == {"SEC-001", "SEC-002", "SEC-003", "SEC-004"}
    sec1 = [f for f in v["findings"] if f["rule_id"] == "SEC-001"]
    assert {f["line"] for f in sec1} == {2, 3}
    # Guidance, remediation, exemplar and version all came from the knowledge layer.
    f = sec1[0]
    assert "rotate" in f["remediation"].lower() and f["exemplar_good"] and "+" in f["guidance_version"]
    assert v["verdict"] == "fail"


def test_secrets_are_redacted_in_findings(tmp_path):
    v = run(tmp_path, {}, {"app.py": BAD_APP})
    blob = json.dumps(v)
    assert "hunter2hunter2" not in blob
    assert tok("AKIA", "QWERTYUIOP123456") not in blob


def test_security_only_judges_lines_the_pr_added(tmp_path):
    base = {"app.py": "import requests\nrequests.get(u, verify=False)\n"}
    pr = {"app.py": "import requests\nrequests.get(u, verify=False)\nprint('hello')\n"}
    v = run(tmp_path, base, pr)
    assert "SEC-003" not in rule_ids(v)  # pre-existing, untouched by this PR


def test_full_scan_judges_everything(tmp_path):
    repo, _b, _h = make_pr(tmp_path, {"app.py": "import requests\nrequests.get(u, verify=False)\n"}, {"x.md": "x\n"})
    v = pipeline(repo, None, None, tmp_path / "out", full=True)
    assert "SEC-003" in rule_ids(v)


def test_security_false_positive_guards(tmp_path):
    ok = "\n".join([
        "import os",
        'PASSWORD = os.environ["PASSWORD"]',
        'API_KEY = "<your-api-key-here>"',
        'token = "${SECRET_TOKEN}"',
        "model.eval()",
        "# subprocess.run(x, shell=True)  commented out",
        "value = ast.literal_eval(text)",
        "",
    ])
    v = run(tmp_path, {}, {"app.py": ok})
    assert rule_ids(v, "security") == set()


def test_security_dockerfile_root_and_nonroot(tmp_path):
    root = "FROM python:3.12-slim\nCOPY . /app\nCMD [\"python\", \"/app/app.py\"]\n"
    nonroot = "FROM python:3.12-slim\nRUN useradd app\nUSER app\nCMD [\"python\"]\n"
    multistage = "FROM golang:1.22 AS build\nUSER builder\nFROM alpine\nCMD [\"/app\"]\n"
    assert "SEC-005" in rule_ids(run(tmp_path / "a", {}, {"Dockerfile": root}), "security")
    assert "SEC-005" not in rule_ids(run(tmp_path / "b", {}, {"Dockerfile": nonroot}), "security")
    assert "SEC-005" in rule_ids(run(tmp_path / "c", {}, {"Dockerfile": multistage}), "security")  # only the last stage counts


def test_security_terraform_open_ingress(tmp_path):
    v = run(tmp_path, {}, {"infra/main.tf": 'ingress {\n  cidr_blocks = ["0.0.0.0/0"]\n}\n'})
    assert "SEC-006" in rule_ids(v, "security")


def test_a_secret_in_a_readme_is_still_a_secret(tmp_path):
    v = run(tmp_path, {}, {"README.md": '# demo\nPASSWORD = "correct-horse-battery"\n'})
    assert "SEC-001" in rule_ids(v, "security") and v["verdict"] == "fail"


# ---------- accessibility ----------

BAD_HTML = """<html>
<body>
<img src="a.png">
<input type="text" name="q">
<a href="/x">click here</a>
<button></button>
</body>
</html>
"""

GOOD_HTML = """<!doctype html>
<html lang="en-GB">
<head><title>Pricing</title></head>
<body>
<img src="a.png" alt="">
<label for="q">Search</label><input id="q" type="text" name="q">
<label>Email <input type="email" name="e"></label>
<a href="/x">See pricing plans</a>
<button aria-label="Close">x</button>
<button><img src="i.png" alt="Save"></button>
<input type="hidden" name="csrf" value="1">
</body>
</html>
"""


def test_accessibility_finds_each_issue_but_never_blocks(tmp_path):
    v = run(tmp_path, {}, {"index.html": BAD_HTML})
    assert rule_ids(v, "accessibility") == {"A11Y-001", "A11Y-002", "A11Y-003", "A11Y-004", "A11Y-005", "A11Y-006"}
    a11y = [f for f in v["findings"] if f["domain"] == "accessibility"]
    assert all(f["effective_severity"] in ("warn", "info") for f in a11y)  # advise mode caps blocks
    assert any(f["capped"] for f in a11y)
    assert v["counts"]["block"] == 0 and v["verdict"] == "pass-with-warnings"


def test_accessibility_good_page_is_clean(tmp_path):
    v = run(tmp_path, {}, {"index.html": GOOD_HTML})
    assert rule_ids(v, "accessibility") == set() and v["verdict"] == "pass"


def test_accessibility_fragment_does_not_need_lang_or_title(tmp_path):
    v = run(tmp_path, {}, {"partials/card.html": '<div><img src="a.png" alt="A"></div>\n'})
    assert rule_ids(v, "accessibility") == set()


# ---------- enterprise alignment ----------

ADR_OK = """# ADR 7
## Guidance consulted
| Entry | Version | Result |
## Deviations requiring approval
None
## Tensions with strategy
None
"""


def pkg(**deps):
    return json.dumps({"name": "x", "dependencies": deps}, indent=2) + "\n"


def test_unapproved_technology_is_flagged_and_asks_for_evidence(tmp_path):
    v = run(tmp_path, {}, {"package.json": pkg(moment="^2", **{"left-pad": "^1", "event-stream": "^3"}, react="^18")})
    assert rule_ids(v, "enterprise-alignment") == {"EA-001", "EA-002", "EA-003", "EA-005"}
    by_rule = {f["rule_id"]: f for f in v["findings"] if f["domain"] == "enterprise-alignment"}
    assert "date-fns" in by_rule["EA-002"]["evidence"]
    assert "Preferred" in by_rule["EA-001"]["evidence"]
    assert v["verdict"] == "fail"  # banned + missing evidence


def test_adr_satisfies_evidence_but_not_a_ban(tmp_path):
    pilot = {".governance.yml": "stage: pilot\n"}  # deprecated and uncatalogued technology only warn before production
    v = run(tmp_path, pilot, {"package.json": pkg(moment="^2", **{"left-pad": "^1"}), "docs/adr/0007-x.md": ADR_OK})
    assert rule_ids(v, "enterprise-alignment") == {"EA-002", "EA-003"}
    assert v["verdict"] == "pass-with-warnings"
    v2 = run(tmp_path / "b", {}, {"package.json": pkg(**{"event-stream": "^3"}), "docs/adr/0007-x.md": ADR_OK})
    assert "EA-001" in rule_ids(v2) and v2["verdict"] == "fail"


def test_incomplete_adr_is_flagged(tmp_path):
    adr = "# ADR\n## Guidance consulted\nTBD\n"
    v = run(tmp_path, {}, {"package.json": pkg(moment="^2"), "docs/adr/0007-x.md": adr})
    ev = [f["evidence"] for f in v["findings"] if f["rule_id"] == "EA-006"]
    assert any("missing sections" in e for e in ev) and any("TBD" in e for e in ev)


def test_adr_template_is_not_treated_as_evidence(tmp_path):
    v = run(tmp_path, {}, {"package.json": pkg(**{"left-pad": "^1"}), "docs/adr/0000-template.md": ADR_OK})
    assert "EA-005" in rule_ids(v)


def test_approved_stack_needs_no_evidence(tmp_path):
    files = {
        "requirements.txt": "flask==3.0.0\ngunicorn>=22\nPyYAML\n# comment\n-r other.txt\n",
        "Dockerfile": "FROM python:3.12-slim\nUSER app\n",
    }
    v = run(tmp_path, {}, files)
    assert rule_ids(v, "enterprise-alignment") == set()


def test_deprecated_pip_and_docker_detection(tmp_path):
    v = run(tmp_path, {}, {"requirements.txt": "nose\nrequests\n", "Dockerfile": "FROM mysterybox/thing:1\nUSER x\n"})
    assert rule_ids(v, "enterprise-alignment") >= {"EA-002", "EA-003"}


def test_existing_dependencies_are_not_reflagged_in_diff_mode(tmp_path):
    base = {"package.json": pkg(moment="^2")}
    pr = {"package.json": pkg(moment="^2", react="^18")}  # adds only an approved package
    v = run(tmp_path, base, pr)
    assert rule_ids(v, "enterprise-alignment") == set()


def test_trial_technology_is_info_and_still_needs_an_adr(tmp_path):
    v = run(tmp_path, {}, {"package.json": pkg(**{"htmx.org": "^2"})})
    assert {"EA-004", "EA-005"} <= rule_ids(v, "enterprise-alignment")


def test_pyproject_dependencies_are_read(tmp_path):
    toml = '[project]\nname = "x"\ndependencies = ["flask>=3", "nose"]\n'
    v = run(tmp_path, {}, {"pyproject.toml": toml})
    assert "EA-002" in rule_ids(v, "enterprise-alignment")
