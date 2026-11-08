---
row: N52-02
baseline: 49aa659
created: 2026-11-12 09:30 UTC
modified: 2026-11-12 10:00 UTC
evidence:
  - claim: "A turn reads the symbols it must mark inside the guard it was given, which is the positions lock where it has one and nothing where it has none"
    source: "`nexus/core/mtm_loop.py` 213-215 into 218 and 224-227"
  - claim: "It fetches the marks outside that guard"
    source: "`nexus/core/mtm_loop.py` 230-231, the guard left at 227"
  - claim: "A mark that comes back missing ends the turn"
    source: "`nexus/core/mtm_loop.py` 232-237"
  - claim: "So does one that is not a finite figure of the exact kind"
    source: "`nexus/core/mtm_loop.py` 239-244"
  - claim: "The fetching stops at the first such mark, so the symbols after it are never asked for"
    source: "`nexus/core/mtm_loop.py` 230 into 237, or into 244"
  - claim: "The positions themselves are read inside the guard again afterwards"
    source: "`nexus/core/mtm_loop.py` 248 into 254"
  - claim: "A turn finding no positions zeroes every strategy's unrealized figure and the account's, where either stood at something"
    source: "`nexus/core/mtm_loop.py` 256-267"
---
# The mark that ends a turn

A turn of [the marking loop](the-lock-the-marking-insists-on.md) gives up entirely where one mark it needs cannot be had, rather than marking the positions it can price.

## What the turn guards

It enters the guard it was built with — the positions lock where it was given one, and nothing at all where it was not — reads the symbols its positions name, and leaves it.

It fetches the marks for those symbols outside the guard, and takes it again afterwards to read the positions themselves.

## The mark that ends it

A mark that comes back missing ends the turn. So does one that is not a finite figure of the exact kind.

The fetching stops at the first such mark, so the symbols after it in the order are never asked for at all.

Either way the turn stops with nothing written. Every position's unrealized figure is left standing at whatever it already held — which for a position opened since the last turn that finished is the nought it was created with.

## The turn with nothing to mark

Where the second reading finds no positions, every strategy's unrealized figure is set to nought, and the account's too — but only where one of them stood at something, so a turn over an account that was already flat writes nothing.

## Related

- [The lock the marking insists on](the-lock-the-marking-insists-on.md)
- [The two ways the signed figures change](the-two-ways-the-signed-figures-change.md)
- [Which of a host's changes reach the log](which-of-a-hosts-changes-reach-the-log.md)
