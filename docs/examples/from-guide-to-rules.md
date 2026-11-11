# From a human-written design guide to governed rules

A worked example of how raw human knowledge becomes the readable policy and the YAML rules this repository uses. Everything here is invented for the example: the guide, the interview, the claims and the counts. The new rules shown (A11Y-007 to A11Y-012) are **not** in the repository's `rules.yml`.

## Does this make sense?

Yes, and it is the honest start of the process. Real policy does not begin as tidy rules. It begins as a person writing down what they know, in their own voice. The demo already shows the last two steps (a readable policy page, then YAML). This document adds the step before them, and shows what happens to a real piece of writing on the way.

The four stages:

1. **A human guide.** Written by a design lead, with no thought of governance. Stories, opinions and rules of thumb, all mixed together.
2. **Analysis.** Break the guide into single claims and sort each one: can a program check it from a pull request, or does it need a person?
3. **The readable policy.** For the claims a program can check, write the policy entry the way our policy pages look today.
4. **YAML.** The policy entry becomes a rule. The claims that cannot be checked stay as guidance, and are not forced into code.

One point worth making to the team: **only a little over half of a good human guide can be checked automatically.** The rest is still valuable, and it still reaches agents and people through the guidance, but it does not become a blocking check. In the example below, 11 of 19 claims become checks and 8 do not.

The same four stages also work when the starting point is a recorded interview with a practitioner instead of a written guide. That is worked through in the second half of this document.

## Stage 1: the human guide

This is the kind of thing a design lead writes on a wiki page one afternoon. It has no rule numbers, no severities and no mention of pipelines. Notice how it mixes principles, opinions, specific rules and advice, in the order the author thought of them.

> ### How we think about accessible design
>
> I keep getting asked what "good" looks like for accessibility, so here is my attempt to write it down. It is not a standard, just how I would want a new designer to think.
>
> **Start early.** Accessibility is not a layer you add at the end. If you have designed a screen that only works with a mouse and good eyesight, no amount of fixing later will rescue it. Start from how someone would use it with a keyboard, or a screen reader, or with the text blown up to twice the size.
>
> **Images.** Every picture that tells you something needs a description. Say what it is for, not what it looks like: "sign-ups went from 120 to 340" beats "a blue bar chart". If it is just decoration, say so explicitly so the screen reader skips it.
>
> **Words on links and buttons.** Nothing drives me madder than a page full of "click here". People who use screen readers often pull up a list of every link on the page, and a list of forty "click here"s is useless. Same for icon-only buttons: the little cog or the magnifying glass needs a name someone can hear.
>
> **Forms.** Put the label where people can see it, above the box, not just as grey placeholder text that vanishes when you type. Say what format you want before they get it wrong. And when something does go wrong, tell them what and how to fix it, in words, not just a red border.
>
> **Colour.** Do not use colour as the only way to say something. Red and green status with nothing else is a classic. And make sure text has enough contrast with its background, particularly the pale grey on white that designers love. If you have to squint, so will a lot of other people.
>
> **Keyboard.** You should be able to do everything without a mouse and always see where you are. Please never remove the focus outline unless you have put something better in its place. And the order you tab through things should follow the order you read them.
>
> **Structure.** Headings are how screen reader users skim, so use them in order: one main title, then sections, then subsections. Do not pick a heading because it looks the right size; style it instead. Give every page its own title too, so tabs and browser history make sense. Oh, and tell the page what language it is written in, otherwise the screen reader can read English in a French accent (or worse).
>
> **Movement.** Be careful with anything that moves on its own. Auto-playing video with sound is a no. Anything that animates for more than a few seconds needs a pause button, and respect it when someone has told their device to reduce motion.
>
> **Zoom.** People zoom. Do not lock the page so it cannot be zoomed, and check it still works at 200%.
>
> **Plain words.** Write like a human. Short sentences, no jargon, and say the useful thing first.
>
> **Finally,** test with real people when you can. Even one session with someone who uses a screen reader every day will teach you more than a checklist will.

