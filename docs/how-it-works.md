# How it works, and what matters about it

This is the explanation behind the [README](../README.md): why the design is shaped the way it is, what happens
on a pull request step by step, and which properties must survive any future change.

## The problem

Technology governance usually reaches engineers as a document to read or a review meeting to book. Both come too
late or never. AI coding agents make it worse: they write more code, faster, and will pick whatever framework is
most familiar unless something tells them what the organisation has approved.

The aim here is to bring each governance area's guidance into the pull request itself, as short, specific,
actionable feedback, in a form that **a person and an AI agent can both act on**.

## The idea in one paragraph

Each governance area (security, accessibility, enterprise alignment, and later FinOps, design, user research...)
owns a small **knowledge server** that says what "good" looks like. An independent **reviewer** for that area
checks the pull request against it. A **governor** collects every reviewer's findings, applies the organisation's
rules about how strict each area is, and produces one comment and one pass/fail check. Areas never depend on each
other; only the governor sees all of them.

## What happens on a pull request

1. **Trigger.** The consuming repo's small `governance.yml` calls the reusable workflow
   [`governed-pr.yml`](../.github/workflows/governed-pr.yml) on every PR event.
2. **Triage** (`governed / triage`). Reads `policy.yml` and the changed files and labels, and decides which
   domains apply. A docs-only change runs only security; a change to `package.json` also runs enterprise alignment.
3. **Review** (`governed / review (<domain>)`, one parallel job per domain). Each job starts that domain's MCP
   server, asks it for rules, guidance, exemplars and the deviation route, runs the domain's checks against the
   diff, and uploads its findings as an artifact in the common schema.
4. **Govern** (`governed / governor`). Downloads every domain's findings and the triage result and:
   - checks every required domain reported (fail closed),
   - applies each domain's mode (gate, advise, evidence),
   - applies waivers and the rollout setting,
   - flags findings from different domains that sit on the same line,
   - upserts **one** PR comment and sets **one** check result.
5. **Fix.** The author (or their AI agent) reads the comment. Each finding says what was found, why it matters,
   how to fix it, what good looks like, who owns the rule, and how to ask for an exception. A machine-readable
   JSON block in the comment lets an agent repair its own PR.

## The three layers

| Layer | Question it answers | Owned by | Changes when |
| --- | --- | --- | --- |
| Knowledge | What does good look like here? | Each domain team | The domain's guidance changes |
| Judgment | Does this change meet it? | Each domain team | Detection improves |
| Synthesis | What does the organisation do with all the answers? | OCTO / platform | Governance policy changes |

Keeping these apart is the central design choice. A domain team can update its rules without touching CI. The
platform can tighten policy without understanding accessibility. Neither can quietly weaken the other.

## Domain modes

| Mode | Use when | Effect |
| --- | --- | --- |
| `gate` | The domain may stop a merge | Rule severities apply as written |
| `advise` | The domain is new or its checks are noisy | A `block` is shown as a warning |
| `evidence` | The domain wants proof a decision was made, not a verdict on it | Rule severities apply, but only to whether evidence exists |

New domains should start as `advise` and move to `gate` by changing one line, once their findings have earned
trust. Enterprise alignment is deliberately `evidence`: the pipeline requires an ADR for off-road technology, but
it does not decide whether the choice was wise. That judgment stays with people.

## Product stages

Guardrails are staged to the maturity of the product: 🔍 scan → 🧪 pilot → 🚀 production. Each rule names the stage
it starts to apply in (`applies_from`) and applies to every later stage. A product declares its stage in
`.governance.yml`, a README marker, or a platform-set repository variable. Triage works out the stage (the strictest
declaration wins, nothing declared means production, and a pull request can raise but never lower it). The
governor then treats findings for later-stage guardrails as a preview: shown, never counted. A rule can also get stricter at a later stage (`escalate`), for example warning at pilot and blocking in production. Raising the stage
triggers a full-repository promotion scan. See [guardrails.md](guardrails.md) for the picture.

## Properties that matter

These are the parts to protect when changing the system.

