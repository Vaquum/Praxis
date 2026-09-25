# Article template

## What the reader sees

- **Title** — a noun phrase naming the subject. Not a question, not a sentence.
- **A lead paragraph, directly under the title**, whose first sentence defines the subject. No heading before it, and no throat-clearing: not "Three names are in play", not "This is about", not "X happens in two stages" before saying what X is.
- **Sections** named for what they contain.
- **Links in the prose**, on the terms themselves, wherever another article owns the term. A reader who meets a word they do not know clicks it where they meet it.

The check blocks on a missing lead, on a lead that opens with "This", and on `## What it is`, `## Overview` or `## Introduction`, which are prompts rather than section names.

It also blocks on a term another article owns appearing unlinked — but only for terms whose string cannot mean anything else, such as `priority line` or `order book`. Ordinary words like *fill*, *run* and *held* mean one thing in "counted as filled" and another in "too thin to fill", and no string match separates them. Those are asked of the reviewer instead, as part of every review: **which mentions of an owned term are the concept and should link, and which are ordinary usage that should not.**

## Say what a thing is

Nobody arrives asking what a thing is not. "A name, not an object" and "Cancelling is a request, not an act" answer a question the reader never had, and spend the word budget denying a confusion the article itself introduced. Write the positive form: "A name supplied from outside." "Cancelling asks Praxis to stop an order."

The check blocks on the `X, not a Y` construction and on double negatives such as "does not mean nothing happened", which make the reader work out a fact by cancelling two terms.

A negation is right when the absence is the finding: that no fill count is consulted on a path, that a book is never checked for price order, that the changes put back on the line are not refused. Those say what happens. Say it directly rather than denying its opposite.

**300 words of prose is a hard cap and the check blocks on it.** Navigation links do not count. An article needing more room is not one article: the parent keeps the shape of the thing, and each part that needs explaining becomes its own article, linked from it.

## What the reader does not see

Evidence is apparatus. It is how the article is checked, not part of what it says, and a reader who does not yet know what a trade is has no use for a line number in a ten-thousand-line file. So it lives in the metadata block at the top of the file, never in the body:

```
---
row: P1-02
baseline: 49aa659
created: 2026-09-20 15:52 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "A full queue is refused"
    source: "`execution_manager.py` 3497-3511"
---
```

The row ID, the source revision and both timestamps live there too. The check blocks on an `## Evidence` heading or a claim/source table appearing in the body, and on a file with no metadata block at all.

## Add only when it earns its place

- How it works, when the order of things explains something the description has not.
- What varies, when a reader would otherwise be surprised.
- Where it goes wrong — only where it does. Do not manufacture a failure section.

Omit empty headings. A prompt is not a heading you must fill.

## Read the body, not the docstring

An article is written from what the code does. A docstring is a claim about the code and can be stale — one described a change as lost on restart when the behaviour had been fixed and the debt closed, and an article repeating it told readers to re-apply a change that had survived.

Cite a docstring only as a statement of intent, and say so. Where a docstring and the body disagree, the body wins and the article says the docstring is stale.

The same applies to a log message. A line reading `_log.warning('placing the replacement…')` is a claim about what happens next, not the thing happening. Cite the call that does the work. Citing a log line is right only when the claim is about the log line itself — that a particular message exists, or that two cases share one.

## Cite a body, not a shape

A citation must land on code that does the thing. The check blocks three ways of failing that, each one first caught by hand after it had already reached a finished article:

- **A signature only.** A range covering `def place_order(...)` and its parameters proves nothing about behaviour. Cite where the work happens.
- **A docstring, or a log line.** Covered above.
- **Two mutually exclusive branches, cited as a sequence.** An early `return` and the code after it, or both halves of an `if`/`else`, cannot both run for one request. Citing them together reads as "first this, then that" and is wrong. Where the point genuinely is that they are alternatives, say so in the row — "need not", "instead", "rather than", "unless" — and the check allows it.

A cited file that cannot be found is a failure too, not a skip.

## Two tests, both applied at review

- **Code-label removal** — strip implementation names; the explanation must still say what happens and why.
- **Reader test** — someone who meets the subject for the first time can follow the article without reading the code.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-09-25 18:14 UTC