## Stage 2: analysis

Read the guide once and split it into single claims. Then ask three questions of each:

1. **Can a program tell from the files in a pull request?** If not, it cannot be a check.
2. **Is it already one of our rules?** If so, it only confirms the rule, and may sharpen the wording.
3. **If it cannot be checked, is it still useful?** Usually yes. It becomes advice that people and agents read.

This is the step an assistant is good at, as a first draft. A person from the accessibility practice reviews it. The result for this guide:

| # | What the guide says | Sort | Becomes |
| --- | --- | --- | --- |
| 1 | Design for keyboard, screen reader and zoom from the start | Principle | The opening of the policy page |
| 2 | Informative images need a description of their purpose | Check, exists | A11Y-001 |
| 3 | Decorative images are marked so they are skipped | Check, exists | A11Y-001 (the empty alt allowance) |
| 4 | Avoid "click here" link text | Check, exists | A11Y-004 |
| 5 | Icon-only buttons need a name | Check, exists | A11Y-006 |
| 6 | Labels visible, not only placeholder text | Check, exists | A11Y-003 |
| 7 | Say the format up front, explain errors in words | Advice | Guidance, no check |
| 8 | Do not use colour as the only signal | Advice | Guidance, no check |
| 9 | Text has enough contrast | Needs another tool | Guidance now; a contrast tool later |
| 10 | Everything works by keyboard, in reading order | Needs another tool | Guidance now; a browser test later |
| 11 | Never remove the focus outline without a replacement | Check, new | A11Y-007 |
| 12 | Headings in order, one main title | Check, new | A11Y-008 |
| 13 | Every page has its own title | Check, exists | A11Y-005 |
| 14 | Say what language the page is in | Check, exists | A11Y-002 |
| 15 | No auto-playing video with sound | Check, new | A11Y-009 |
| 16 | Pause control and respect for reduced motion | Advice | Guidance, no check |
| 17 | Do not lock zoom; works at 200% | Check, new (zoom lock only) | A11Y-010, and the 200% part is advice |
| 18 | Plain words, short sentences | Advice | Guidance, no check |
| 19 | Test with real people | Process | A line in the policy, no rule |

The count: **7 claims confirm existing rules** (they map to the six rules already in the demo), **4 become new checks**, **4 are advice**, **2 need a different tool** and **2 are principle or process**. That is 11 of 19 that turn into checks, and 8 that stay as guidance.

Two things came out of the analysis. First, the guide supports all six rules we already have. Be careful with that one: the guide was written for this example, so it is not independent evidence, but with a real guide it is a useful check that the rules match what practitioners believe. Second, it finds four rules we do not have yet, which is the real value of writing the analysis down.

### Decisions a person makes

The analysis cannot decide these. The accessibility practice does, and records the reason.

| Rule | Applies from | Severity | Confidence | Why |
| --- | --- | --- | --- | --- |
| A11Y-007 Focus outline removed | Pilot | Block (advice-only today, so a warning) | High | Easy to detect, and it harms keyboard users directly |
| A11Y-008 Heading levels skipped | Pilot | Warn | Medium | Sometimes done for a reason, so it should not block |
| A11Y-009 Video autoplays with sound | Production | Warn | High | Rare in practice, and clearly wrong |
| A11Y-010 Page zoom is locked | Pilot | Warn | High | Easy to detect; a few mobile apps need it |

## Stage 3: the readable policy

For each claim that becomes a check, a person writes the policy entry in the form our policy pages use. It is shorter and firmer than the guide, it says why, and it shows what to avoid and what to prefer. This page is what developers and the governance team actually read, and what every finding links to.

Here is one claim taken all the way through. The source is a single sentence from the guide:

> Please never remove the focus outline unless you have put something better in its place.

And the entry it becomes:

