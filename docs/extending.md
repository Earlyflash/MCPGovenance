# Extending it: rules, policy and new domains

Three kinds of change, from lightest to heaviest:

| I want to... | Edit | Code change? |
| --- | --- | --- |
| Change guidance, wording, severity or the technology catalogue | `domains/<id>/knowledge/*.yml` | No |
| Change how strict a domain is, where it runs, or global behaviour | `domain.yml` or `policy.yml` | No |
| Detect something new, or add a whole new area | A reviewer in `governance/reviewers/` (and a domain folder) | Yes |

The key idea: **the knowledge file explains, the reviewer detects.** A rule only fires if a reviewer produces a hit
for its id. A rule with no detector is documentation (agents can still read it through the MCP server, which is
useful), but it never appears in a PR.

## 1. Change or add a rule in an existing domain

Rules live in `domains/<id>/knowledge/rules.yml`.

```yaml
- id: SEC-007                 # <PREFIX>-<number>, never reuse an id
  title: Unpinned container image
  severity: warn              # block | warn | info
  applies_from: pilot         # scan | pilot | production: the product stage this guardrail starts to apply in
  confidence: high            # high | medium | low
  tags: [docker, supply-chain]
  summary: One sentence on what is wrong and why it matters.
  guidance: >-
    The longer explanation an engineer or agent should read.
  remediation: The concrete fix, in one line.
  exemplars:
    bad:  |
      FROM python:latest
    good: |
      FROM python:3.12-slim@sha256:...
```

**Changing only text or severity** (for example `warn` to `block`) needs nothing else. Open a pull request against
this repo; the next governed PR anywhere picks it up, and the finding's `guidance_version` changes so you can see
which version judged it.

**Adding a new detectable rule** needs a detector too:

1. Add the rule to `rules.yml` as above.
2. In `governance/reviewers/<id>.py`, inside `run_checks(ctx)`, return a `Hit` for each occurrence:

   ```python
   hits.append(Hit("SEC-007", f.path, line_no, evidence=line.strip()[:160]))
   ```

   Useful helpers on `ctx`: `ctx.live_files(globs)` (changed, not deleted files), `ctx.lines(f)` (numbered lines of
   untrusted text), `ctx.base_text(path)` (the file at the base commit, for comparisons), `ctx.mcp` (call the
   domain's own MCP tools).
3. Add a test in `tests/test_reviewers.py` for a violation, a clean case and a false-positive guard.

Rules of thumb:
- Never execute or import PR content. Read it as text only.
- Report only what the PR changed. The runner drops hits on untouched lines (`ctx.keep`) unless it is a full scan.
- Put the explanation in `rules.yml`, not in the hit. `detail=` is only for facts specific to this occurrence.
- Start new or noisy rules at `warn`. Promote to `block` once the false-positive rate is known.
- If a hit uses a rule id missing from `rules.yml`, the run fails with "code and knowledge have drifted". That is
  intentional: it stops code and guidance disagreeing.

**Escalating by stage:** to make a rule a warning early and a block later, set the early severity and add
`escalate: { production: block }`. Severity may only rise, and only at stages after `applies_from`. Use it to
nudge early-stage products without blocking them, while holding production to the full standard.

**Choosing `applies_from`:** a rule applies at its stage and every later one, so pick the *earliest* stage at
which it is reasonable to demand it. `scan` is for the must-never-happen rules (leaked secrets, banned
technology), `pilot` for everyday good practice, `production` for what a system people rely on must meet. It
defaults to `scan` if left out, which is the strictest choice. After changing stages run
`python -m governance docs` to refresh the generated guardrail pages (a test fails if you forget).

**Retiring a rule:** remove the detector first, then the rule. Never recycle an id, because old waivers refer to it.

### Enterprise alignment is mostly data

Technology decisions need no code. Edit `domains/enterprise-alignment/knowledge/technology.yml`:

```yaml
- id: htmx
  name: htmx
  category: frontend-library
  status: trial          # adopt | approved | trial | tolerated | deprecated | banned
  owner: Platform Engineering
  last_reviewed_on: 2026-11-01
  detection: { npm: [htmx.org] }     # names seen in pip, npm or docker image names
```

The status maps to the existing rules: `banned` blocks (EA-001), `deprecated` warns (EA-002), unknown packages need
an ADR (EA-005). Agents ask the same catalogue through `check_technology`, so updating this file changes what both
CI and Copilot are told. Ideally this file is generated from your real technology radar rather than hand-edited.

## 2. Change policy

| Setting | File | Effect |
| --- | --- | --- |
| `mode`: gate / advise / evidence | `domains/<id>/domain.yml` | Whether the domain's blocks stop a merge. Owned by the domain team. |
| `owner`, `contact`, `waiver_route` | `domain.yml` | Shown on every finding from that domain. |
| `knowledge_version` | `domain.yml` | Bump when guidance changes meaningfully. Combined with a content hash. |
| `domains.<id>.paths` / `labels` | `policy.yml` | When the domain runs. A match on either triggers it. |
| `domains.<id>.required` | `policy.yml` | `true`: if the reviewer fails or is missing, the PR fails. |
| `precedence` | `policy.yml` | Order of findings and of settling disagreements. |
| `enforcement.mode` | `policy.yml` | `warn-only` reports "would be blocked" without failing (use for onboarding). |
| `waivers.max_days`, `require_approval`, `never_waivable` | `policy.yml` | How exceptions work. Add ids to `never_waivable` for rules that must always be fixed. |
| `ignore_paths` | `policy.yml` | Files no reviewer sees. |
| `stages.default`, `stages.file` | `policy.yml` | Stage assumed when a product declares none (strictest by default), and the file it declares it in. |

Ownership matters: `domain.yml` and `knowledge/` belong to the domain team; `policy.yml` belongs to the platform
or OCTO. Use CODEOWNERS on this repo so each team approves only its own area.

Promoting a domain from `advise` to `gate` is a one-line change to `mode`. Do it with warn-only enforcement on
first, watch a few weeks of PRs, then switch enforcement on.

## 3. Add a new area (for example FinOps)

No workflow changes are needed. Triage reads the domain list from `policy.yml`, and the review jobs fan out from
that list.

1. **Create the domain folder** `domains/finops/` with:
   - `domain.yml`: copy the security one and set `id: finops`, `title`, `mode: advise`, owner, contact, waiver route.
   - `knowledge/rules.yml`: rules with ids `FIN-001`...
   - `mcp_server.py`: identical to the security one except nothing else changes:

     ```python
     from pathlib import Path
     from governance.domain_mcp import build_server
     mcp, _knowledge = build_server(Path(__file__).parent)
     if __name__ == "__main__":
         mcp.run()
     ```

     This gives you the standard tools (`get_domain_info`, `list_rules`, `get_guidance`, `get_exemplars`,
     `get_deviation_route`) for free. Add extra tools only if the domain needs them, as enterprise alignment does.
2. **Write the reviewer** `governance/reviewers/finops.py` with `async def run_checks(ctx) -> list[Hit]`. The file
   name is the domain id with hyphens turned into underscores (`enterprise-alignment` becomes
   `enterprise_alignment.py`).
3. **Register it in `policy.yml`:**

   ```yaml
   precedence: [security, enterprise-alignment, finops, accessibility]
   domains:
     finops:
       required: false
       paths: ["terraform/**", "**/*.tf", "k8s/**"]
       labels: ["finops-review"]
   ```
4. **Test it:** add cases to `tests/test_reviewers.py` and run `python -m pytest`. Try it on a real branch with
   `python -m governance local --repo <path> --base main --head HEAD`.
5. **Roll out safely:** merge as `advise` and `required: false`, watch real PRs, tune false positives, then move to
   `gate` and `required: true` when the owner is ready.

Consuming repos need nothing: their `governance.yml` already calls the reusable workflow, and the governor check
name stays `governed / governor`.

### Domains that need judgment, not pattern matching (design, user research)

A reviewer can call an LLM instead of regexes, as long as it returns the same `Hit` records. Guidelines:
- Use the domain's MCP guidance and exemplars as the prompt context, so the model judges against the owner's
  standard rather than its own.
- Keep severity at `warn` and confidence honest (`low` or `medium`) until reviewed samples show it is reliable.
- Do not let it block. Evidence and advise modes exist for exactly this.
- Pin the model and keep the prompt in the repo so results are reproducible and reviewable.

### Using an external tool

For better detection, wrap Semgrep, Checkov, axe or Infracost inside the reviewer: run the tool on the changed
files, map each result to a `Hit` with one of your rule ids, and keep the explanations in `rules.yml`. Install the
tool in `scripts/bootstrap.sh` or the domain's action step.

## 4. Move a domain to its own team and endpoint

When a team wants to own and release its domain independently:
1. Move `domains/<id>/` into the team's repo, or host its MCP server as a remote streamable-HTTP service behind
   Entra (EKS).
2. Change `mcp_client.open_domain` so a domain with a `url` in `policy.yml` connects over HTTP instead of
   launching the local stdio server.
3. Keep the tool contract and finding schema unchanged. Nothing else in the pipeline needs to know.

## Checklist before merging any change here

- [ ] `applies_from` chosen deliberately and `python -m governance docs` run
- [ ] Rule id is new (or deliberately kept), and exists in both `rules.yml` and the detector
- [ ] Severity matches the domain's mode and confidence
- [ ] Tests cover a violation, a clean case and one false-positive guard
- [ ] `python -m pytest` passes
- [ ] The domain owner approved (CODEOWNERS)
- [ ] For a new `block`: run on a few real PRs in `warn-only` first
