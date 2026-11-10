---
row: P120-01
baseline: 49aa659
created: 2026-11-09 09:27 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "A position of no size is put in under the command's own name on either road an entry takes, before the order goes out"
    source: "`launcher.py` 2137 into 2138-2145, or 4314, then 4315, then 4316, both reaching 1446-1452"
  - claim: "The price it carries is the action's own, or a provider's where the action gives none"
    source: "`launcher.py` 1431, then 1432 into 1433"
  - claim: "Where neither gives one, an entry sized by amount is reported and nothing is put in, or an entry sized in money takes a price of one"
    source: "`launcher.py` 1435, then 1437 into 1442, or 1444"
  - claim: "Its side is the action's own, or a buy where the action names none, and its symbol is the one standing default whatever the action named"
    source: "`launcher.py` 1450, and 1449"
  - claim: "The write is made only where nothing stands under that name already, under the lock where one was given and without it where none was"
    source: "`launcher.py` 1455 into 1456-1457, or 1459"
  - claim: "The first fill sets the position's price to the fill's own where the size standing is nought, so the price put in is discarded"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 473, then 479, then 480-482"
  - claim: "A fill for an entry the records hold no position for raises instead"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 467, then 469 into 470-471"
---
# The empty position an entry is given first

An entry has a position of no size written for it before its order goes out, under the command's own name, so the first fill has something to grow.

## Why it is there at all

A fill for an entry the records hold no position for raises. The empty position is what keeps that from happening to every entry, since nothing on the far side creates one when a fill arrives.

## The price it is given

The action's own, or a provider's where the action gives none. Where neither gives one, what happens turns on how the entry was sized: one sized by amount is reported and nothing is put in at all, and one sized in money takes a price of one.

That price is discarded by the first fill, which sets the position's price to the fill's own wherever the size standing is nought. So the figure put in has to be a positive one and does not have to be right.

## What else it carries

Its side is the action's own, or a buy where the action names none. Its symbol is the one standing default, whatever the action named.

## Written once

The write is made only where nothing stands under that name already, so a second call for the same command changes nothing. It is made under the positions lock where one was given, and without it where none was.

## Related

- [What an entry's sum is worked out from](what-an-entrys-sum-is-worked-out-from.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)
- [Whether a fill closes a position](whether-a-fill-closes-a-position.md)