> ### A11Y-007 Focus outline removed
>
> **Applies from:** Pilot
>
> A style rule removes the visible focus outline from interactive elements, so keyboard users cannot see where they are on the page.
>
> **Why:** People who cannot use a mouse move through a page with the Tab key. The outline is the only thing that shows them where they are. Removing it without a replacement leaves them lost.
>
> **What to do:** Keep the default outline, or replace it with a clearly visible style on :focus-visible, such as a thick outline or a strong border.
>
> **Avoid:** `a:focus { outline: none; }`
>
> **Prefer:** `a:focus-visible { outline: 3px solid #1a5fb4; outline-offset: 2px; }`

What the writer did, in order:

1. **Kept the author's reason** and made it plain: "people cannot see where they are".
2. **Made the condition exact.** "Unless you have put something better in its place" became "removes the outline, with no :focus-visible replacement". A program can check that; it cannot check "better".
3. **Added a concrete fix and an example pair**, so a developer or an agent can act on it without asking.
4. **Kept it short.** The story and the opinions stay in the original guide, which the policy page can link to for readers who want the background.

## Stage 4: the YAML

The policy entry now becomes a rule in the accessibility domain's `rules.yml`. This is mostly a mechanical translation, because the policy entry already holds every field. The domain team changes it with an ordinary pull request, and the governance team approves it.

```yaml
- id: A11Y-007
  applies_from: pilot
  title: Focus outline removed
  severity: block          # the accessibility area is advice-only, so this shows as a warning
  confidence: high
  tags: [keyboard, focus, outline, css, wcag-2.4.7]
  summary: A style rule removes the visible focus outline, so keyboard users cannot see where they are.
  guidance: >-
    People who cannot use a mouse move through a page with the Tab key. The outline is the only thing that
    shows them where they are. Keep it, or replace it with a clearly visible :focus-visible style.
  remediation: Keep the default outline, or add a visible :focus-visible style such as a 3px solid outline.
  exemplars:
    bad: |
      a:focus { outline: none; }
    good: |
      a:focus-visible { outline: 3px solid #1a5fb4; outline-offset: 2px; }
```

There is one more piece, and it is the only code. A short detector in the accessibility reviewer looks for a style that removes an outline with no `:focus-visible` replacement, and reports `A11Y-007` when it finds one. Everything the developer sees (the wording, the fix, the example, the link to the policy page) comes from the YAML.

### What is deliberately not turned into code

The advice claims (7, 8, 16 and 18) go into the same file, with the lowest severity and no detector. They never produce a finding, but they are served to agents and people through the guidance, so an agent that asks "how should I handle form errors?" gets the answer.

```yaml
- id: A11Y-011
  applies_from: scan
  title: Explain form errors in words
  severity: info
  confidence: low
  tags: [forms, errors, validation, wcag-3.3.1]
  summary: Tell people what went wrong and how to fix it, in words, not only with a red border.
  guidance: >-
    Say the expected format before people get it wrong. When something fails, name the field, say what is
    wrong and how to fix it. Do not rely on colour alone to show an error.
  remediation: This is a design and writing choice. No automatic check exists for it.
```

The two claims that need another tool (contrast and full keyboard operation) go in the same way for now. Later, a contrast checker or a browser test can be added as a new detector without changing the policy or the YAML, which is the point of keeping the two apart.

### What this document does not do

None of these new rules has been added to the demo repository. They are an illustration of the method, and the numbers (19 claims, 11 checks) belong to this one invented guide. If you would like them in the repo, the four checks need detectors and tests, which is a small piece of work.

## Starting from an interview instead

A written guide is not always there. Often the knowledge sits in someone's head, and the quickest way to get it out is a conversation, recorded and transcribed. The only prompt the leader needs is: **"Tell me how your team reviews a system for accessibility."** The rest is follow-up questions.

This transcript is invented for the example. It is lightly tidied, but it keeps the tangents, the half-remembered details and the things said twice, because real ones are like that.

