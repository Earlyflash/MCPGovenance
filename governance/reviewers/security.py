"""Security reviewer (gate). Deterministic checks only; the guidance text comes from the security MCP."""

from __future__ import annotations

import re

from .base import Context, Hit

CODE_GLOBS = ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.go", "*.rb", "*.java", "*.sh", "*.yml", "*.yaml"]
DOCKERFILE_GLOBS = ["Dockerfile", "Dockerfile.*", "*.Dockerfile"]
TERRAFORM_GLOBS = ["*.tf"]

PROVIDER_TOKEN_PATTERNS = [
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
]
# Matches names such as password, DB_PASSWORD, apiKey_prod, "secret": in YAML, JSON, Python, JS and shell.
GENERIC_CREDENTIAL = re.compile(
    r"""(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\w*["']?\s*[:=]\s*(["'])(?P<v>[^"'\s]{8,})\1"""
)
PLACEHOLDER = re.compile(r"(?i)(\$\{|\{\{|<[^>]+>|changeme|change-me|example|placeholder|your[_-]|xxxx|\*{4})")

SHELL_TRUE = re.compile(r"\bsubprocess\.\w+\([^)]*shell\s*=\s*True")
OS_SYSTEM = re.compile(r"\bos\.system\s*\(")

TLS_DISABLED = [
    re.compile(r"\bverify\s*=\s*False\b"),
    re.compile(r"rejectUnauthorized\s*:\s*false"),
    re.compile(r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0"),
    re.compile(r"InsecureSkipVerify\s*:\s*true"),
]

PY_EVAL = re.compile(r"(?<![\w.])(?:eval|exec)\s*\(")
JS_EVAL = re.compile(r"(?<![\w.])eval\s*\(|\bnew\s+Function\s*\(")


def redact(value: str) -> str:
    return f"{value[:4]}…({len(value)} chars)"


def _is_comment(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("#") or s.startswith("//")


async def run_checks(ctx: Context) -> list[Hit]:
    hits: list[Hit] = []

    # SEC-001 hard-coded secrets: every text file, since a secret in a README is still a leaked secret.
    for f in ctx.live_files():
        for n, line in ctx.lines(f):
            for label, pat in PROVIDER_TOKEN_PATTERNS:
                m = pat.search(line)
                if m:
                    hits.append(Hit("SEC-001", f.path, n, evidence=f"{label}: {redact(m.group(0))}"))
            m = GENERIC_CREDENTIAL.search(line)
            if m and not PLACEHOLDER.search(m.group("v")):
                hits.append(Hit("SEC-001", f.path, n, evidence=f"hard-coded credential: {redact(m.group('v'))}"))

    for f in ctx.live_files(CODE_GLOBS):
        is_py = f.path.endswith(".py")
        is_js = f.path.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs"))
        for n, line in ctx.lines(f):
            if _is_comment(line):
                continue
            if is_py and (SHELL_TRUE.search(line) or OS_SYSTEM.search(line)):
                hits.append(Hit("SEC-002", f.path, n, evidence=line.strip()[:160]))
            for pat in TLS_DISABLED:
                if pat.search(line):
                    hits.append(Hit("SEC-003", f.path, n, evidence=line.strip()[:160]))
                    break
            if (is_py and PY_EVAL.search(line)) or (is_js and JS_EVAL.search(line)):
                hits.append(Hit("SEC-004", f.path, n, evidence=line.strip()[:160]))

    # SEC-005 containers must not run as root. Only the final build stage matters.
    for f in ctx.live_files(DOCKERFILE_GLOBS):
        last_from = 0
        user: str | None = None
        for n, line in ctx.lines(f):
            s = line.strip()
            if re.match(r"(?i)^FROM\s", s):
                last_from, user = n, None
            elif re.match(r"(?i)^USER\s", s):
                user = s.split(None, 1)[1].strip().split(":")[0]
        if last_from and (user is None or user.lower() in ("root", "0")):
            hits.append(Hit("SEC-005", f.path, last_from, evidence="final stage has no non-root USER"))

    # SEC-006 world-open network rules in Terraform.
    for f in ctx.live_files(TERRAFORM_GLOBS):
        for n, line in ctx.lines(f):
            if _is_comment(line):
                continue
            if "0.0.0.0/0" in line or "::/0" in line:
                hits.append(Hit("SEC-006", f.path, n, evidence=line.strip()[:160]))

    return hits
