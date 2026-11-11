"""Make demonstration data for the demand layer by really calling the three domain MCP servers.

    python scripts/simulate_demand.py --calls 1000 --out demand-demo

Every call goes through a real MCP session, so the servers record it exactly as they would for a real agent.
The questions, teams and assistants are invented. After the run, the timestamps are spread over the last
--days days so the daily chart is meaningful (a live run would take only seconds). Then it writes
demand.jsonl and demand.html in the output folder.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

from governance import demand  # noqa: E402
from governance.mcp_client import open_domain  # noqa: E402

CALLERS = {"copilot": 10, "claude-code": 7, "cursor": 4, "chat-assistant": 3, "developer-cli": 2}
REPOS = {"payments-api": "production", "identity-service": "production", "web-portal": "pilot",
         "mobile-app": "pilot", "data-platform": "pilot", "reporting": "scan", "internal-tools": "scan"}

# (question, weight). Anything the knowledge does not cover is a gap; the weights make a few gaps stand out.
SECURITY = [("SEC-001", 6), ("hard-coded secret", 5), ("tls certificate verify", 4), ("eval injection", 3), ("docker root user", 4),
            ("subprocess shell command", 3), ("network ingress cidr", 2),
            ("kafka message queue", 9), ("rate limiting", 7), ("logging standards", 6), ("encryption at rest", 5),
            ("api key rotation", 4), ("oauth scopes", 3), ("sbom", 2), ("data retention", 2), ("pen testing", 1)]
ACCESS = [("images alt text", 6), ("link text", 4), ("form labels", 4), ("page title", 3), ("button accessible name", 3),
          ("html lang", 2), ("colour contrast", 7), ("keyboard navigation", 6), ("aria labels", 4), ("video captions", 3),
          ("focus order", 3), ("pdf accessibility", 2)]
TECH = [("flask", 5), ("react", 5), ("fastapi", 4), ("postgresql", 5), ("express", 3), ("jquery", 3), ("moment", 3), ("event-stream", 1),
        ("htmx", 2), ("celery", 7), ("redis", 6), ("kafka", 7), ("mongodb", 5), ("graphql", 4), ("svelte", 3), ("terraform", 3), ("rabbitmq", 3)]
ECOSYSTEM = {"flask": "pip", "fastapi": "pip", "celery": "pip", "moment": "npm", "react": "npm", "express": "npm", "jquery": "npm",
             "event-stream": "npm", "htmx": "npm", "svelte": "npm", "graphql": "npm", "postgresql": None, "redis": "docker",
             "mongodb": "docker", "kafka": "docker", "terraform": "pip", "rabbitmq": "docker"}
RULES = {"security": ["SEC-001", "SEC-002", "SEC-005"], "accessibility": ["A11Y-001", "A11Y-002"], "enterprise-alignment": ["EA-001", "EA-003"]}


def pick(rng: random.Random, pool):
    return rng.choices([q for q, _ in pool], weights=[w for _, w in pool])[0]


async def session(domain: str, caller: str, repo: str, n: int, rng: random.Random) -> None:
    os.environ["GOVERNANCE_CALLER"], os.environ["GOVERNANCE_REPO"], os.environ["GOVERNANCE_STAGE"] = caller, repo, REPOS[repo]
    async with open_domain(domain, ROOT) as mcp:
        for _ in range(n):
            if domain == "enterprise-alignment" and rng.random() < 0.7:
                name = pick(rng, TECH)
                await mcp.call("check_technology", name=name, ecosystem=ECOSYSTEM[name])
            elif rng.random() < 0.15:
                await mcp.call("get_exemplars", rule_id=rng.choice(RULES[domain]))
            else:
                pool = {"security": SECURITY, "accessibility": ACCESS, "enterprise-alignment": [("technology radar", 2), ("decision record", 4), ("assessment route", 3), ("cloud region policy", 2)]}[domain]
                await mcp.call("get_guidance", query=pick(rng, pool))


async def main_async(a: argparse.Namespace) -> Path:
    rng = random.Random(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "demand.jsonl"
    log.unlink(missing_ok=True)
    os.environ["GOVERNANCE_DEMAND_LOG"] = str(log)
    done = 0
    while done < a.calls:
        n = min(rng.randint(8, 20), a.calls - done)
        domain = rng.choices(["security", "accessibility", "enterprise-alignment"], weights=[5, 3, 4])[0]
        await session(domain, rng.choices(list(CALLERS), weights=list(CALLERS.values()))[0], rng.choice(list(REPOS)), n, rng)
        done += n
        print(f"\r{done}/{a.calls} calls", end="", file=sys.stderr)
    print(file=sys.stderr)
    rows = demand.load([log])
    now = dt.datetime.now(dt.timezone.utc)
    for r in rows:  # spread over the period, a little busier on weekdays and recently
        while True:
            back = int(rng.triangular(0, a.days, 0))
            day = now - dt.timedelta(days=back, hours=rng.randint(0, 9), minutes=rng.randint(0, 59))
            if day.weekday() < 5 or rng.random() < 0.15:
                break
        r["ts"] = day.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows.sort(key=lambda r: r["ts"])
    log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (out / "demand.html").write_text(demand.render_html(demand.summarise(rows, 8)), encoding="utf-8")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--calls", type=int, default=1000)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default="demand-demo")
    out = asyncio.run(main_async(p.parse_args()))
    print(f"wrote {out / 'demand.jsonl'} and {out / 'demand.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