> **Alex (leader):** Thanks for making time, Priya. I'd like to understand how your team reviews a system for accessibility. Walk me through it like I've never seen it.
>
> **Priya (accessibility specialist):** Sure. So, honestly, it starts with someone asking us. A product team gets close to launch, someone remembers accessibility, and we get a message in the channel. I'd love for that to be earlier, but that's how it is.
>
> **Alex:** What's the first thing you do?
>
> **Priya:** I ask what it is and who uses it. A staff intranet page is different from a public application form. If it's something the public has to use to get a service, I'm much stricter, because they can't just go and ask someone for help. Then I run an automated scan. We use axe. It takes ten minutes and catches the obvious stuff: missing alt text, missing labels, empty buttons, no page language, that sort of thing. I'd say it catches maybe a third of real problems. People think a clean scan means it's accessible, and it really doesn't.
>
> **Alex:** So what's the rest?
>
> **Priya:** The manual pass. First, I put the mouse away and try to do the main journey with the keyboard only. Can I tab to everything? Can I see where I am? Does the order make sense? Can I get out of a popup? You'd be amazed how often there's a modal you can't escape. Then I do the same journey with a screen reader. NVDA on Windows, VoiceOver on the Mac, and if it's a mobile app, VoiceOver on the iPhone. I'm listening for whether it makes sense. Do the buttons have names? Do the headings help me find my way?
>
> **Alex:** And after that?
>
> **Priya:** Zoom to 400 percent and see if it falls apart. Check colour contrast, which axe does partly, but not on images of text or on hover states. Check the forms properly: labels, errors, whether the error actually tells you what went wrong. Forms are where most people get stuck, so I spend the most time there. And I look at anything that moves or plays on its own. Oh, and PDFs. People forget PDFs.
>
> **Alex:** What counts as a failure, and what counts as a note?
>
> **Priya:** That's the judgement call. My rule is: can someone complete the task? If a keyboard user can't submit the form, or a screen reader user can't tell what a button does, that's a fail, and I won't sign off. If a heading level is skipped, or a link says "read more", that's annoying and I'll write it down, but I wouldn't stop a launch for it. Though if the same thing is everywhere on the page, I get less relaxed. A hundred small things add up to a big thing.
>
> **Alex:** What do you do when a team can't fix something in time?
>
> **Priya:** We can sign off with a plan, if it's honest. They tell me what's broken, who's fixing it and by when. I'm not going to make a team miss a date over something that's affecting a few people for a few weeks, as long as it's not blocking a core task. But I put the date in the report and I do chase it. Third-party stuff is the hard one. A chat widget or a payment form from a supplier, and they say it's the supplier's problem. Technically yes, but the user doesn't know that. I'd ask for the supplier's accessibility statement and I'd want to see it's real, not a logo.
>
> **Alex:** What do you record?
>
> **Priya:** A short report. What I tested, with what, what I found, how bad, and what we agreed. Usually it's a week from when I get the request, if the team is ready. If they're not, it takes a lot longer. We also keep the standard as WCAG 2.2, level AA, I think. Or is it 2.1 still? I'd have to check the policy. Anyway, AA.
>
> **Alex:** What would make your job easier?
>
> **Priya:** Being asked sooner. Honestly, if the design system components were solid, half of this would disappear, because a team using the proper button and the proper form field gets most of it for free. The problems come from custom stuff. A custom dropdown is almost always broken. And I'd love teams to run the scan themselves before they ask me, so I'm not spending my week telling people they have no page title.
>
> **Alex:** Anything you'd tell a new starter?
>
> **Priya:** Use it yourself. Sit with someone who relies on a screen reader if you can. Thirty minutes of that changes how you design.

### What an interview gives that a written guide does not

The analysis in Stage 2 works the same way here: split the transcript into single claims and sort them. The material is different, though, and that is worth knowing before you start.

