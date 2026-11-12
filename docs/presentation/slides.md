# Presentation: guardrails that grow with your product

A text version of the slides, with speaker notes, for reading without the slide viewer. The slide source is in [`deck/`](deck/) (one HTML file per slide; `deck.json` holds the order). Use it with the [demo script](demo-script.md).

The published deck is a private slides artifact; these files are the source it was built from.

## Slide 1: Guardrails that grow with your product

Office of the CTO · Technology governance

Automatic, explainable policy checks on every pull request. A working proof of concept.

Security

Accessibility

Enterprise alignment

+ your area

> **Speaker notes:** About 1 minute. Open with the one-line pitch: every pull request is checked automatically against our own technology policy, and the checks get stricter as a product matures. Today is a working proof of concept on real GitHub runners, not a finished product. Everything you will see is live in two personal repos.

## Slide 2: Policy reaches engineers too late, and AI writes code faster than we can review it

**A document to read**

Standards live on a docs site. Few people read them before they build.

**A meeting to book**

Review boards catch problems after the design is set and the code is written.

**Agents that guess**

Coding assistants pick whatever framework is familiar, unless something tells them what we approved.

Goal: bring each area’s guidance into the pull request, as short, specific feedback that a person and an AI agent can both act on.

> **Speaker notes:** About 1 minute. Three ways policy fails today: it is a document, a meeting, or nothing at all when an AI agent is writing the code. The fix is to put the guidance where the work happens, in the pull request, and make it readable by people and machines.

## Slide 3: Each area owns its knowledge. One governor collates it.

Pull request

Triage

Security

Accessibility

Enterprise alignment

Your area

Governor

One comment and one check

Each area has its own knowledge server and its own reviewer, with the same contract.

Areas never talk to each other. Only the governor sees all of them.

> **Speaker notes:** About 2 minutes. Walk left to right. Triage decides which areas apply from the changed files, so a docs-only change only runs security. Each area runs in its own job and pulls what good looks like from its own MCP server, which is the same source an AI agent can read before it writes code. The governor collates, applies the rules about strictness, and posts one comment and one pass or fail check. Adding a new area needs no change to the workflow.

## Slide 4: Three layers, three owners

| Layer | The question it answers | Owned by | Changes when |
| --- | --- | --- | --- |
| Knowledge | What does good look like? | Each domain team | Their guidance changes |
| Judgment | Does this change meet it? | Each domain team | Detection improves |
| Synthesis | What do we do with all the answers? | Office of the CTO | Governance policy changes |

A domain team can change its rules without touching CI. The platform can tighten policy without understanding accessibility.

The industry calls the knowledge layer a “context layer”. Gartner describes it as the infrastructure that feeds enterprise knowledge into AI agents, coding agents included. This is ours, with the pull request as the point of use.

> **Speaker notes:** About 1 minute. Gartner’s data and analytics research talks about a context layer (and a semantic layer) as the new critical infrastructure that joins enterprise knowledge to agentic AI. Other writers say knowledge layer or intelligence layer. Our knowledge layer is that idea applied to engineering: each domain publishes what good looks like once, in a form agents and people can both read. Check the exact Gartner wording and cite the current research note before the session, as I could only confirm the term “context layer”. This separation is the central design choice. Knowledge is plain YAML that the domain team owns and changes by pull request. Judgment is a small reviewer that detects violations. Synthesis is the governor, which only collates and applies organisation-wide rules about strictness. Neither side can quietly weaken the other.

## Slide 5: What a developer sees

One comment, updated in place as they push.

One check to require: governed / governor.

A kind, plain-spoken note: what we noticed, why it matters, a way forward, who to ask.

A machine-readable block, so Copilot can fix its own pull request.

Governance review: Blocked

Product stage: Scan → Pilot → Production

⛔ Needs fixing · SEC-003 · TLS certificate verification disabled

What we noticed: admin.py:9 requests.get(url, verify=False)

Why it matters: someone on the network could read or change what is sent.

A way forward: remove verify=False and trust the organisation certificate bundle.

Want to read more? The policy, in plain words · The exact rule

Questions? Ask Security Engineering

> **Speaker notes:** About 1 minute. This is a mock-up of the real comment you will see in the demo. The important things are that it is one comment that updates, the fix is stated, the owner is named and there is a link back to the human-readable policy. The JSON block at the bottom of the real comment is for AI agents.

## Slide 6: Guardrails grow with the product

STAGE 1

**Scan**

Exploring an idea. Only the must-never-happen rules.

4

guardrails in force

STAGE 2

**Pilot**

Real users, limited scope. Everyday good practice.

15

guardrails in force

STAGE 3

**Production**

Relied upon. Every guardrail, and five get stricter.

18

guardrails in force

A product declares its stage in one file. If it declares nothing it is treated as production, so forgetting never makes a product look safer than it is.

> **Speaker notes:** About 2 minutes. The stage is declared by the product in a file called .governance.yml, or a marker in the README, or a platform-set repository variable. Each guardrail says which stage it starts at and then applies to every later stage. The strictest declaration wins, a pull request can raise the stage but never lower it, and raising it re-checks the whole repository, so promotion is a readiness check. The numbers are from the example rules in the proof of concept; your governance teams will set the real ones.

