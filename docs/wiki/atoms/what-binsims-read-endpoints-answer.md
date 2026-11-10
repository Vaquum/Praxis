---
row: P89-01
baseline: 49aa659
created: 2026-11-09 07:07 UTC
modified: 2026-11-09 07:07 UTC
evidence:
  - claim: "The health endpoint throws the request away and answers one fixed word"
    source: "`server.py` 211, then 213"
  - claim: "The time endpoint throws it away too, and answers the clock as whole milliseconds"
    source: "`server.py` 218, then 220"
  - claim: "The exchange information weighs a symbol only where one was given, and answers a fixed payload otherwise"
    source: "`server.py` 229 into 231-235, then 237"
  - claim: "The book demands a symbol, refusing a missing one under a different code from an unknown one"
    source: "`server.py` 242 into 244 into 245-248, against 250 into 251-254"
  - claim: "The depth asked for goes through its own reading, and both sides are cut to it"
    source: "`server.py` 256, applied at 259 and 260"
  - claim: "Every price and quantity is answered as text, and the book's own last-update name goes with them"
    source: "`server.py` 259, and 260, then 262-266, the book itself taken at 257"
---
# What binsim's read endpoints answer

Four endpoints answer without asking who is calling, and they differ in how much of the request they read.

## The two that read nothing

The health endpoint throws the request away and answers one fixed word. The time endpoint throws it away too, and answers the clock as whole milliseconds.

## The one that reads a symbol if offered

The exchange information weighs a symbol only where one was given, and answers a fixed payload otherwise. So a caller naming the wrong symbol is refused, and one naming none at all is answered.

## The one that insists

The book demands a symbol. A missing one is refused under a different code from an unknown one — so a caller can tell a forgotten parameter from a venue that does not trade what they asked for.

## What the book gives back

The depth asked for goes through [its own reading](the-two-shapes-a-refusal-takes.md), and both sides of the book are cut to it. Every price and quantity is answered as text, and the book's own last-update name goes with them.

So a caller gets the figures as strings to parse for themselves, and a name they can use to tell one snapshot from the next.

## Related

- [What asking for a signature buys](what-asking-for-a-signature-buys.md)
- [The two shapes a refusal takes](the-two-shapes-a-refusal-takes.md)
