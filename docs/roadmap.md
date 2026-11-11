# Roadmap: ideas worth keeping, not committed to build

This is a menu of good ideas for where PR governance could go. None of it is planned or scheduled. Each idea says
what it is, why it is worth doing, what it needs first, and how you would know it is working. They are grouped by
horizon, which is a judgment about **dependency and value**, not a delivery date.

## Principles any new idea should respect

These are what make the current design trustworthy. An idea that breaks one of them needs a very good reason.

1. **Domains stay autonomous.** Areas own their guidance and checks. Only the governor sees all of them.
2. **Fail closed, and be visible.** A broken check never looks like a pass. Exceptions are dated and shown.
3. **Policy sits out of reach of the thing it judges.** A PR author cannot loosen the rules that judge their PR.
4. **Humans read policy, machines read rules, and they link.** Every finding leads back to the plain-language policy.
5. **Deterministic first, judgment advisory.** Anything an AI judges starts as advice until it has earned trust.
6. **Earn strictness.** New rules arrive quietly and tighten as evidence shows they are right.

## Summary

| Horizon | Theme | Ideas |
| --- | --- | --- |
| **Foundations** (make what exists trustworthy at scale) | Control and safety | A1 Shadow rules · A2 Base-branch waivers and a waiver register · A3 Rule impact preview · A4 Org-wide required check |
| **Next** (high value once foundations exist) | Knowledge and visibility | B1 Remote domain endpoints · B2 Policy-to-rules drafting · B3 Estate dashboard · B4 Agent pre-flight · B5 Fix suggestions |
| **Later** (strategic bets) | Reach and intelligence | C1 Judgment reviewers · C2 Strategy alignment · C3 Risk tiers alongside stages · C4 Beyond the PR · C5 New domains |
| **Always** | Quality of the system itself | D1 Rule quality scores · D2 Release rings for guidance · D3 Audit trail |

---

## Foundations

### A1. Shadow rules
**What:** a rule can run in *shadow* mode: it executes on every PR and records what it would have said, but shows
nothing to authors and counts for nothing. After a trial period the owner reviews the results and promotes it to
`warn` or `block`.
**Why:** the biggest risk to trust is a noisy or wrong rule. Shadowing lets an owner measure false positives on
real code before anyone is affected, which makes strict rules politically easy to introduce.
**Needs:** somewhere to store shadow results (job artifacts are enough to begin; a store later).
**Working when:** nearly every new `block` rule has a shadow period behind it, and the false-positive rate at
promotion is known.

### A2. Base-branch waivers and a waiver register
**What:** two things. (1) Read waivers only from the base branch, with a request flow that creates the waiver PR
first, so an unapproved waiver can never count. (2) A register of every waiver across the estate with owner,
reason, expiry, and automatic reminders before expiry.
**Why:** today a waiver in a PR counts for that PR and is only held back by CODEOWNERS. A register turns waivers
from scattered files into something governance can actually manage, and expiring ones get noticed.
**Needs:** a way to scan repos for the waiver file; a notification channel.
**Working when:** nothing is waived without prior approval, and no waiver is ever silently expired or forgotten.

### A3. Rule impact preview
**What:** before merging a change to a rule (new rule, stage change, severity change), run it against a sample or
all governed repos and put the result in the governance PR: "this change would newly block 14 PRs' worth of code
in 6 repos".
**Why:** governance teams currently change rules blind. This is the "dry run" that makes tightening safe, and it is
the natural companion to staged guardrails.
**Needs:** full-scan capability across repos (exists per repo); a runner that iterates the estate.
**Working when:** no rule change surprises a delivery team.

### A4. Organisation-wide required check
**What:** use organisation rulesets so `governed / governor` and the CODEOWNERS requirement are applied to every
repo by default, with the stage declared in each repo or defaulted by a repository property.
**Why:** adoption by convention does not scale. A ruleset makes governance the default and opting out explicit.
**Needs:** organisation admin rights; a clear exemption process.
**Working when:** a new repo is governed from its first PR without anyone setting anything up.

---

## Next

### B1. Remote domain endpoints behind SSO
**What:** each domain team runs its own MCP endpoint (for example on your Kubernetes platform) behind your identity
provider, versioned and released independently. Reviewers and AI agents connect over HTTP instead of starting a
local process.
**Why:** domain teams get real ownership and release cadence, and the guidance AI agents read is the same live
source CI uses. Only the client changes; the tool contract stays.
**Needs:** hosting, authentication for CI and for agents, an availability plan (fail closed has a cost when an
endpoint is down).
**Working when:** a guidance change by a domain team is live without touching this repo.

### B2. Policy-to-rules drafting
**What:** the compliance team writes policy on the documentation site as they do today. An assistant drafts the
matching rule entries (summary, fix, examples, suggested stage and severity) and, where possible, a detector. A
human domain owner reviews it in a PR.
**Why:** the translation from policy to rules is the main bottleneck and the main drift risk. Drafting removes the
effort without removing the review.
**Needs:** a stable format for policy pages; a "policy changed" trigger.
**Working when:** a policy change produces a ready-to-review rules PR within a day, and the policy and rules never
disagree for long. A check can flag drift.

### B3. Estate dashboard
**What:** one view across all governed repos: findings by area, stage and team; time to fix; which rules cause the
most friction; waivers by age; which products are ready for the next stage and what stops them.
**Why:** governance without visibility is hope. It also tells you which rules need work and where teams need help.
**Needs:** findings published somewhere queryable (scheduled full scans, or uploading each verdict).
**Working when:** the CTO can answer "how are we doing on security this quarter and where are the gaps?" in a
minute, and a team can see its own readiness for production.