## Slide 7: A warning today can be a block tomorrow

| Guardrail | Scan | Pilot | Production |
| --- | --- | --- | --- |
| SEC-001 Hard-coded secret | Blocks | Blocks | Blocks |
| SEC-005 Container runs as root | Not yet | Warning | Blocks |
| EA-003 Technology not in the catalogue | Not yet | Warning | Blocks |
| A11Y-004 Vague link text (advice only) | Not yet | Not yet | Warning |

The comment warns early: “At Production this becomes blocking.”

Raising the stage re-checks the whole repository, so promotion becomes a readiness gate.

> **Speaker notes:** About 1 minute. Some guardrails apply only from a later stage, and some get stricter. The container running as root is a good example: a warning for a pilot, a block for production. Accessibility is advice-only, so even its blocking rules show as warnings. The developer is told early, so they fix it before the last minute. In the demo, the promotion pull request shows this live.

## Slide 8: Built to be trusted

**Fails closed**

A crashed or missing check blocks. A broken gate never looks like a pass.

**Policy out of reach**

Rules live in the governance repo. A pull request cannot loosen the rules that judge it.

**Exceptions are visible**

Waivers are dated, capped at 90 days and shown in every comment. Secrets can never be waived.

**Humans read, machines enforce**

Every finding links to the plain-language policy and to the exact rule that produced it.

> **Speaker notes:** About 1 minute. These are the properties that make people trust a gate. If a required check crashes, the pull request fails rather than passing silently. Policy is held in the governance repo, not in the repo being judged. Waivers live in the product repo but are dated, narrow and visible. Finally, every finding links back to the policy people actually read.

## Slide 9: How a policy becomes a guardrail

1

**Compliance writes policy**

In plain language, on the docs site.

2

**Turned into a rule**

Guidance in YAML, plus a detector if it can be automated.

3

**Governance approves**

A pull request that the owning team must approve.

4

**Live everywhere**

Every pull request is checked from its next run.

Exceptions: a waiver file in the product’s repo, approved by the governance team through code owners. Dated, narrow and visible.

> **Speaker notes:** About 1 minute. Be precise here, because it is a common misunderstanding: the guidance is mostly YAML, not code. Code is needed only where a rule can be checked automatically, and then it is a small detector. A waiver is approved once but it expires, after at most 90 days, and it covers every matching finding in its path for that time, so approvers should insist on narrow paths. Be honest that the code owner approval only becomes enforced when a branch ruleset requires it, which is not set up yet in the proof of concept.

## Slide 10: What people ask for becomes what we build

**Ask**

Developers and agents query the guidance: a rule, a topic or a technology.

**Record**

One small record per question: who, which area, answered or not. No code.

**Rank**

Questions with no answer, ranked, become each team’s backlog.

Example from the proof of concept: “kafka message queue” asked twice, no guidance. That is the next guardrail to write.

Built as a small proof of concept. Reported by team or repo, never by person.

> **Speaker notes:** About 1 minute. Every question to the knowledge layer is a statement of need, and normally it is lost. We record it, with no file contents and no names, and rank what we could not answer. That tells each governance team what to write next, and tells us where to invest. It also fits the industry idea of a context layer: it feeds agents, and it learns what they lack. Be honest that this is a small proof of concept: the records are files from each run, and a shared store would come with hosted endpoints. To show it, run python -m governance ask a couple of times with an unknown topic, then python -m governance demand on the log.

## Slide 11: Demo: seven pull requests, one demo app

| PR | What changes | What you should see |
| --- | --- | --- |
| 1 | Docs only | Passes. Only security runs. |
| 2 | Approved dependency | Passes. No findings. |
| 3 | Secret, no TLS check, eval | Blocked by security. |
| 4 | Inaccessible page | Warnings only, plus a preview of a later stage. |
| 5 | Banned and unknown packages | Blocked. Warnings say they will block later. |
| 6 | Shell call with a waiver | Passes. The waiver is listed. |
| 7 | Pilot to production | Blocked. Whole repo re-checked. |

Order for the live demo: 3, then 5, then 7. The others are there to open if asked.

> **Speaker notes:** Hand over to the live demo here, using the separate demo script. If the live view is slow, the comments on these pull requests are already posted and can be opened directly.

## Slide 12: Where we are, and what we need from you

**Where we are**

Working on real GitHub runners, with three areas and 18 example guardrails.

Rule text, owners and the technology catalogue are placeholders.

Not set up yet: the required-check ruleset and real teams as code owners.

**Decisions we need**

1. Which two areas go first?

2. Who owns each area’s rules and approves changes?

3. Which repos adopt first, and at which stage?

Later ideas: shadow rules, a rule impact preview, an estate dashboard, agent pre-flight checks. See the roadmap.

> **Speaker notes:** About 2 minutes, then questions. Be clear that this is a proof of concept with example content. The three decisions are the real ask: the pilot areas, the owners, and the first repos plus the stage each declares. Mention that the roadmap is a menu of ideas, not commitments.
