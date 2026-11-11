"""Enterprise-alignment reviewer (evidence mode).

It does not judge whether a technology choice is wise. It checks the choice against the approved
catalogue (asked of the domain's MCP server, ``check_technology``) and, when a PR introduces
something that is not on the paved road, asks for evidence: an ADR that records the guidance consulted,
the deviation and any tension with strategy.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass

from ..diff import ChangedFile
from .base import Context, Hit

ADR_GLOB = "docs/adr/*.md"
REQUIRED_ADR_HEADINGS = ["guidance consulted", "deviations requiring approval", "tensions with strategy"]


@dataclass
class Dep:
    name: str
    ecosystem: str  # pip | npm | docker
    file: str
    line: int


def _line_of(text: str, needle: str) -> int:
    for n, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return n
    return 1


def _norm_pip(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(path: str, text: str) -> list[Dep]:
    deps = []
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "http://", "https://", "git+")):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if m:
            deps.append(Dep(_norm_pip(m.group(1)), "pip", path, n))
    return deps


def parse_pyproject(path: str, text: str) -> list[Dep]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    specs = list(data.get("project", {}).get("dependencies", []))
    for group in data.get("project", {}).get("optional-dependencies", {}).values():
        specs.extend(group)
    deps = []
    for spec in specs:
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
        if m:
            deps.append(Dep(_norm_pip(m.group(1)), "pip", path, _line_of(text, m.group(1))))
    return deps


def parse_package_json(path: str, text: str) -> list[Dep]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    deps = []
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name in (data.get(section) or {}):
            deps.append(Dep(name.lower(), "npm", path, _line_of(text, f'"{name}"')))
    return deps


def parse_dockerfile(path: str, text: str) -> list[Dep]:
    deps = []
    for n, raw in enumerate(text.splitlines(), start=1):
        m = re.match(r"(?i)^\s*FROM\s+(?:--\S+\s+)*(\S+)", raw)
        if not m:
            continue
        image = m.group(1)
        if image.lower() == "scratch" or "$" in image:
            continue
        name = image.split("@", 1)[0].rsplit(":", 1)[0] if ":" in image.rsplit("/", 1)[-1] else image.split("@", 1)[0]
        deps.append(Dep(name.rsplit("/", 1)[-1].lower(), "docker", path, n))
    return deps


def _parser_for(path: str):
    base = path.rsplit("/", 1)[-1]
    if re.match(r"^requirements.*\.txt$", base):
        return parse_requirements
    if base == "pyproject.toml":
        return parse_pyproject
    if base == "package.json":
        return parse_package_json
    if base == "Dockerfile" or base.startswith("Dockerfile.") or base.endswith(".Dockerfile"):
        return parse_dockerfile
    return None


def detect_deps(ctx: Context) -> list[tuple[Dep, bool]]:
    """Every direct dependency in the changed manifests, each with 'is it new in this PR?'.

    "New" means absent from the same file at the base commit. Comparing dependency sets rather than diff
    lines matters: adding one JSON entry also edits the trailing comma of the entry above it.
    """
    out: list[tuple[Dep, bool]] = []
    for f in ctx.live_files():
        parser = _parser_for(f.path)
        text = ctx.read(f) if parser else None
        if parser is None or text is None:
            continue
        old_text = ctx.base_text(f.path)
        old = {(d.ecosystem, d.name) for d in parser(f.path, old_text)} if old_text else set()
        for dep in parser(f.path, text):
            out.append((dep, not ctx.full and (dep.ecosystem, dep.name) not in old))
    return out


def check_adr(f: ChangedFile, text: str) -> list[Hit]:
    hits = []
    lowered = text.lower()
    # ADR problems are about the document as a whole, so pin them to a line this PR touched.
    anchor = f.added_lines[0] if f.added_lines else 1
    missing = [h for h in REQUIRED_ADR_HEADINGS if not re.search(rf"^#+\s*{re.escape(h)}\b", lowered, re.M)]
    if missing:
        hits.append(Hit("EA-006", f.path, anchor, evidence="missing sections: " + ", ".join(missing)))
    tbd_line = next((n for n, line in enumerate(text.splitlines(), start=1) if re.search(r"\bTBD\b", line)), None)
    if tbd_line:
        hits.append(Hit("EA-006", f.path, tbd_line, evidence="ADR still contains TBD"))
    return hits


async def run_checks(ctx: Context) -> list[Hit]:
    hits: list[Hit] = []
    new_off_road: list[Dep] = []
    seen: set[tuple[str, str, str]] = set()

    for dep, is_new in detect_deps(ctx):
        if not (is_new or ctx.full):
            continue  # diff mode: only judge what this PR introduced
        key = (dep.ecosystem, dep.name, dep.file)
        if key in seen:
            continue
        seen.add(key)
        answer = await ctx.mcp.call("check_technology", name=dep.name, ecosystem=dep.ecosystem)
        label = f"{dep.name} ({dep.ecosystem})"
        if not answer["found"]:
            hits.append(Hit("EA-003", dep.file, dep.line, evidence=f"{label} is not in the technology catalogue",
                            detail=answer.get("assessment_route", "")))
            if is_new:
                new_off_road.append(dep)
            continue
        status = answer["status"]
        extra = {k: answer.get(k) for k in ("status", "preferred_alternative", "reason", "conditions")}
        alt = f" Preferred: {answer['preferred_alternative']}." if answer.get("preferred_alternative") else ""
        reason = f" {answer['reason']}." if answer.get("reason") else ""
        if status == "banned":
            hits.append(Hit("EA-001", dep.file, dep.line, evidence=f"{label} is banned.{reason}{alt}", extra=extra))
        elif status == "deprecated":
            hits.append(Hit("EA-002", dep.file, dep.line, evidence=f"{label} is deprecated.{reason}{alt}", extra=extra))
            if is_new:
                new_off_road.append(dep)
        elif status in ("trial", "tolerated"):
            cond = f" Conditions: {answer['conditions']}." if answer.get("conditions") else ""
            hits.append(Hit("EA-004", dep.file, dep.line, evidence=f"{label} is {status}.{cond}", extra=extra))
            if status == "trial" and is_new:
                new_off_road.append(dep)

    adr_files = [
        f for f in ctx.live_files([ADR_GLOB])
        if "template" not in f.path.rsplit("/", 1)[-1].lower()
    ]
    if new_off_road and not adr_files:
        first = new_off_road[0]
        names = ", ".join(sorted({d.name for d in new_off_road}))
        hits.append(Hit("EA-005", first.file, first.line,
                        evidence=f"new off-road technology ({names}) but no ADR found under docs/adr/"))
    for f in adr_files:
        text = ctx.read(f)
        if text is not None:
            hits.extend(check_adr(f, text))
    return hits
