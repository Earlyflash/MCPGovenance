# Security policy

> **PoC example.** In a real deployment this page is the human-written policy, owned by the domain team and published on the documentation site. This copy is generated from [`rules.yml`](../../domains/security/knowledge/rules.yml) by `python -m governance docs`, so the stage tables always match what the pipeline enforces.

**Owner:** Security Engineering (PoC placeholder) · **Contact:** #security-help (placeholder) · **Enforcement:** rules marked *Blocks the merge* stop a pull request until fixed or waived.

**Exceptions:** Add an entry to .governance-waivers.yml (rule_id, optional path, reason, approver, expires within 90 days) and have the security domain owner approve the pull request. SEC-001 (secrets) can never be waived: remove the secret and rotate it.

## Which guardrails apply to your product

A product declares its stage (see [guardrails by stage](../guardrails.md)). A guardrail applies from the stage shown and to every later stage, so a production product has all of them.

| Rule | 🔍 Scan | 🧪 Pilot | 🚀 Production |
| --- | :---: | :---: | :---: |
| [SEC-001 Hard-coded secret](#sec-001-hard-coded-secret) | ⛔ | ⛔ | ⛔ |
| [SEC-002 Shell command built for execution](#sec-002-shell-command-built-for-execution) | ▫️ | ⚠️ | ⛔ |
| [SEC-003 TLS certificate verification disabled](#sec-003-tls-certificate-verification-disabled) | ▫️ | ⛔ | ⛔ |
| [SEC-004 Dynamic code evaluation](#sec-004-dynamic-code-evaluation) | ▫️ | ⛔ | ⛔ |
| [SEC-005 Container runs as root](#sec-005-container-runs-as-root) | ▫️ | ⚠️ | ⛔ |
| [SEC-006 Network rule open to the whole internet](#sec-006-network-rule-open-to-the-whole-internet) | ▫️ | ⚠️ | ⛔ |

⛔ blocks the merge · ⚠️ warning · ℹ️ note · ▫️ does not apply yet

## SEC-001 Hard-coded secret

**Applies from:** 🔍 Scan  
**By stage:** 🔍 Scan: ⛔ blocks the merge → 🧪 Pilot: ⛔ blocks the merge → 🚀 Production: ⛔ blocks the merge

A credential, key or token is written into source control, where it is visible to everyone with read access and persists in history.

**What it means for people:** Anyone who can see this code can use the secret, and once it is in the history it is hard to take back. Sorting it now protects you, your team and your customers.

**Why:** Secrets must never be committed. Read them at runtime from the environment or a secrets manager. If one has been committed it is compromised: rotate it first, then remove it. Deleting the line is not enough.

**What to do:** Remove the value, load it from an environment variable or secrets manager, and rotate the exposed credential.

Avoid:

```
DB_PASSWORD = "hunter2hunter2"
```

Prefer:

```
import os
DB_PASSWORD = os.environ["DB_PASSWORD"]  # injected by the platform from the secrets manager
```

## SEC-002 Shell command built for execution

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⛔ blocks the merge

Running commands through a shell (shell=True, os.system) turns any untrusted input in the command into command injection.

**What it means for people:** If any part of the command comes from a user, someone could make your server run something you never intended.

**Why:** Pass an argument list to subprocess without a shell. If a shell is genuinely required, the input must be constant or strictly validated, and the reason recorded in a waiver.

**What to do:** Use subprocess.run([...], shell=False) with an argument list, or request a waiver explaining why a shell is needed.

Avoid:

```
subprocess.run(f"convert {filename} out.png", shell=True)
```

Prefer:

```
subprocess.run(["convert", filename, "out.png"], check=True)
```

## SEC-003 TLS certificate verification disabled

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⛔ blocks the merge → 🚀 Production: ⛔ blocks the merge

Disabling certificate verification removes the protection HTTPS provides and allows man-in-the-middle attacks.

**What it means for people:** Without the check, someone on the network could pretend to be the other side and read or change what is sent, such as your customers' data.

**Why:** Never disable certificate verification, including in test or development code that can be copied elsewhere. Trust an internal certificate authority by configuring its certificate bundle instead.

**What to do:** Remove the override. If an internal CA is involved, point the client at its CA bundle (for example verify="/etc/ssl/internal-ca.pem").

Avoid:

```
requests.get(url, verify=False)
```

Prefer:

```
requests.get(url, verify="/etc/ssl/internal-ca.pem")
```

## SEC-004 Dynamic code evaluation

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⛔ blocks the merge → 🚀 Production: ⛔ blocks the merge

eval, exec and new Function run text as code, so any attacker-influenced string becomes arbitrary code execution.

**What it means for people:** Text that reaches this could be run as code, so a cleverly crafted input might take control of your application.

**Why:** Parse data with a data parser (json, ast.literal_eval) and dispatch behaviour through explicit lookup tables, not by evaluating strings.

**What to do:** Replace eval/exec with a parser or an explicit mapping of allowed operations.

Avoid:

```
result = eval(user_expression)
```

Prefer:

```
import ast
value = ast.literal_eval(user_value)   # literals only, never code
```

## SEC-005 Container runs as root

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⛔ blocks the merge

A container whose final stage has no non-root USER runs as root, which widens the impact of any compromise.

**What it means for people:** If anything went wrong inside the container, running as root would give it far more power than it needs.

**Why:** Create an unprivileged user in the image and switch to it before the entrypoint.

**What to do:** Add a non-root USER in the final stage of the Dockerfile.

Avoid:

```
FROM python:3.12-slim
COPY . /app
CMD ["python", "/app/app.py"]
```

Prefer:

```
FROM python:3.12-slim
RUN useradd --create-home app
COPY --chown=app . /app
USER app
CMD ["python", "/app/app.py"]
```

## SEC-006 Network rule open to the whole internet

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⛔ blocks the merge

A rule allowing 0.0.0.0/0 or ::/0 exposes the resource to every address on the internet.

**What it means for people:** Anyone on the internet could try to reach this, not only the people who should.

**Why:** Scope ingress to known CIDR ranges or security groups. Public ingress is acceptable only behind an approved load balancer or CDN.

**What to do:** Restrict the CIDR to the ranges that need access, or reference a security group.

Avoid:

```
cidr_blocks = ["0.0.0.0/0"]
```

Prefer:

```
cidr_blocks = [var.office_cidr]
```