- **More process, less rule.** A review has steps, an order and a turnaround time. Much of this belongs in how the team works, not in a pull request check.
- **Severity lives here.** "Can someone complete the task?" is the practitioner's real test for block versus note. A written guide rarely says it. It is exactly what the governance team needs to set severities and stages, and it is better recorded than guessed.
- **Context changes the rule.** Public-facing services are held to a higher standard than an intranet page. That is close to the idea of stages and risk tiers we already have, and it may point to risk tiers on the roadmap.
- **Things need checking.** "WCAG 2.2, level AA, I think" has to be confirmed against the actual standard before it is written into a policy. Analysis should mark these claims and ask, not copy them.
- **Some of it is a gap, not a rule.** "Run the scan yourself first" and "a custom dropdown is almost always broken" are tips that could become guidance, or a new check for custom components, which is demand the knowledge layer could record.

## The interview, worked down the stages

The same method, applied to the transcript. Split it into single claims, then sort each one.

| # | What Priya says | Sort | Becomes |
| --- | --- | --- | --- |
| 1 | Reviews are requested too late | Process | Already answered by the pull request check, which reviews from the first change. Say so in the policy introduction. |
| 2 | Ask what it is and who uses it; public services are held to a stricter standard | Context | A risk tier idea (roadmap C3). Not a rule. |
| 3 | Run an automated scan first, and a clean scan does not mean accessible | Principle | The pipeline is that scan. The policy says it is a floor, not a pass. |
| 4 | Keyboard only: reach everything, see where you are, logical order, escape from a popup | Needs another tool | Guidance now; a browser test later. Visible focus is already A11Y-007 from the guide. |
| 5 | With a screen reader, buttons have names | Check, exists | A11Y-006 |
| 6 | With a screen reader, headings help you find your way | Check, new (also in the guide) | A11Y-008 |
| 7 | Zoom to 400% and see if it falls apart | Conflict | The guide says 200%. Flag it and ask. |
| 8 | Contrast, including hover states and images of text | Needs another tool | Guidance now; a contrast tool later |
| 9 | Forms: labels, and errors that say what went wrong | Check, exists, plus advice | A11Y-003, and A11Y-011 from the guide |
| 10 | Anything that moves or plays on its own | Check, new (also in the guide) | A11Y-009 |
| 11 | PDFs | Check, new (only here) | A11Y-012 |
| 12 | Fail if someone cannot complete the task; otherwise it is a note | Severity principle | The rule for choosing block or warn |
| 13 | A skipped heading or "read more" is a note, not a launch blocker | Severity evidence | Supports warn for A11Y-008 and A11Y-004 |
| 14 | A hundred small things add up to a big thing | Idea | The governor could escalate when one rule fires many times. Roadmap idea, not a rule. |
| 15 | Sign off with a plan: what is broken, who fixes it, by when, and chase the date | Exception process | Already how waivers work: a reason, an approver and an expiry |
| 16 | Supplier widgets: ask for a real accessibility statement | Check, new (only here), crosses areas | Candidate evidence rule. Needs an owner decision. |
| 17 | The standard is WCAG 2.2 level AA, "I think" | To verify | Confirm against the standard before it goes in a policy |
| 18 | Design system components solve half of it; a custom dropdown is almost always broken | Advice | Guidance to use the components. Measuring component use is a roadmap idea. |
| 19 | Run the scan yourself first; spend time with a real screen reader user | Process | A line in the developer guide |

The count: **6 of 19 claims point to checks** (two exist already, two are new but also appear in the written guide, two are new and only appear here). The other 13 are process, context, severity thinking, advice or things to verify. That is a lower share than the written guide, and expected: an interview is about how work is done, not just what is correct.

### What the interview adds that the guide did not

