# Accessibility policy

> **PoC example.** In a real deployment this page is the human-written policy, owned by the domain team and published on the documentation site. This copy is generated from [`rules.yml`](../../domains/accessibility/knowledge/rules.yml) by `python -m governance docs`, so the stage tables always match what the pipeline enforces.

**Owner:** Accessibility Practice (PoC placeholder) · **Contact:** #accessibility (placeholder) · **Enforcement:** advice only; nothing here blocks a merge.

**Exceptions:** Advise-only domain: findings never block a merge. If you disagree with one, reply on the pull request and tag the accessibility practice. Persistent disagreements are reviewed monthly and may change the guidance.

## Which guardrails apply to your product

A product declares its stage (see [guardrails by stage](../guardrails.md)). A guardrail applies from the stage shown and to every later stage, so a production product has all of them.

| Rule | 🔍 Scan | 🧪 Pilot | 🚀 Production |
| --- | :---: | :---: | :---: |
| [A11Y-001 Image without alternative text](#a11y-001-image-without-alternative-text) | ▫️ | ⚠️ | ⚠️ |
| [A11Y-002 Page language not set](#a11y-002-page-language-not-set) | ⚠️ | ⚠️ | ⚠️ |
| [A11Y-003 Form control without a label](#a11y-003-form-control-without-a-label) | ▫️ | ⚠️ | ⚠️ |
| [A11Y-004 Link text does not describe its destination](#a11y-004-link-text-does-not-describe-its-destination) | ▫️ | ▫️ | ⚠️ |
| [A11Y-005 Page has no title](#a11y-005-page-has-no-title) | ⚠️ | ⚠️ | ⚠️ |
| [A11Y-006 Button without an accessible name](#a11y-006-button-without-an-accessible-name) | ▫️ | ⚠️ | ⚠️ |

⛔ blocks the merge · ⚠️ warning · ℹ️ note · ▫️ does not apply yet

## A11Y-001 Image without alternative text

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⚠️ warning

An image has no alt attribute, so screen reader users get nothing (or the file name) in its place.

**Why:** Every img needs an alt attribute. Describe the purpose of informative images. Use alt="" for purely decorative images so assistive technology skips them.

**What to do:** Add alt text that conveys the image's purpose, or alt="" if it is decorative.

Avoid:

```
<img src="chart.png">
```

Prefer:

```
<img src="chart.png" alt="Quarterly sign-ups rose from 120 to 340">
```

## A11Y-002 Page language not set

**Applies from:** 🔍 Scan  
**By stage:** 🔍 Scan: ⚠️ warning → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⚠️ warning

Without a lang attribute on the html element screen readers may pronounce the page in the wrong language.

**Why:** Set the primary language of every page on the html element.

**What to do:** Add lang to the html element, for example <html lang="en-GB">.

Avoid:

```
<html>
```

Prefer:

```
<html lang="en-GB">
```

## A11Y-003 Form control without a label

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⚠️ warning

An input, select or textarea has no programmatic label, so assistive technology cannot tell users what to enter.

**Why:** Every form control needs a visible label associated with it (label for/id, or wrapping the control). Use aria-label only when a visible label is not possible.

**What to do:** Associate a visible <label> with the control using for and id.

Avoid:

```
<input type="email" name="email">
```

Prefer:

```
<label for="email">Email address</label>
<input id="email" type="email" name="email" autocomplete="email">
```

## A11Y-004 Link text does not describe its destination

**Applies from:** 🚀 Production  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ▫️ not yet → 🚀 Production: ⚠️ warning

Link text such as "click here" or "read more" is meaningless when links are read out of context.

**Why:** Link text should make sense on its own and describe where the link goes.

**What to do:** Rewrite the link text to describe the destination.

Avoid:

```
<a href="/pricing">click here</a>
```

Prefer:

```
<a href="/pricing">See pricing plans</a>
```

## A11Y-005 Page has no title

**Applies from:** 🔍 Scan  
**By stage:** 🔍 Scan: ⚠️ warning → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⚠️ warning

A page without a title gives screen reader users and tab bars nothing to identify it by.

**Why:** Every page needs a short, unique, descriptive title element.

**What to do:** Add a descriptive <title> inside <head>.

Avoid:

```
<head></head>
```

Prefer:

```
<head><title>Pricing plans - Example</title></head>
```

## A11Y-006 Button without an accessible name

**Applies from:** 🧪 Pilot  
**By stage:** 🔍 Scan: ▫️ not yet → 🧪 Pilot: ⚠️ warning → 🚀 Production: ⚠️ warning

A button with no text and no aria-label is announced as just "button".

**Why:** Give every button visible text, or an aria-label when it only contains an icon.

**What to do:** Add visible text or an aria-label that says what the button does.

Avoid:

```
<button><svg>...</svg></button>
```

Prefer:

```
<button aria-label="Close dialog"><svg aria-hidden="true">...</svg></button>
```