- **One source of truth for humans, CI and agents.** Reviewers call the same MCP tools an AI agent would. If an
  agent can read the guidance before it writes code, the PR check becomes a confirmation, not a surprise.
- **Every finding is traceable.** Each carries a `guidance_version` (knowledge version plus a content hash), so you
  can always say which version of which guidance produced it. This matters when guidance changes often.
- **Fail closed.** A crashed or missing required reviewer fails the check (`GOV-001` missing, `GOV-002` crashed).
  A governance system that passes when it breaks is worse than none. Optional domains only warn.
- **Policy lives out of reach of the PR author.** `policy.yml`, domain modes and rule text sit in this repo, not
  the repo being reviewed. A PR cannot loosen the rules that judge it. Waivers are the one thing a PR can add, which
  is why they are visible, dated, capped at 90 days and (once a second approver exists) approved.
- **Waivers are visible, not hidden.** A waived finding stays in the comment with its reason, approver and expiry.
  `SEC-001` (hard-coded secrets) can never be waived.
- **Domains are autonomous.** A reviewer never reads another reviewer's output. Disagreement between domains is
  surfaced as "Review together" for a human; the governor does not arbitrate.
- **Judge the change, not the history.** Diff mode reports only what the PR added. Dependency changes are compared
  against the base commit so editing a neighbouring line does not make an old dependency look new. A scheduled full
  scan covers the rest.
- **One comment, one check.** The comment is updated in place (marker `<!-- governance-governor:v1 -->`). Branch
  protection requires only `governed / governor`, so adding or removing a domain never changes repo settings.
- **Untrusted input is treated as text.** Reviewers never execute PR code, do not follow symlinks, and limit file
  sizes. Workflow inputs go through environment variables, not string interpolation, to avoid script injection.
- **Deterministic first.** Every PoC check is a plain, reproducible rule. People trust a gate they can predict.

## Verified behaviour

On the demo app, six pull requests ran on real GitHub-hosted runners and produced the expected outcomes: docs-only
passed (security only); an approved dependency passed; hard-coded secret, disabled TLS verification and `eval`
blocked; an inaccessible page passed with seven warnings; a banned package without an ADR blocked; and a shell call
with a valid waiver passed with the waiver listed. See the
[demo repo](https://github.com/Earlyflash/MCPGovenance-DemoApp) for each PR.

## What this is not

- **Not a replacement for human review.** It removes the checkable, repetitive part so reviewers spend time on
  judgment.
- **Not production-ready content.** Rule text, owners and the technology catalogue are placeholders.
- **Not LLM-based.** That is a deliberate first step. See below for how an LLM reviewer would fit.

## Where it goes next

| Step | What changes | What stays the same |
| --- | --- | --- |
| Real content | Domain teams replace example rules and the technology catalogue, ideally exported from the docs site | Contract, schema, governor |
| Better detectors | Wrap Semgrep, Checkov, axe, Infracost inside reviewers | Finding schema |
| Judgment domains | Add LLM reviewers (design, user research) with `check_type: agent`, low confidence, `warn` severity until trusted | Governor and comment |
| Shared endpoints | Replace the stdio subprocess with remote streamable-HTTP MCP servers on EKS behind Entra via OIDC (change `mcp_client.open_domain`), so agents and CI read the same live endpoint | Tool contract |
| Enforcement | Add a ruleset requiring `governed / governor`; enable `require_approval` for waivers; pin the workflow to a tag | Consumer workflow |
| Agent-side | Point Copilot instructions at the same MCP endpoints so decisions are informed before the PR | Everything above |

## Pitfalls seen while building it

- An unpinned `mcp` install jumped from 1.x to 2.x, which renamed `FastMCP` to `MCPServer` and `isError` to `is_error`. It is now pinned `>=2,<3`: the import is `mcp.server.mcpserver.MCPServer` and results use `is_error`.
- A technology lookup must be restricted to the requested ecosystem, or an npm package can match a Python one.
- A JSON dependency added at the end of a list also edits the previous line (trailing comma); compare dependency
  sets rather than lines.
- Secret patterns need to catch names like `DB_PASSWORD`, not just `password`.
- Composite actions resolve their own files with `github.action_path`, not the caller's workspace.
