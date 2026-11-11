# Enterprise technology alignment policy

> **PoC example.** In a real deployment this page is the human-written policy, owned by the domain team and published on the documentation site. This copy is generated from [`rules.yml`](../../domains/enterprise-alignment/knowledge/rules.yml) by `python -m governance docs`, so the stage tables always match what the pipeline enforces.

**Owner:** Office of the CTO (PoC placeholder) · **Contact:** #architecture (placeholder) · **Enforcement:** checks that the required evidence exists; people judge whether the decision is right.

**Exceptions:** Banned technology needs a waiver in .governance-waivers.yml approved by the Office of the CTO. For anything else off the paved road, add an ADR under docs/adr/ that records the guidance consulted, the deviation and any tension with strategy. This domain checks that the evidence exists, not that the decision is right: people judge that.

## Which guardrails apply to your product

A product declares its stage (see [guardrails by stage](../guardrails.md)). A guardrail applies from the stage shown and to every later stage, so a production product has all of them.

| Rule | 🔍 Scan | 🧪 Pilot | 🚀 Production |
| --- | :---: | :---: | :---: |
| [EA-001 Banned technology](#ea-001-banned-technology) | ⛔ | ⛔ | ⛔ |
| [EA-002 Deprecated technology](#ea-002-deprecated-technology) | ▫️ | ⚠️ | ⛔ |
| [EA-003 Technology not in the catalogue](#ea-003-technology-not-in-the-catalogue) | ▫️ | ⚠️ | ⛔ |
| [EA-004 Technology on trial or tolerated](#ea-004-technology-on-trial-or-tolerated) | ▫️ | ▫️ | ℹ️ |
| [EA-005 Evidence missing for off-road technology](#ea-005-evidence-missing-for-off-road-technology) | ▫️ | ⛔ | ⛔ |
| [EA-006 ADR incomplete](#ea-006-adr-incomplete) | ▫️ | ▫️ | ⚠️ |

⛔ blocks the merge · ⚠️ warning · ℹ️ note · ▫️ does not apply yet

## EA-001 Banned technology

**Applies from:** 🔍 Scan  
**By stage:** 🔍 Scan: ⛔ blocks the merge → 🧪 Pilot: ⛔ blocks the merge → 🚀 Production: ⛔ blocks the merge

This technology is on the banned list in the technology catalogue.

**Why:** Banned technology must not be introduced or kept. An ADR does not unlock it. Only a waiver approved by the Office of the CTO does, and it must expire.

**What to do:** Replace it with the preferred alternative named above, or request a time-limited waiver from the Office of the CTO.

Avoid:

```
"dependencies": { "event-stream": "^3.3.6" }
```

Prefer:

```
# use the platform's built-in streams, or the catalogue's preferred alternative
```

## EA-002 Deprecated technology

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⛔ blocks the merge

This technology is deprecated in the technology catalogue. New use is discouraged.

**Why:** Do not start new work on deprecated technology. Existing use should move to the preferred alternative on the next planned change. If you must add it, record why in an ADR.

**What to do:** Use the preferred alternative, or record the reason in an ADR under docs/adr/.

Avoid:

```
"dependencies": { "moment": "^2.30.0" }
```

Prefer:

```
"dependencies": { "date-fns": "^3.6.0" }
```

## EA-003 Technology not in the catalogue

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⛔ blocks the merge

This technology is not in the technology catalogue, so it has not been assessed. Unknown is not the same as permitted.

**Why:** Prefer an adopted or approved technology for the same job. If nothing on the catalogue fits, open an assessment request and record the decision in an ADR so the catalogue can learn from it.

**What to do:** Pick a catalogue option, or add an ADR under docs/adr/ and request an assessment.

Avoid:

```
"dependencies": { "left-pad": "^1.3.0" }
```

Prefer:

```
# choose an adopted option, or link the assessment request from your ADR
```

## EA-004 Technology on trial or tolerated

**Applies from:** 🚀 Production  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ▫️ not yet → 🚀 Production: ℹ️ note

This technology is allowed only under the conditions shown in the catalogue.

**Why:** Trial technology is for the use cases named in its conditions. Tolerated technology is for existing systems only.

**What to do:** Check the conditions apply to your use. If they do not, choose an adopted technology.

Avoid:

```
# using a trial technology for a customer-facing product
```

Prefer:

```
# using a trial technology inside an internal tool, as its conditions allow
```

## EA-005 Evidence missing for off-road technology

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⛔ blocks the merge → 🚀 Production: ⛔ blocks the merge

The change introduces technology that is off the paved road, but no ADR is included to record the decision.

**Why:** Off-road choices are allowed when they are deliberate and recorded. Add an ADR under docs/adr/ using the template: the guidance you consulted (with versions), the deviation, and any tension with strategy.

**What to do:** Add docs/adr/NNNN-title.md from the template and complete every section.

Avoid:

```
# PR adds an unassessed framework and no docs/adr/ file
```

Prefer:

```
docs/adr/0007-use-htmx-for-internal-tools.md   # with Guidance consulted, Deviations, Tensions
```

## EA-006 ADR incomplete

**Applies from:** 🚀 Production  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ▫️ not yet → 🚀 Production: ⚠️ warning

The ADR is missing a required section or still contains TBD.

**Why:** An ADR must have the sections Guidance consulted, Deviations requiring approval and Tensions with strategy. "None" is a valid answer; "TBD" is not.

**What to do:** Complete the missing sections. Write "None" where nothing applies.

Avoid:

```
## Guidance consulted
TBD
```

Prefer:

```
## Guidance consulted
| Entry | guidance_version | Result |
| --- | --- | --- |
| htmx | 2026.11.1+ab12cd34 | trial, internal tools only |
```

