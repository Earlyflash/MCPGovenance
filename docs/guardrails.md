# Guardrails by product stage

A product says how mature it is. The more mature, the more guardrails it must meet, and some get stricter. Each guardrail names the stage it **starts** to apply in, and it then applies to that stage and every later one.

```mermaid
flowchart LR
    scan["🔍 Scan<br/><b>+4 new · 4 in force</b><br/>SEC-001 Hard-coded secret<br/>EA-001 Banned technology<br/>A11Y-002 Page language not set<br/>A11Y-005 Page has no title"]
    pilot["🧪 Pilot<br/><b>+11 new · 15 in force</b><br/>SEC-002 Shell command built for execution<br/>SEC-003 TLS certificate verification disabled<br/>SEC-004 Dynamic code evaluation<br/>SEC-005 Container runs as root<br/>SEC-006 Network rule open to the whole internet<br/>EA-002 Deprecated technology<br/>EA-003 Technology not in the catalogue<br/>EA-005 Evidence missing for off-road technology<br/>A11Y-001 Image without alternative text<br/>A11Y-003 Form control without a label<br/>A11Y-006 Button without an accessible name"]
    production["🚀 Production<br/><b>+3 new · 18 in force</b><br/>EA-004 Technology on trial or tolerated<br/>EA-006 ADR incomplete<br/>A11Y-004 Link text does not describe its destination<br/>⏫ SEC-002 now blocks the merge<br/>⏫ SEC-005 now blocks the merge<br/>⏫ SEC-006 now blocks the merge<br/>⏫ EA-002 now blocks the merge<br/>⏫ EA-003 now blocks the merge"]
    scan -->|keeps all of these, adds more| pilot
    pilot -->|keeps all of these, adds more| production
```

## What each stage means

| Stage | Meaning |
| --- | --- |
| 🔍 **Scan** | exploring an idea; only the must-never-happen guardrails apply |
| 🧪 **Pilot** | real users, limited scope; the everyday guardrails apply |
| 🚀 **Production** | relied upon; every guardrail applies |

## How many guardrails apply

| Stage | Added at this stage | In force | Made stricter at this stage |
| --- | :---: | :---: | :---: |
| 🔍 Scan | 4 | 4 | 0 |
| 🧪 Pilot | 11 | 15 | 0 |
| 🚀 Production | 3 | 18 | 5 |

## Every guardrail, by stage

| Rule | Name | Area | 🔍 Scan | 🧪 Pilot | 🚀 Production |
| --- | --- | --- | :---: | :---: | :---: |
| `SEC-001` | Hard-coded secret | security | ⛔ | ⛔ | ⛔ |
| `SEC-002` | Shell command built for execution | security | ▫️ | ⚠️ | ⛔ |
| `SEC-003` | TLS certificate verification disabled | security | ▫️ | ⛔ | ⛔ |
| `SEC-004` | Dynamic code evaluation | security | ▫️ | ⛔ | ⛔ |
| `SEC-005` | Container runs as root | security | ▫️ | ⚠️ | ⛔ |
| `SEC-006` | Network rule open to the whole internet | security | ▫️ | ⚠️ | ⛔ |
| `EA-001` | Banned technology | enterprise-alignment | ⛔ | ⛔ | ⛔ |
| `EA-002` | Deprecated technology | enterprise-alignment | ▫️ | ⚠️ | ⛔ |
| `EA-003` | Technology not in the catalogue | enterprise-alignment | ▫️ | ⚠️ | ⛔ |
| `EA-004` | Technology on trial or tolerated | enterprise-alignment | ▫️ | ▫️ | ℹ️ |
| `EA-005` | Evidence missing for off-road technology | enterprise-alignment | ▫️ | ⛔ | ⛔ |
| `EA-006` | ADR incomplete | enterprise-alignment | ▫️ | ▫️ | ⚠️ |
| `A11Y-001` | Image without alternative text | accessibility | ▫️ | ⚠️ | ⚠️ |
| `A11Y-002` | Page language not set | accessibility | ⚠️ | ⚠️ | ⚠️ |
| `A11Y-003` | Form control without a label | accessibility | ▫️ | ⚠️ | ⚠️ |
| `A11Y-004` | Link text does not describe its destination | accessibility | ▫️ | ▫️ | ⚠️ |
| `A11Y-005` | Page has no title | accessibility | ⚠️ | ⚠️ | ⚠️ |
| `A11Y-006` | Button without an accessible name | accessibility | ▫️ | ⚠️ | ⚠️ |

⛔ blocks the merge · ⚠️ warning · ℹ️ note · ▫️ does not apply yet

A guardrail can get **stricter** as a product matures: for example a warning at pilot that blocks in production (`escalate: { production: block }` in the rule). Severity can rise with the stage but never fall.

Each area also has its own page with the full wording: [security](policy/security.md), [enterprise-alignment](policy/enterprise-alignment.md), [accessibility](policy/accessibility.md).

## Declaring your stage

Add a `.governance.yml` file to the root of your repository:

```yaml
stage: pilot   # scan | pilot | production
```

Or, if you prefer, put a marker in your `README.md`:

```markdown
<!-- governance-stage: pilot -->
```

A platform team can also set it as a repository setting (the `stage` input of the workflow, from a repository variable), which a pull request cannot change.

| Rule | What it means |
| --- | --- |
| Strictest wins | If it is declared in more than one place, the highest stage applies. |
| A PR can raise it, never lower it | Raising the stage in a pull request re-checks the **whole product**, not only the changed lines. Lowering it has no effect until the lower stage is merged with code owner approval. |
| Not declared | The strictest stage (production) applies, so forgetting never makes a product look safer than it is. |
| Seeing ahead | Findings for guardrails from a later stage are shown in the PR comment under *Coming at a higher stage*, but do not count. |

