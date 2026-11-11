"""The two GitHub API calls the governor needs, using only the standard library."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class GitHubError(RuntimeError):
    pass


def _request(method: str, path: str, token: str, body: dict[str, Any] | None = None) -> Any:
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    req = urllib.request.Request(
        base + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mcp-governance-poc",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raise GitHubError(f"{method} {path} -> {exc.code}: {exc.read().decode(errors='replace')[:300]}") from exc
    except urllib.error.URLError as exc:
        raise GitHubError(f"{method} {path} failed: {exc.reason}") from exc


def upsert_comment(repo: str, pr: int, body: str, token: str, marker: str) -> str:
    """Update the governor's existing comment on the PR, or create it. Returns 'updated' or 'created'."""
    page = 1
    while True:
        comments = _request("GET", f"/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}", token)
        for c in comments:
            if marker in (c.get("body") or ""):
                _request("PATCH", f"/repos/{repo}/issues/comments/{c['id']}", token, {"body": body})
                return "updated"
        if len(comments) < 100:
            break
        page += 1
    _request("POST", f"/repos/{repo}/issues/{pr}/comments", token, {"body": body})
    return "created"


def approvers(repo: str, pr: int, token: str) -> set[str]:
    """Logins whose latest review on the PR is an approval."""
    latest: dict[str, str] = {}
    page = 1
    while True:
        reviews = _request("GET", f"/repos/{repo}/pulls/{pr}/reviews?per_page=100&page={page}", token)
        for r in reviews:
            if r.get("user") and r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
                latest[r["user"]["login"]] = r["state"]
        if len(reviews) < 100:
            break
        page += 1
    return {login for login, state in latest.items() if state == "APPROVED"}