### B4. Agent pre-flight
**What:** make AI coding agents ask before they write. A tool such as `get_decision_context(task, stage)` returns
the relevant guidance, approved technologies and past decisions. A generated, thin agent instruction file points to
it and states the repo's stage.
**Why:** the strongest fix is the finding that never happens. This is the original goal of making agents
organisationally aware, now with the same source CI uses.
**Needs:** B1 (a reachable endpoint); a view of the rules tuned for agents (short, ranked by relevance).
**Working when:** findings per PR from agent-authored code fall measurably, and agents cite the policy in their
descriptions.

### B5. Fix suggestions
**What:** for rules with a mechanical fix (add `lang`, add a non-root user, pin a version), include a suggested
patch in the comment or as a one-click change. For harder ones, hand the finding to the coding agent with the
guidance as context.
**Why:** a finding with a ready fix is resolved in seconds. It turns governance from a gate into a helper.
**Needs:** safe, tested patch generators per rule; a policy on who may apply them.
**Working when:** a large share of findings are closed by accepting a suggestion.

---

## Later

### C1. Judgment reviewers for design and research
**What:** reviewers for areas that cannot be pattern-matched (design consistency, user research evidence,
architecture quality) that use a language model against the domain's own guidance and examples.
**Why:** much of what matters most to the organisation cannot be linted. These reviewers cover it, advisory first.
**Needs:** the domain's guidance written well enough to judge against; a way to measure the model's agreement with
human reviewers; pinned models and prompts; strict limits on what PR content the model sees.
**Working when:** domain owners agree with most of the reviewer's findings on a labelled sample, at which point
specific rules can move from advice to a gate.

### C2. Strategy alignment
**What:** check proposals (an ADR, a design doc, a dependency choice) against the CTO strategy: which strategic
themes does this support, which does it cut across, and does the decision record say so?
**Why:** this is the second original goal. It is partly deterministic (does the ADR name the theme?) and partly
judgment, so it builds on C1 and the evidence mode.
**Needs:** strategy distilled into short, versioned, linkable statements; C1.
**Working when:** reviewers see strategic tensions surfaced before a decision is made, not after.

### C3. Risk tiers alongside stages
**What:** stage says how mature a product is; a second dimension says how much harm it could do (data classification,
number of users, regulated or not). Guardrails apply by the combination. A scan-stage product that holds personal
data still gets the privacy rules.
**Why:** maturity alone is a blunt instrument. Some prototypes touch sensitive data, and some production tools are
low risk.
**Needs:** a product registry as the source of truth for tier; a decision on who sets it.
**Working when:** guardrails feel proportionate to both teams and auditors.

### C4. Beyond the pull request
**What:** apply the same domain knowledge in more places: local checks before commit, IDE feedback, infrastructure
plan checks, container image scans, deployment gates, design and document reviews, and a scheduled estate scan.
**Why:** one knowledge layer, many checkpoints. Earlier is cheaper; later catches what slipped through.
**Needs:** the reviewer logic packaged as a library and command line (largely there); integration per surface.
**Working when:** the same finding appears with the same wording whether it is found locally, in review or in the
pipeline.

### C5. New domains
Each is a folder of rules and a reviewer, as in [extending.md](extending.md).

| Domain | Examples of what it would check |
| --- | --- |
| FinOps | Untagged or oversized resources, expensive defaults, cost estimate in the PR |
| Data protection | Personal data in logs, retention, cross-border transfers, missing data protection impact assessment evidence |
| Resilience | Health checks, timeouts, backups, single points of failure, runbook present |
| AI governance | Approved models only, calls routed through the gateway, prompt and data handling, evaluation evidence |
| Supply chain | Licences, vulnerable or unmaintained dependencies, software bill of materials, signed images |
| Design and research | Design system use, evidence of user research, accessibility annotations |
| Documentation | Service owner, runbook, architecture decision record present |

---

## Always

### D1. Rule quality scores
Track, for each rule, how often it fires, how often authors fix it versus waive it, and how often a human overrules
it. Surface rules with high waiver or dismissal rates as candidates for rewriting or retirement. Rules are
products too.

### D2. Release rings for guidance
Today a merged rule applies everywhere immediately. Add rings: a rule goes first to a pilot group of repos, then
widely, with automatic pause if friction rises. Pair it with tagged releases of the governance repo that consumers
pin to.

### D3. Audit trail
Keep a tamper-evident record of what was checked, against which guidance version, with what result and which
waivers, for each merge. It lets you answer an auditor's "what did you check on this release and why did it pass?"
without reconstructing it.

---

## Suggested ordering

If you do only a few, this order has the best value for effort and removes the most risk first:

1. **A1 Shadow rules** and **A3 Rule impact preview**: make changing rules safe.
2. **A4 Organisation-wide required check** with **A2 waiver register**: make governance the default and controllable.
3. **B3 Estate dashboard**: make it visible to leadership and teams.
4. **B1 Remote endpoints** then **B4 Agent pre-flight**: the original goal of informed agents.
5. **B2 Policy-to-rules drafting** to keep policy and rules in step as the system grows.
6. **C1 Judgment reviewers** once the earlier pieces provide the measurement to trust them.

## What we would deliberately not do

- **Let AI approve or waive anything.** Humans own exceptions and policy.
- **Let a repo choose its own rules.** Stage and risk tier can vary guardrails; teams cannot opt out of a rule.
- **Make the governor smart.** It collates and applies policy. Judgment belongs in the domains, where an owner is
  accountable for it.
- **Block on anything unmeasured.** Strictness follows evidence (A1, D1).
