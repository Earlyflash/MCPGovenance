# Demo script: PR governance proof of concept

A script for showing the proof of concept to a team. It goes with the [slides](slides.md) (source in [`deck/`](deck/)). Allow 15 to 20 minutes: ten minutes of slides, then a live walk through three pull requests.

## Before you start

The demo is already live on GitHub, so preparation is opening the right tabs and checking they load. Allow 10 minutes, ideally the day before.

- [ ] Open the demo app pull requests list: [github.com/Earlyflash/MCPGovenance-DemoApp/pulls](https://github.com/Earlyflash/MCPGovenance-DemoApp/pulls)
- [ ] Open PR 3, PR 5 and PR 7 in separate tabs (links in the next section) and scroll to the governance comment on each
- [ ] On PR 3, open the Checks tab and confirm the check named governed / governor is there
- [ ] Open the guardrail picture: [docs/guardrails.md](../guardrails.md)
- [ ] Open one policy page: [docs/policy/security.md](../policy/security.md)
- [ ] Check both repos open for the people in the room; if not, sign in to GitHub as the repo owner first
- [ ] Zoom the browser to about 125% so the comment is readable from the back
- [ ] Have the slide deck open on the demo slide (slide 11)

Fallback: if GitHub is slow or offline, the comments are already posted, so a screenshot of each is enough to tell the story.

## Run of show

Cut the optional extras if time is short.

| Time | What | Slides or link | Key message |
| --- | --- | --- | --- |
| 0:00 | The problem and the idea | Slides 1 to 4 | Policy reaches engineers too late, so we put it in the pull request |
| 4:00 | What developers see | Slide 5 | One comment, one check, a fix and a link to the policy |
| 6:00 | Stages and escalation | Slides 6 and 7 | Guardrails grow with the product, and some get stricter |
| 9:00 | Trust and how rules get in | Slides 8 and 9 | Fails closed, visible exceptions, humans approve |
| 10:00 | What people ask for | Slide 10 | Questions with no answer become the next guardrails |
| 11:00 | Demo 1: blocked PR | [PR 3](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/3) | The core loop |
| 13:00 | Demo 2: heads-up | [PR 5](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/5) | Warnings that will block later |
| 15:00 | Demo 3: promotion | [PR 7](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/7) | Raising the stage re-checks everything |
| 17:00 | Decisions needed | Slide 12 | Which areas, which owners, which repos |

## Demo 1: an insecure change is blocked (PR 3)

Open [PR 3](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/3). It adds one file, admin.py, with a hard-coded password, a web request with certificate checking turned off, and a call to eval. Time: about 2 minutes.

1. **Set the scene.** Say: this is an ordinary pull request. The author did nothing special. Scroll to the bottom of the conversation tab.
2. **Show the check.** Point at the failing check, governed / governor. Say: there is one check to require, however many areas we add.
3. **Show the comment.** Point at the banner (Blocked), then the totals row (3 blocking), then the scoreboard. Say: each area reviews on its own; this comment only collates them. Here only security applied, because only a Python file changed.
4. **Open one finding.** Pick the secret (SEC-001, admin.py line 5). Read the **What we noticed** line: the value is redacted, so the comment never leaks the secret again. Then read **Why it matters**, which says in plain words who is affected, and **A way forward**. Point out the tone: the comment opens by thanking the author, and nothing in it blames them.
5. **Follow the policy link.** Click **The policy, in plain words**. Say: engineers read the plain-language policy; **The exact rule** link is for people who maintain it.
6. **Point at the owner.** Under the domain heading, show the owner and contact. Say: every finding says who to ask.
7. **Mention the agent block.** Expand the machine-readable findings at the bottom. Say: this is how Copilot can fix its own pull request.

Transition: that was a clear-cut case. Now a case where the judgment depends on how mature the product is.

## Demo 2: technology choices and the heads-up (PR 5)

Open [PR 5](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/5). It adds a front-end package file with React, a deprecated library (moment), an unknown one (left-pad) and a banned one (event-stream), and no architecture decision record. This is the original worry: people choosing tools nobody approved. Time: about 2 minutes.

1. **Show who reviewed.** The scoreboard now shows enterprise alignment, not security. Say: triage picked the area from the file that changed.
2. **Show the product stage line.** Point at Scan, Pilot, Production with Pilot in bold. Say: this product declared itself a pilot, so it is held to the pilot guardrails.
3. **Read the two blocks.** The banned package, and the missing decision record for technology that is off the paved road. Say: the pipeline does not decide whether React is a good idea. It checks that a person recorded the decision.
4. **Read a heads-up.** On a warning, show the line that says it becomes blocking at Production. Say: the author is told early, while it is cheap to fix.
5. **Show the catalogue link.** Open **The exact rule** for the banned technology. Say: agents ask the same catalogue through the MCP server, so Copilot can be told what is approved before it writes the code.

Transition: the same repository, a different stage. Watch what happens when this product is promoted.

## Demo 3: promotion to production (PR 7)

Open [PR 7](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/7). It changes one word in one file: stage: pilot becomes stage: production. This is the most important demo because it shows the idea of guardrails that grow. Time: about 3 minutes.

1. **Show the diff first.** Open the Files changed tab. One line changed in .governance.yml. Say: the author touched no code.
2. **Show the result anyway.** Back on the conversation tab, show the Blocked banner and the friendly opening line. Say: the pipeline checked the whole repository, not just the diff, because the stage went up. Point at the **You are moving up a stage** note and at the totals row, which says the whole repository was scanned.
3. **Open the blocking finding.** It is the Dockerfile that runs as root (SEC-005). Read the line that says it was only a warning for a pilot but blocks for production. Say: at pilot this was a warning; now it is a block.
4. **Show the warning.** One vague link on the home page, a guardrail that only starts at production. It is advice only because accessibility is an advice-only area.
5. **Go back to PR 1 or PR 4 for contrast.** On PR 4 point at the section called **A look ahead: coming at a higher stage**. Say: even at pilot, teams can see what is ahead. Nothing there counts yet.
6. **Make the point.** Promotion becomes a readiness check with a clear list of what is missing, instead of a surprise review.

Transition: now show the picture that explains all of it.

## Optional extras

Use these if the room wants more or you have time. Each is two to three minutes.

**The guardrail picture** ([guardrails.md](../guardrails.md))

1. Show the stage ladder diagram at the top: how many guardrails each stage adds, and which get stricter.
2. Scroll to the matrix of every rule by stage. Say: this page is generated from the rules, so it cannot drift from what the pipeline enforces.
3. Open a policy page and show one rule's row of severities by stage. This is what a governance team reads and approves.

**An exception that is visible (PR 6)** ([PR 6](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/6))

1. The change uses a shell command, which security normally warns about. The PR includes a waiver.
2. Show the Waived table: rule, location, approver, expiry and a status. Point at the status that says the waiver is new in this pull request.
3. Say: a waiver is approved once by the governance team through code owners, then lasts until it expires, at most 90 days. It stays visible in every comment until then.
4. Be candid: the code owner requirement is only enforced once a branch ruleset requires it, which is not set up in this proof of concept.

**A live fix**

1. Before you start talking about PR 3, open the demo/insecure branch on GitHub, edit admin.py and remove the verify=False argument from the web request. Commit to the same branch.
2. Keep talking. The check re-runs in one to two minutes and the same comment updates in place, now with two blocking findings instead of three.
3. To restore the demo, put the argument back and commit again.

**A preview of a later stage (PR 4)** ([PR 4](https://github.com/Earlyflash/MCPGovenance-DemoApp/pull/4))

1. Show seven accessibility warnings. Say: accessibility is advice only, so even rules marked blocking appear as warnings.
2. Point at the section called **A look ahead: coming at a higher stage**.

**What people ask for (the demand layer)**

1. In a terminal, set `GOVERNANCE_DEMAND_LOG=/tmp/demand.jsonl`, then run `python -m governance ask --domain security --caller copilot "kafka message queue"` twice. The answer is empty: we have no guidance on it.
2. Run `python -m governance ask --domain enterprise-alignment --technology --ecosystem pip celery`. Say: an agent asking whether a technology is approved gets a straight answer, or a gap.
3. Run `python -m governance demand /tmp/demand.jsonl`. Show the table of questions with no answer. Say: this is each team's backlog, ranked by how often it is asked.
4. Be candid: this is a small proof of concept. The records are files from each run; a shared store would come with hosted endpoints. It is roadmap item B6.

**The demand report with real volume**

The terminal demo above only has a few questions. For a richer picture, generate 1,000 and open the visual report. Do this the day before.

1. In the governance repo run `python scripts/simulate_demand.py --calls 1000 --out demand-demo`. It makes 1,000 real calls to the three guidance servers and takes about a minute.
2. Open `demand-demo/demand.html` in a browser. A saved sample is in [`../examples/demand-report-sample.html`](../examples/demand-report-sample.html).
3. Start with the amber box, **Write these first**: the most-asked questions we have no guidance for. Then show the questions per day chart and the by area bars.
4. Be candid: the questions, repos and assistants are invented, and the timestamps are spread over 30 days so the chart has a shape. The calls themselves are real.

## Likely questions

| Question | Honest answer |
| --- | --- |
| Does this replace human review? | No. It removes the checkable, repetitive part so reviewers spend time on judgment. People still decide whether a technology choice is wise; the pipeline only checks that the decision is recorded. |
| Who writes the rules? | The domain teams, mostly as plain YAML guidance, changed by pull request and approved by their own team. A small detector is needed only where a rule can be checked automatically. An assistant can draft the YAML from the written policy. |
| What about false positives? | A waiver covers a genuine exception, and a wrong rule is fixed once in the governance repo for everyone. A shadow mode, where a new rule runs silently before it counts, is on the roadmap. |
| Will it slow pull requests down? | The checks run in parallel and take roughly one to two minutes in the proof of concept. We have not measured this on a large repository. |
| Where does it run? Do we need EKS? | On GitHub-hosted runners. EKS only becomes useful later, if each area hosts a shared endpoint for people and agents to read. |
| What if a repo does not say its stage? | It is held to production, the strictest. A pull request can raise the stage but never lower it. |
| How does Copilot use this? | Today through the machine-readable block in the comment, so it can fix its own pull request. Asking the guidance before it writes code is on the roadmap. |
| Is it safe to run on untrusted code? | Reviewers read changed files as text and never run them. The rules live in the governance repo, so a pull request cannot loosen the rules that judge it. |
| What is real and what is example? | The mechanism works end to end. The rule wording, owners, contacts and the technology catalogue are placeholders for your teams to replace. |
| What is not set up yet? | A branch ruleset that makes the check and code owner review mandatory, real teams as code owners, and a second approver for waivers. |
| How do we know which guardrails to write next? | Every question to the guidance can be recorded without file contents. A report ranks what people and agents asked for and we could not answer. It is a small proof of concept today, and reported by team or repo, never by person. |

## If something goes wrong

| Problem | What to do |
| --- | --- |
| GitHub is slow or the page will not load | Every comment is already posted on the pull requests, so open them directly. Keep screenshots of pull requests 3, 5 and 7 in the deck as a backup. |
| The governance comment is missing on a pull request | Open the Actions tab and check the run. Re-run it with the **Re-run all jobs** button, or run `gh api -X POST repos/Earlyflash/MCPGovenance-DemoApp/actions/runs/<run id>/rerun`. It takes one to two minutes. |
| The check is still running when you reach it | Talk through the stage slide while it finishes, then refresh. The comment updates in place, so there is only ever one. |
| Someone asks about a pull request from a fork | Fork pull requests get a read-only token and cannot comment. This is a known limit of the proof of concept. Say so and move on. |
| A result differs from this script | Do not hide it. Explain what the finding says and follow its links to the policy and the rule. That is the product working as designed. |
| After the live fix on `demo/insecure` | Restore the branch afterwards by putting `verify=False` back in `admin.py`, so pull request 3 shows the blocked result again next time. |
| You are asked for something you cannot answer | Say it is a proof of concept with example content, note the question, and point to the roadmap and the guides in the governance repo. |
