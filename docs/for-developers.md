# Guide for developers

Every pull request in a governed repository is automatically reviewed against your organisation's technology
policy: security, accessibility, enterprise alignment, and any other area added. You get one comment on your PR
that says what is wrong, why, how to fix it, and who to ask.

## What you see

Within a couple of minutes of opening or updating a PR:

- **A comment** headed with the result:
  - ✅ **Passed**: nothing to do.
  - ⚠️ **Passed with warnings**: you can merge, but the advice is worth acting on.
  - ⛔ **Blocked**: you cannot merge until the blocking findings are fixed or waived.
- **A check** named `governed / governor` on the PR. If your repo requires it, a blocked result stops the merge.
- **Inline annotations** on the changed lines in the "Files changed" tab.

The comment updates itself when you push. It does not add a new one each time.

### Reading a finding

```
⛔ Blocking · SEC-003 · TLS certificate verification disabled
📍 admin.py:9
Found:         requests.get(url, verify=False)
Why it matters: ...
How to fix:    ...
📘 Read the policy · 📖 Rule definition   ← the policy as people read it, and the exact rule
What good looks like  ▸ (expand for an example)
```

| Part | Meaning |
| --- | --- |
| Severity | ⛔ blocks the merge, ⚠️ advises, ℹ️ informs |
| Rule id | Stable name, for example `SEC-003`. Quote it when asking for help |
| 📍 location | File and line you changed |
| 📘 Policy link | The human-readable policy for this rule. Start here |
| 📖 Rule definition | The rule as coded, for engineers |
| Owner and contact | Who to ask. Shown under each domain heading |

Only the lines **your PR added or changed** are judged. Old code is not held against you.

### Your product's stage

Not every product has to meet every guardrail on day one. Your repo declares how mature it is, and you get more
guardrails as it grows:

🔍 Scan → 🧪 Pilot → 🚀 Production. See [guardrails by stage](guardrails.md) for exactly what applies at each.

Declare it in `.governance.yml` at the root of your repo:

```yaml
stage: pilot     # scan | pilot | production
```

(or put `<!-- governance-stage: pilot -->` in your README). The comment shows your stage at the top.

- A guardrail applies from its stage onward, so moving up only ever adds guardrails.
- Some guardrails also get **stricter**: a warning at pilot can block in production. The comment says so (*Heads up: at Production it becomes blocking*), so you can fix it early rather than at the last minute.
- **Not declared means production**, the strictest stage.
- Findings from a guardrail that starts at a later stage appear under **Coming at a higher stage**. They are real
  problems in your change, but they do not count today. It is a free look at what promotion will demand.
- **Moving up a stage** is a pull request that changes `stage:`. The whole repository is then checked against the
  new guardrails, not just your diff, so you find out whether you are ready. Fix what it finds in the same PR or
  before.
- You cannot lower the stage in a pull request to dodge a finding. The stage already on the main branch applies.

### Which areas run

Only the areas relevant to your change run. A docs-only change gets security only. Touching `package.json`,
`requirements.txt`, a `Dockerfile` or `docs/adr/` also runs enterprise alignment. HTML changes run accessibility.
The foot of the comment lists areas that did not apply.

## Fixing a finding

1. Read **How to fix** and the example under **What good looks like**.
2. Make the change and push. The comment refreshes.
3. If it is not clear, open the 📘 policy link or contact the owner shown for that domain.

### Using Copilot or another AI agent

The comment ends with a collapsed section, **Machine-readable findings**. It lists each open blocking or warning
finding with its file, line and fix. You can ask the agent to "fix the blocking findings in the governance
comment" and it can work from that block. The guidance servers can also be read by agents before they write code,
which avoids the findings in the first place.

## Choosing technology

Enterprise alignment checks dependencies and base images against the organisation's technology catalogue:

| Catalogue status | What you will see |
| --- | --- |
| adopt / approved | Nothing. Go ahead |
| trial / tolerated | A note, and an ADR is still needed |
| deprecated | A warning with the preferred alternative |
| banned | ⛔ Blocked, with the preferred alternative |
| not in the catalogue | ⚠️ Warning. Unknown is not the same as permitted |

If you really need something off the paved road, write an **ADR** (architecture decision record) in
`docs/adr/`, copied from `0000-template.md`. Fill in every section: the guidance you consulted, where you deviate,
and any tension with strategy. The pipeline checks the ADR exists and is complete. People, not the pipeline,
decide whether the choice is wise.

## Asking for an exception (a waiver)

If a finding is genuinely a false alarm or an accepted risk, add a waiver to `.governance-waivers.yml` in your
repo **in the same PR**:

```yaml
waivers:
  - rule_id: SEC-002
    path: scripts/**               # keep it as narrow as you can
    reason: The command is a constant string with no user input.
    approver: name-of-governance-approver
    expires: 2027-01-10            # at most 90 days from today
```

Then:
1. The governance team is asked to review the waiver file (it is protected by code owners). Explain why in the PR.
2. When they approve and you merge, the waiver applies to that rule and path until it expires. You do not need a
   fresh approval for each PR in that time.
3. It is shown in every PR comment under **Waived** so it stays visible. In your own PR it is marked ⏳ *New in this PR* until it is merged; after that it shows ✅.
4. When it expires the finding returns. Either fix the underlying issue or request a new waiver.

Rules about waivers:
- `reason`, `approver` and `expires` are required, and the expiry cannot be more than 90 days away.
- Hard-coded secrets (`SEC-001`) can never be waived. Remove the secret and rotate it, even if it was only
  committed briefly.
- The waiver covers the whole `path` for the whole period, including code you add later, so keep the path narrow.
- If the comment shows **Waivers that did not apply**, it states why (missing field, expired, too far ahead).
- A waiver is for a known, reasoned exception. It is not a way to hide a problem you plan to fix, so prefer a fix.

## Frequently asked questions

**It blocked my PR but I think the rule is wrong.** Open the policy link and contact the owner shown. If the
rule is wrong, the fix is a change to the rule (a pull request to the governance repo), which benefits everyone. A
waiver is for your one case.

**The comment did not appear.** PRs from forks run with a read-only token and cannot post comments; the check and
job summary still work. Otherwise open the check's details, or the **workflow run** link, and report the error.

**A reviewer is shown as "did not report" or "failed".** The system fails closed: a required area that could not
run counts as blocking, so a broken check never looks like a pass. Re-run the workflow. If it persists, tell the
platform team.

**Will old problems in files I touch be flagged?** Only lines you added or changed, unless the PR raises the product's stage, which checks everything. A scheduled full scan covers
the rest of the repo.

**Can I run it before pushing?** Yes. From a clone of the governance repo:
`python -m governance local --repo /path/to/your/repo --base main --head HEAD`.

**How do I set it up in a new repo?** Add the small `governance.yml` workflow shown in the
[README](../README.md#adopt-it-in-a-repository), then ask for the `governed / governor` check to be required.
