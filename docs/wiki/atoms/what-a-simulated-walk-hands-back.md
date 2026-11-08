---
row: P31-01
baseline: 49aa659
created: 2026-11-11 13:30 UTC
modified: 2026-11-11 14:00 UTC
evidence:
  - claim: "Each walk refuses a figure that is not finite and one at or below nought"
    source: "`praxis/binsim/book.py` 144-148, or 214-218"
  - claim: "A walk whose side of the book is empty raises a different kind of error, naming the book as never filled"
    source: "`praxis/binsim/book.py` 152-153, or 220-221"
  - claim: "The walk for a spend hands back the spend left over as well as the fills"
    source: "`praxis/binsim/book.py` 241"
  - claim: "That figure is the spend still unspent where the book ran out"
    source: "`praxis/binsim/book.py` 226-227 ending the walk with it unchanged"
  - claim: "Where a partial level was taken it is set to nought instead, so the sliver the rounding down left unspent is not reported"
    source: "`praxis/binsim/book.py` 237-239 into 241"
  - claim: "The two sides are handed out as copies"
    source: "`praxis/binsim/book.py` 48, or 53, against the lists kept at 115-116"
---
# What a simulated walk refuses

[The walks over binsim's book](binsims-book.md) each refuse the figure they are given before they look at a single level, and each answers an empty book differently again.

## The figure

Not finite, or at or below nought: refused. Both walks make that pair of checks, the one for a size and the one for a spend alike.

## The empty book

A walk whose side of the book holds nothing raises a different kind of error, one that names the book as never having been filled rather than the request as wrong.

So a caller can tell a bad request from a book that was never handed anything.

## What the spend walk reports

The walk for a spend hands back the spend left over beside the fills. That figure is what is still unspent where the book ran out before the spend did.

Where the walk stopped instead at a level it could only take part of, the figure is set to nought — so the sliver that the rounding down did not spend goes unreported. A spend of one against a price of three reports nothing left, having spent all but a ten-thousandth of a billionth of a billionth.

## What the sides hand out

The bids and the asks come out as copies. A caller that changes what it was given changes nothing the book holds.

## Related

- [Binsim's book](binsims-book.md)
- [What a binsim snapshot is turned away for](what-a-binsim-snapshot-is-turned-away-for.md)
- [Binsim](binsim.md)
