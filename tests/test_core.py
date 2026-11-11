"""globs, diff parsing and triage."""

from governance.diff import git_changed_files, parse_unified_diff
from governance.globs import match, match_any
from governance.policy import load_policy
from governance.triage import triage
from helpers import ROOT, make_pr


def test_glob_basename_patterns_match_at_any_depth():
    assert match("a/b/c.html", "*.html")
    assert match("deep/Dockerfile.prod", "Dockerfile*")
    assert match("services/api/package.json", "package.json")
    assert not match("a/b/c.htm", "*.html")


def test_glob_anchored_patterns():
    assert match("docs/adr/0001-x.md", "docs/adr/**")
    assert match("docs/adr/0001-x.md", "docs/adr/*.md")
    assert not match("other/docs/adr/0001-x.md", "docs/adr/**")
    assert match("node_modules/x/y.js", "node_modules/**")
    assert match("src/app/main.py", "**/main.py")
    assert match("main.py", "**/main.py")
    assert match("anything/at/all.txt", "**")
    assert not match("docs/adr/sub/x.md", "docs/adr/*.md")
    assert match_any("x.tf", ["*.py", "*.tf"])


def test_parse_unified_diff_counts_added_lines():
    diff = (
        "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n"
        "@@ -2 +2 @@\n-old\n+new\n"
        "@@ -9,0 +10,2 @@\n+a\n+b\n"
        "diff --git a/new.txt b/new.txt\nnew file mode 100644\n--- /dev/null\n+++ b/new.txt\n"
        "@@ -0,0 +1,3 @@\n+1\n+2\n+3\n"
        "diff --git a/gone.txt b/gone.txt\ndeleted file mode 100644\n--- a/gone.txt\n+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n-x\n-y\n"
    )
    by_path = {f.path: f for f in parse_unified_diff(diff)}
    assert by_path["app.py"].added_lines == [2, 10, 11]
    assert by_path["app.py"].status == "modified"
    assert by_path["new.txt"].status == "added" and by_path["new.txt"].added_lines == [1, 2, 3]
    assert by_path["gone.txt"].status == "deleted" and by_path["gone.txt"].added_lines == []


def test_git_changed_files_reports_only_changed_lines(tmp_path):
    repo, base, head = make_pr(
        tmp_path,
        base={"app.py": "a = 1\nb = 2\nc = 3\n", "old.txt": "bye\n"},
        pr={"app.py": "a = 1\nb = 99\nc = 3\nd = 4\n", "new dir/with space.txt": "hi\n"},
        delete=("old.txt",),
    )
    files = {f.path: f for f in git_changed_files(repo, base, head)}
    assert files["app.py"].added_lines == [2, 4]
    assert files["new dir/with space.txt"].status == "added"
    assert files["old.txt"].status == "deleted"
    assert "README.md" not in files


def _domains(tmp_path, pr, labels=None, base=None):
    repo, b, h = make_pr(tmp_path, base or {}, pr)
    return triage(repo, load_policy(ROOT / "policy.yml"), b, h, labels or [])["domains"]


def test_triage_docs_only_runs_only_security(tmp_path):
    assert _domains(tmp_path, {"docs/notes.md": "hello\n"}) == ["security"]


def test_triage_html_adds_accessibility(tmp_path):
    assert _domains(tmp_path, {"web/index.html": "<p>x</p>\n"}) == ["security", "accessibility"]


def test_triage_manifest_adds_enterprise_alignment(tmp_path):
    assert _domains(tmp_path, {"package.json": "{}\n"}) == ["security", "enterprise-alignment"]


def test_triage_label_forces_domain(tmp_path):
    assert "accessibility" in _domains(tmp_path, {"x.md": "x\n"}, labels=["a11y-review"])


def test_triage_ignores_vendored_paths(tmp_path):
    # Only node_modules changed: nothing to review at all.
    assert _domains(tmp_path, {"node_modules/x/index.js": "eval('1')\n"}) == []


def test_full_scan_lists_every_tracked_file(tmp_path):
    repo, _b, _h = make_pr(tmp_path, {"a.py": "x=1\n"}, {"b.py": "y=2\n"})
    data = triage(repo, load_policy(ROOT / "policy.yml"), full_scan=True)
    assert {f["path"] for f in data["files"]} == {"README.md", "a.py", "b.py"}
    assert all(f["added_lines"] is None for f in data["files"])
