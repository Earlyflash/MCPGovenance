# MCPGovenance: PR governance proof of concept

A pull request is reviewed by several **autonomous domain reviewers** (security, accessibility, enterprise
alignment). Each one pulls "what good looks like" from its **own MCP server**, reports findings in one common
schema, and a **governor** collates everything into a single PR comment and a single pass/fail check.

The demo consumer is [MCPGovenance-DemoApp](https://github.com/Earlyflash/MCPGovenance-DemoApp).

For the reasoning, the step-by-step flow and the properties to protect, read [docs/how-it-works.md](docs/how-it-works.md). To add rules, change policy or add a new area, read [docs/extending.md](docs/extending.md).

**Guides by audience:** [for governance teams](docs/for-governance-teams.md) (writing policy, approving changes and waivers) and [for developers](docs/for-developers.md) (reading the comment, fixing findings, asking for a waiver).

```
 pull request
      │
   triage ── decides which domains apply from changed paths and labels (policy.yml)
      │
      ├── security reviewer ──────────┐   each reviewer runs in its own job and
      ├── accessibility reviewer ─────┤   asks ITS OWN MCP server for guidance,
      └── enterprise-alignment ───────┤   exemplars and the deviation route
                                      ▼
                                  governor ── applies each domain's mode, waivers and rollout settings,
                                      │       posts ONE comment, passes or fails ONE required check
                                      ▼
                         PR author sees what, why, how to fix, who to ask
```

## The three layers

| Layer | What it is | Where |
| --- | --- | --- |
| **Knowledge** | One MCP server per domain, same tool contract, content is plain YAML owned by that domain's team | `domains/<id>/` |
| **Judgment** | One autonomous reviewer per domain. Deterministic checks detect; the MCP explains | `governance/reviewers/` |
| **Synthesis** | The governor: modes, fail-closed, waivers, collation, one verdict | `governance/govern.py`, `policy.yml` |

### The knowledge layer: one contract, every domain

Every domain MCP server offers `get_domain_info`, `list_rules`, `get_guidance`, `get_exemplars` and
`get_deviation_route`. Domains may add tools: enterprise alignment adds `check_technology` and
`list_technologies`. Reviewers use the same tools an AI agent would, so CI and Copilot read one source of truth.
Each answer carries a `guidance_version` (the knowledge version plus a content hash), so every finding says exactly
which guidance it came from.

### Domain modes

| Mode | Meaning | Governor behaviour | Example |
| --- | --- | --- | --- |
| `gate` | Rules can block a merge | Severities used as declared | security |
| `advise` | Guidance only | `block` is capped at `warn` | accessibility |
| `evidence` | Checks that evidence exists, never judges it | Severities as declared by the rule | enterprise alignment (needs an ADR; does not decide if the choice is wise) |

Flipping `mode` in a domain's `domain.yml` from `advise` to `gate` makes its existing rules block, with no other change.

### The common finding

Every reviewer emits the same record ([`schemas/finding.schema.json`](schemas/finding.schema.json)): domain, rule id,
severity, file and line, evidence (secrets redacted), guidance version, remediation, a "what good looks like"
exemplar, owner, confidence, check type and waiver route. A machine-readable copy is embedded in the PR comment so an
AI agent such as the Copilot coding agent can fix its own PR.

## What each domain checks in this PoC

| Domain | Mode | Rules |
| --- | --- | --- |
| security | gate | SEC-001 hard-coded secrets (never waivable), SEC-002 shell execution, SEC-003 TLS verification off, SEC-004 `eval`/`exec`, SEC-005 container runs as root, SEC-006 world-open Terraform rules |
| accessibility | advise | A11Y-001 image alt, -002 page language, -003 form labels, -004 vague link text, -005 page title, -006 unnamed buttons |
| enterprise-alignment | evidence | EA-001 banned technology, -002 deprecated, -003 not in catalogue, -004 trial or tolerated, -005 off-road technology needs an ADR, -006 ADR incomplete |

All checks are deterministic. The catalogue and the rule text are **example content**; replace them with your own.

## Behaviours worth knowing

- **Diff mode.** A PR is only judged on what it changed. Dependencies are compared against the base commit, because adding one JSON entry also edits the line above it. A scheduled full scan (`full-scan: true`) judges everything.
- **Fails closed.** If a required reviewer crashes or never reports, the governor fails the check (`GOV-001`/`GOV-002`) instead of passing silently. Optional domains only warn.
- **Waivers.** `.governance-waivers.yml` in the PR's repo: `rule_id`, optional `path`, `reason`, `approver`, `expires` (max 90 days). Waived findings stay visible in the comment. `SEC-001` can never be waived. Set `waivers.require_approval: true` in `policy.yml` once a second reviewer exists: the named approver must then have approved the PR.
- **Rollout.** `enforcement.mode: warn-only` reports "would be blocked" without failing, for onboarding a repository.
- **Co-located findings.** When two domains flag the same line, the comment says "Review together" so a person reconciles them. The governor does not try to out-argue a domain.
- **Untrusted input.** Reviewers read PR files as text only (no execution, no symlinks, size limits). Policy and guidance live in this repo, so a PR author cannot loosen the rules that judge their own change. Waivers live in the PR, which is why approval matters.

## Adopt it in a repository

1. Add `.github/workflows/governance.yml`:

   ```yaml
   name: governance
   on:
     pull_request:
   permissions:
     contents: read
     pull-requests: write
   concurrency:
     group: governance-${{ github.event.pull_request.number }}
     cancel-in-progress: true
   jobs:
     governed:
       uses: Earlyflash/MCPGovenance/.github/workflows/governed-pr.yml@main
   ```

2. Create a branch ruleset that requires the status check **`governed / governor`** (check the exact name in a first run's Checks tab). Domain jobs stay informational, so adding or retiring a domain never touches branch protection.
3. Optional: add `docs/adr/` with the ADR template and a `.governance-waivers.yml`.

The repository is public, so no sharing settings are needed. If you make it private, enable **Settings → Actions → General → Access** so other repositories can use its workflows and actions. Pin `@main` to a tag or SHA once you stop iterating.

## Run it locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest                                        # 68 tests, including real MCP sessions and git runs

# Judge a branch in any git repo, exactly as CI would:
python -m governance local --repo /path/to/repo --base main --head HEAD

# Judge a whole repo (the nightly full scan):
python -m governance local --repo /path/to/repo --full-scan

# Talk to a domain's MCP server yourself:
PYTHONPATH=. python domains/security/mcp_server.py      # stdio MCP server
```

## Add a domain (for example FinOps)

1. `domains/finops/domain.yml` (id, title, mode, owner, waiver route) and `domains/finops/knowledge/rules.yml`.
2. `domains/finops/mcp_server.py`: three lines, copy another domain's.
3. `governance/reviewers/finops.py` with `async def run_checks(ctx) -> list[Hit]`.
4. Add the domain to `policy.yml` with its `paths`/`labels`. No workflow changes are needed.
5. Add tests next to `tests/test_reviewers.py`.

## What this PoC deliberately does not do yet

- **No LLM judgment.** Reviewers are deterministic. Where a domain needs interpretation (design, user research), add a reviewer that calls an LLM through your gateway and still emits the same finding schema with `check_type: agent`. Keep its confidence honest and its severity at `warn` until it has earned trust.
- **Local stdio MCP servers.** Each reviewer job starts its domain's server as a subprocess. Production would point at remote streamable-HTTP endpoints, owned and released by each domain team, behind Entra via OIDC. The tool contract does not change, only `mcp_client.open_domain`.
- **Heuristic detectors.** Regex and HTML parsing stand in for tools such as Semgrep, Checkov, axe or Infracost. Wrap those tools in the reviewer instead; they will be better. Because `SEC-001` is never waivable, a false positive there has to be fixed in code, which is intentional but worth watching.
- **GitHub-hosted runners.** No EKS needed. Self-hosted runners only matter once domain endpoints are private services.
- **Fork pull requests** get a read-only token, so the comment cannot be posted; the check result and job summary still work.
- **Example content.** Rule text, owners, contacts and the technology catalogue are placeholders.
