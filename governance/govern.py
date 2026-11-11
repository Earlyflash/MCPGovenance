"""The governor: collates every domain's findings into one verdict.

It never re-reviews. It (1) applies each domain's declared mode, (2) fails closed when a required
reviewer did not report, (3) applies valid waivers, (4) notes places where several domains flag the
same line so a human looks at them together, and (5) sets a single pass/fail verdict.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml

from .findings import SEVERITY_RANK, effective_severity
from .globs import match


def load_waivers(path: Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).is_file():
        return []
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    items = doc.get("waivers") or []
    return [w for w in items if isinstance(w, dict)]


def _to_date(value: Any) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


def validate_waiver(w: dict[str, Any], policy: dict[str, Any], today: dt.date, approvals: set[str] | None) -> str | None:
    """Return None if the waiver is valid, otherwise why it is not."""
    cfg = policy["waivers"]
    missing = [k for k in ("rule_id", "reason", "approver", "expires") if not str(w.get(k) or "").strip()]
    if missing:
        return "missing " + ", ".join(missing)
    expires = _to_date(w["expires"])
    if expires is None:
        return f"expires '{w['expires']}' is not a date (use YYYY-MM-DD)"
    if expires < today:
        return f"expired on {expires.isoformat()}"
    if (expires - today).days > int(cfg["max_days"]):
        return f"expiry is {(expires - today).days} days away; the maximum is {cfg['max_days']}"
    if str(w["rule_id"]).upper() in {r.upper() for r in cfg.get("never_waivable", [])}:
        return f"{w['rule_id']} can never be waived"
    if cfg.get("require_approval") and str(w["approver"]).lower() not in {a.lower() for a in (approvals or set())}:
        return f"approver {w['approver']} has not approved this pull request"
    return None


def _synthetic(domain: str, rule_id: str, title: str, message: str, severity: str, owner: str = "unknown") -> dict[str, Any]:
    return {
        "domain": domain, "rule_id": rule_id, "title": title, "severity": severity, "message": message,
        "guidance_version": "unknown", "remediation": f"Re-run the workflow. If it keeps failing, contact the {domain} owner.",
        "owner": owner, "waiver_route": "", "file": None, "line": None, "evidence": "", "exemplar_good": "",
        "confidence": "high", "check_type": "deterministic",
    }


def govern(
    policy: dict[str, Any],
    triage: dict[str, Any],
    results_dir: Path,
    waivers: list[dict[str, Any]] | None = None,
    approvals: set[str] | None = None,
    today: dt.date | None = None,
) -> dict[str, Any]:
    today = today or dt.date.today()
    expected: list[str] = triage.get("domains", [])
    order = [d for d in policy.get("precedence", []) if d in policy["domains"]]
    order += [d for d in policy["domains"] if d not in order]

    findings: list[dict[str, Any]] = []
    domain_rows: dict[str, dict[str, Any]] = {}
    for d in expected:
        required = (policy["domains"].get(d) or {}).get("required", True)
        path = Path(results_dir) / f"findings-{d}.json"
        row = {"domain": d, "mode": "unknown", "owner": "unknown", "guidance_version": "unknown", "status": "missing", "waiver_route": ""}
        if not path.is_file():
            findings.append(_synthetic(d, "GOV-001", "Reviewer did not report",
                                       f"The {d} reviewer produced no result, so this domain could not be checked.",
                                       "block" if required else "warn"))
        else:
            res = json.loads(path.read_text(encoding="utf-8"))
            row.update(mode=res["mode"], owner=res["owner"], guidance_version=res["guidance_version"], status=res["status"])
            if res["status"] != "ok":
                findings.append(_synthetic(d, "GOV-002", "Reviewer failed", f"The {d} reviewer failed: {res.get('error', 'unknown error')}",
                                           "block" if required else "warn", res["owner"]))
            for f in res["findings"]:
                row["waiver_route"] = row["waiver_route"] or f.get("waiver_route", "")
                findings.append(f)
        domain_rows[d] = row

    for f in findings:
        mode = domain_rows[f["domain"]]["mode"]
        f["effective_severity"] = effective_severity(f["severity"], mode)
        f["capped"] = f["effective_severity"] != f["severity"]
        f["waived"] = False

    # Waivers
    problems: list[dict[str, str]] = []
    valid: list[dict[str, Any]] = []
    for w in waivers or []:
        why = validate_waiver(w, policy, today, approvals)
        if why:
            problems.append({"rule_id": str(w.get("rule_id", "?")), "problem": why})
        else:
            valid.append(w)
    for f in findings:
        if f["effective_severity"] == "info":
            continue
        for w in valid:
            if str(w["rule_id"]).upper() == f["rule_id"].upper() and match(f.get("file") or "", w.get("path", "**")):
                f["waived"] = True
                f["waiver"] = {"reason": w["reason"], "approver": w["approver"], "expires": str(_to_date(w["expires"]))}
                break

    active = [f for f in findings if not f["waived"]]
    counts = {s: sum(1 for f in active if f["effective_severity"] == s) for s in ("block", "warn", "info")}
    counts["waived"] = sum(1 for f in findings if f["waived"])

    # Several domains on one line: not a pass/fail matter, but a human should read them together.
    by_loc: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for f in active:
        if f.get("file") and f.get("line") and f["effective_severity"] in ("warn", "block"):
            by_loc.setdefault((f["file"], f["line"]), []).append(f)
    escalations = [
        {"file": loc[0], "line": loc[1], "domains": sorted({x["domain"] for x in fs}), "rules": sorted({x["rule_id"] for x in fs})}
        for loc, fs in by_loc.items() if len({x["domain"] for x in fs}) > 1
    ]

    for d, row in domain_rows.items():
        mine = [f for f in active if f["domain"] == d]
        row["counts"] = {s: sum(1 for f in mine if f["effective_severity"] == s) for s in ("block", "warn", "info")}
        row["counts"]["waived"] = sum(1 for f in findings if f["domain"] == d and f["waived"])

    would_fail = counts["block"] > 0
    warn_only = policy["enforcement"]["mode"] == "warn-only"
    if would_fail and not warn_only:
        verdict = "fail"
    elif would_fail or counts["warn"] > 0:
        verdict = "pass-with-warnings"
    else:
        verdict = "pass"

    rank = {d: i for i, d in enumerate(order)}
    findings.sort(key=lambda f: (rank.get(f["domain"], 99), -SEVERITY_RANK[f["effective_severity"]], f.get("file") or "", f.get("line") or 0))

    return {
        "verdict": verdict,
        "would_fail": would_fail,
        "enforcement": policy["enforcement"]["mode"],
        "counts": counts,
        "domains": [domain_rows[d] for d in order if d in domain_rows],
        "not_triggered": [d for d in order if d not in expected],
        "escalations": escalations,
        "waiver_problems": problems,
        "findings": findings,
    }