- **Two new checks.** A11Y-012 (a PDF added without structure tags) and a supplier-widget evidence rule. The guide never mentioned PDFs or suppliers.
- **A rule for severity.** Priya's test, "can someone complete the task?", is what separates a block from a warning. The guide gave no way to choose.
- **Feedback on rules we already have.** By her test, a missing page language (A11Y-002, currently set to block) does not stop anyone completing a task, so it looks too strict. This is the kind of thing the analysis is for. The practice decides, and for now the area is advice-only, so it shows as a warning either way.
- **A conflict to resolve.** The guide says 200%, the interview says 400%. Both appear in the accessibility standard (one is text resizing, the other is reflow), so the answer may be that both are right. The analysis flags it and asks. It does not pick.
- **Ideas that are not rules.** Risk tiers, escalating when a rule fires many times, and measuring use of the design system. These go to the roadmap, which is the right place for them.

### Decisions a person makes

| Item | Decision needed | Suggested |
| --- | --- | --- |
| A11Y-012 PDF without tags | Stage, severity | Pilot, warn, medium confidence, because tag detection is imperfect |
| Supplier widget evidence | Which area owns it: accessibility or enterprise alignment | Enterprise alignment, because it already records evidence (decision records) |
| A11Y-002 page language | Keep as block, or lower | Lower to warn, to match the task test |
| 200% versus 400% zoom | Which statement goes in the policy | Check the standard, then state both |

### The policy text that comes from the severity claim

This is not a rule. It is a short section the policy page gains, and every finding's severity then has a stated reason.

> ### How we decide what blocks
>
> A finding blocks a merge when it is likely to stop someone completing a task: a form control they cannot identify, a button they cannot name, a keyboard trap. A finding is a warning when it makes the product harder to use, but a person can still finish what they came to do: a skipped heading level, a vague link. Where the same warning appears many times, the accessibility practice may treat the pattern as more serious than any single instance.

### A rule written from the PDF claim

```yaml
- id: A11Y-012
  applies_from: pilot
  title: PDF added without structure tags
  severity: warn
  confidence: medium
  tags: [pdf, tags, structure, documents, wcag-1.3.1]
  summary: A PDF has no structure tags, so a screen reader reads it as a flat page of text, or not at all.
  guidance: >-
    A PDF that people must read needs structure tags: headings, lists, reading order and alt text for images.
    Export it from the source document with tagged output turned on, rather than printing to PDF.
  remediation: Re-export the PDF from its source with "create tagged PDF" enabled, or publish the content as a web page.
  exemplars:
    bad: |
      Guide.pdf, created with "Print to PDF" (flat, untagged)
    good: |
      Guide.pdf, exported from the source document with "Create tagged PDF" on
```

The supplier-widget rule waits for the ownership decision above. The detector for A11Y-012 is small: it opens each added PDF and looks for a structure tree. As before, none of this is in the demo repository yet.

## Who does what

| Step | Who | What they produce |
| --- | --- | --- |
| Write the guide | A practitioner, such as a design lead | Free writing, in their own voice. No format required. |
| Analyse it | An assistant drafts, a person from the practice reviews | The sorted list of claims, with new rules and gaps found |
| Decide | The domain team | Severity, stage and confidence for each new rule, with reasons |
| Write the policy entry | The domain team | The readable policy page |
| Turn it into a rule | The domain team, with an assistant | The YAML, and a small detector where one is possible |
| Approve | The governance team, through code owners | A merged pull request. Every pull request is now governed by it. |

The original guide is not thrown away. It stays the readable background, and each policy entry can link to it. When the guide changes, the analysis is repeated for the changed parts only.

### Caveats worth saying out loud

- The guide, the claims and the counts are invented for this example.
- The analysis is a first draft from an assistant. A person must confirm each sort, because a wrong "this is checkable" produces a noisy check.
- A guide can contradict itself or a standard. Analysis should flag those and ask the author, not choose.
- Some of the best material (principle 1 and the advice to test with real people) cannot be enforced in a pull request at all. It belongs in the policy page and in how teams work. This is why the pipeline helps people, but does not replace them.
