"""Enterprise-alignment guidance MCP server (stdio).

Adds two tools to the common contract:
  check_technology(name, ecosystem?) - is this framework/library/image on the approved catalogue?
  list_technologies(status?)         - browse the catalogue (the paved road)
"""

import json
import re
from pathlib import Path

import yaml

from governance.domain_mcp import build_server

DOMAIN_DIR = Path(__file__).parent
mcp, knowledge = build_server(DOMAIN_DIR)
CATALOGUE = yaml.safe_load((DOMAIN_DIR / "knowledge" / "technology.yml").read_text(encoding="utf-8"))["technologies"]
PERMITTED = ("adopt", "approved")


def _norm(name: str, ecosystem: str | None) -> str:
    n = name.strip().lower()
    return re.sub(r"[-_.]+", "-", n) if ecosystem in (None, "pip") else n


def _lookup(name: str, ecosystem: str | None):
    for entry in CATALOGUE:
        detection = entry.get("detection", {})
        if ecosystem:
            # Only entries that exist in this ecosystem can match: "flask" is not an npm package.
            if ecosystem not in detection:
                continue
            names = {_norm(x, ecosystem) for x in detection[ecosystem]}
        else:
            names = {_norm(x, None) for pool in detection.values() for x in pool}
            names |= {_norm(entry["id"], None)} | {_norm(a, None) for a in entry.get("aliases", [])}
        if _norm(name, ecosystem) in names:
            return entry
    return None


@mcp.tool()
def check_technology(name: str, ecosystem: str | None = None) -> str:
    """Check whether a framework, library, runtime or base image is approved. ecosystem is pip, npm or
    docker. Call this BEFORE adding or choosing any technology. A name that is not in the catalogue is
    NOT permitted: the answer says found=false and how to request an assessment."""
    entry = _lookup(name, ecosystem)
    if entry is None:
        return json.dumps({
            "found": False, "name": name, "ecosystem": ecosystem, "permitted": False,
            "assessment_route": knowledge.info["assessment_route"].strip(),
            "guidance_version": knowledge.version,
        })
    return json.dumps({
        "found": True, "id": entry["id"], "name": entry["name"], "category": entry["category"],
        "status": entry["status"], "permitted": entry["status"] in PERMITTED,
        "conditions": entry.get("conditions", ""), "reason": entry.get("reason", ""),
        "preferred_alternative": entry.get("preferred_alternative", ""),
        "owner": entry.get("owner", ""), "last_reviewed_on": str(entry.get("last_reviewed_on", "")),
        "guidance_version": knowledge.version,
    })


@mcp.tool()
def list_technologies(status: str | None = None) -> str:
    """List the technology catalogue (the paved road), optionally filtered by status: adopt, approved,
    trial, tolerated, deprecated or banned."""
    rows = [
        {"id": e["id"], "name": e["name"], "category": e["category"], "status": e["status"]}
        for e in CATALOGUE if status is None or e["status"] == status
    ]
    return json.dumps({"guidance_version": knowledge.version, "technologies": rows})


if __name__ == "__main__":
    mcp.run()
