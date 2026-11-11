# Accessibility policy

> **PoC example.** In a real deployment this page is the human-written policy, owned by the Accessibility Practice and published on the documentation site. Each section below is one rule. The machine-readable form used by the pipeline is [`rules.yml`](../../domains/accessibility/knowledge/rules.yml); keep the two in step when either changes.

**Owner:** Accessibility Practice (PoC placeholder) · **Contact:** #accessibility (placeholder) · **Enforcement:** advice only; nothing here blocks a merge.

**Exceptions:** Advise-only domain: findings never block a merge. If you disagree with one, reply on the pull request and tag the accessibility practice. Persistent disagreements are reviewed monthly and may change the guidance.

## A11Y-001 Image without alternative text

**Effect:** Blocks the merge

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

**Effect:** Blocks the merge

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

**Effect:** Blocks the merge

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

**Effect:** Warning

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

**Effect:** Warning

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

**Effect:** Blocks the merge

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
