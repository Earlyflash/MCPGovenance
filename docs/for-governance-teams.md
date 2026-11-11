# Guide for governance teams

You own what "good" means for your area (security, accessibility, FinOps, enterprise alignment...). This guide
explains how your policy becomes something every pull request is checked against, and what you control.

## The short version

1. You write policy and guidance in plain language.
2. It is turned into structured guidance in this repo (YAML, plus a small detector if the rule can be checked
   automatically).
3. The change goes through a pull request that **your team must approve**.
4. When it merges, every governed pull request in every repo is checked against it. No other repo needs changing.
5. Developers who need an exception ask for a **waiver**, which you approve.

```
 Your policy (human words)
        │  translate
        ▼
 domains/<your-area>/knowledge/rules.yml   ← what good looks like, how to fix, examples
 governance/reviewers/<your_area>.py       ← the check, only if it can be automated
        │  pull request, approved by your team (CODEOWNERS)
        ▼
 merge to main  →  every PR in every governed repo is checked from its next run
```

## What you own

| You own | Where | Changes by |
| --- | --- | --- |
| The human-readable policy | `docs/policy/<area>.md` (generated here; on the docs site in real use) | Pull request |
| Rule wording, fix advice, examples, severity, and the stage it starts at | `domains/<area>/knowledge/rules.yml` | Pull request |
| How strict the area is (`gate`, `advise`, `evidence`), owner, contact, how to ask for a waiver | `domains/<area>/domain.yml` | Pull request |
| Checks that find violations | `governance/reviewers/<area>.py` | Pull request |
| Technology decisions (enterprise alignment) | `domains/enterprise-alignment/knowledge/technology.yml` | Pull request |

The platform team owns `policy.yml` (which areas run where, which are required, waiver limits). You do not need to
touch it unless you are adding a new area.

## Turning policy into guidance

A written policy statement becomes one **rule**. For each rule decide:

| Question | Becomes |
| --- | --- |
| What is the rule in one sentence? | `summary` |
| Why does it exist, and what should people do instead? | `guidance` |
| What is the single most useful fix instruction? | `remediation` |
| What does bad and good look like? | `exemplars.bad` / `exemplars.good` |
| How serious is it? | `severity`: `block` stops the merge, `warn` advises, `info` notes |
| How sure are we that a hit is real? | `confidence` |

Good guidance is specific, short and actionable. A developer (or their AI agent) reads it at the moment of
fixing the problem.

**Can a machine check it?** Two outcomes:
- **Yes** (a banned library, a missing alt attribute, a public bucket): a developer on the platform side adds a
  detector. See [extending.md](extending.md). The rule then appears in PR comments.
- **No** (needs judgment: "is this design inclusive?"): the rule still goes in `rules.yml` so people and AI agents
  can read it through your area's MCP server, but it does not appear in PR comments. Domains for judgment can later
  use an AI-assisted reviewer, kept as advice until trusted.

You can write the YAML yourself, or give the policy to an engineer or an AI assistant to draft it. Either way the
draft is reviewed in the pull request, which is where your approval happens.

## Choosing the stage a guardrail starts at

Products are not all equally mature, so guardrails are staged. Every rule has an `applies_from` stage, and it
applies there and at every later stage:

| Stage | Meaning | Typical guardrails |
| --- | --- | --- |
| 🔍 Scan | Exploring an idea | Only what must never happen: leaked secrets, banned technology |
| 🧪 Pilot | Real users, limited scope | Everyday good practice |
| 🚀 Production | Relied upon | Everything, including the heavier requirements |

The picture of what applies at each stage is in [guardrails by stage](guardrails.md), generated from the rules so
it cannot drift. Each rule's page in [`policy/`](policy/) shows its own row of ✅ and ▫️.

**Making a guardrail stricter as products mature.** A rule can be a warning at one stage and a block later. Add
`escalate` to the rule:

```yaml
- id: SEC-005
  applies_from: pilot             # warns from pilot...
  escalate: { production: block } # ...and blocks in production
  severity: warn
```

Severity can only rise with the stage, never fall, and the escalation stage must come after `applies_from`.
The PR comment tells the author both ways: *Heads up, this becomes blocking at Production* while they are at
pilot, and *Stricter at this stage* once they are there. Advice-only areas still never block, whatever the rule
says. The ⛔/⚠️/ℹ️ matrix on each policy page shows the severity at every stage.

How a product declares its stage, and what you should know:
- It writes `stage: pilot` in `.governance.yml` (or a `<!-- governance-stage: pilot -->` marker in its README, or a
  platform-set repository variable). The strictest declaration wins.
- **Not declared means production.** Forgetting never makes a product look safer than it is.
- **A pull request can raise the stage, never lower it.** Raising it re-checks the whole product against the
  guardrails it adds (a *promotion scan*), which is your readiness gate. Lowering it takes effect only after the
  change is merged, so protect `.governance.yml` with CODEOWNERS like the waivers file.
- **Later-stage findings are previewed, not counted.** The PR comment lists them under *Coming at a higher stage*
  so teams see what is ahead. They cannot be waived or blocked early.
- Promoting a rule to an earlier stage (say pilot to scan) tightens it for every scan-stage product at once.
  Treat it like making a warning into a block: check the impact first.

## Approving changes

All guidance changes are pull requests against this repo. Your team's approval should be **required**, by making
sure `CODEOWNERS` lists your team against your area's folder, and the branch ruleset requires code owner review.

```
# .github/CODEOWNERS (to be set up; use your real team handles)
/domains/security/              @your-org/security-governance
/domains/accessibility/         @your-org/accessibility-governance
/domains/enterprise-alignment/  @your-org/octo-governance
/governance/reviewers/security.py  @your-org/security-governance
/policy.yml                     @your-org/platform-governance
```

> **Current state:** `.github/CODEOWNERS` exists in this repo, with the PoC owner as a placeholder for every
> area. A branch ruleset that makes code owner review **required** has not been created, so today CODEOWNERS only
> requests a review. Create the ruleset and replace the placeholder with real teams before relying on it.

When reviewing a change, check:
- Does the wording say what you mean, and would a developer know what to do?
- Is the severity right? Start new or noisy rules at `warn`; move to `block` once false positives are known.
- If there is a detector, did the tests include a clean example and a false-positive example?
- Does the change turn a rule from warn to block? Then check how many existing repos it would newly fail.

## What happens when you merge

- The change applies immediately to every governed repo, because they all call the workflow at `@main`. (Pin to a
  tag if you want releases to be deliberate.)
- A pull request that is already open picks up the new rules the next time its checks run (any new push, or a
  re-run).
- Every finding records the `guidance_version` that produced it, and links to the exact rule, so you can see which
  version of your guidance judged a PR.
- Anything already merged is not re-checked, unless someone runs a full scan.

Rolling out a stricter rule safely: merge it as `warn`, watch real pull requests, then change to `block`. For a new
area, begin in `advise` mode, then move to `gate` (a one-line change in `domain.yml`).

## Waivers: how exceptions work

Sometimes a developer has a good reason to break a rule. They ask for a **waiver** by adding an entry to
`.governance-waivers.yml` in their own repo, in the same pull request:

```yaml
waivers:
  - rule_id: SEC-002
    path: scripts/**              # optional; default is every file
    reason: The command is a constant string with no user input.
    approver: some-github-user     # the person in your team who approves it
    expires: 2027-01-10            # at most 90 days ahead
```

What the system enforces:
- All four fields are required. The expiry must be a real date within 90 days.
- A rule listed in `never_waivable` (currently `SEC-001`, hard-coded secrets) is never accepted.
- Waived findings stay visible in the PR comment with who approved them and when they expire.
- A waiver that does not validate is ignored, and the comment says why.

### Who approves, and for how long

The intended control: the repo's `CODEOWNERS` lists your team against `.governance-waivers.yml`, so any change to
that file needs your team's approval before it can merge. Once merged, the waiver applies without further
approval **until it expires or is removed**. After expiry the finding returns and a new waiver (with a new
approval) is needed.

Understand what a waiver covers, because approval is given once:
- It covers **every** matching finding for that rule within its `path` for the whole period, including new code
  added later in matching files. A `path` of `**` waives the rule across the whole repo.
- So when approving, check the `path` is as narrow as possible, the reason is specific, and the expiry is short.
- Any later change to the waiver file (adding, widening or extending) needs approval again, because it is a change
  to a CODEOWNERS-protected file.

> **Current state:** the demo app has a CODEOWNERS entry for `.governance-waivers.yml` (placeholder owner), but
> no ruleset requiring code owner review yet, and `waivers.require_approval` is `false` in `policy.yml` because the
> PoC repos have a single person. With `require_approval: true`, the named `approver` must also have approved the
> pull request, which stops people naming someone who never saw it. Turn it on once a second person exists.

**New waivers are flagged.** The governor reads the waiver file from the pull request, so a waiver added in a PR
counts for that PR's check straight away. To make that visible, the comment's **Waived** table has a status
column: ✅ *Already on the base branch* (a code owner accepted it earlier) or ⏳ *New in this PR* (applied
provisionally). New waivers also trigger a highlighted note that they become permanent only when the code owner
approves and the PR merges. The control that actually stops an unapproved waiver is CODEOWNERS plus required
review on that file, so make sure the ruleset exists.

## How findings link back to your policy

People read your policy, not our YAML. Every finding therefore links to:
- 📘 **Read the policy**: the human-readable section for that rule (`policy_url` in `domain.yml`, one section per
  rule, with the heading `RULE-ID Title`). In this PoC the pages are in [`docs/policy/`](policy/); in a real
  deployment point `policy_url` at the policy on the documentation site. A rule can set its own `policy_url` to
  link elsewhere.
- 📖 **Rule definition**: the exact lines in `rules.yml`, for engineers.

When you rename a rule's title, its policy heading must change with it or the anchor will no longer match. A test
checks that the security policy page has the heading each rule links to.

## Operating it

| Task | How |
| --- | --- |
| See what the system said about a PR | The governor comment; the **workflow run** link at its foot |
| Check the rules locally | `python -m pytest`, or `python -m governance local --repo <path> --base main --head HEAD` |
| Find a rule's source | The 📘 policy and 📖 rule definition links on each finding |
| Add or change a rule, add a new area | [extending.md](extending.md) |
| Understand the design | [how-it-works.md](how-it-works.md) |
| Review waivers across the organisation | Search repos for `.governance-waivers.yml`; expiry dates are in each file |

## Setup checklist (before relying on it)

- [x] `CODEOWNERS` in this repo (placeholder owner). Replace with your teams against their folders
- [ ] Branch ruleset on `main`: require pull request, require code owner review, require the CI check
- [x] Demo app has a `CODEOWNERS` entry for `.governance-waivers.yml` (placeholder owner). In each consuming repo, point it at the governance team
- [ ] In each consuming repo: ruleset requiring the `governed / governor` check
- [ ] `waivers.require_approval: true` once there is a second approver
- [ ] Pin consuming repos to a release tag instead of `@main` when you want controlled rollouts
- [ ] Add `/.governance.yml` to the CODEOWNERS of each consuming repo (it sets the stage, like a waiver sets an exception)
- [ ] Replace the example rules, policy pages, owners and contacts with real ones
