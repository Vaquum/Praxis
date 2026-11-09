---
row: P183-01
baseline: 49aa659
created: 2026-11-16 12:00 UTC
modified: 2026-11-16 12:00 UTC
evidence:
  - claim: "A long's take-profit must sit above the entry's average price and its stop below it"
    source: "`execution_manager.py` 5124, then 5125"
  - claim: "A short's must sit the other way about"
    source: "`execution_manager.py` 5127"
  - claim: "The test is made against the price the entry actually filled at rather than anything named at intake"
    source: "`execution_manager.py` 5125, or 5127, the figure reaching either at 4947"
  - claim: "A pair failing it at first placement has the entry closed out as unprotected"
    source: "`execution_manager.py` 4947, then 4958-4961"
  - claim: "A pair failing it on a change answers nothing, which refuses the change"
    source: "`execution_manager.py` 9902, then 9905"
---
# The test both protective prices must pass

Before a protective pair goes up, both its prices are weighed against the price the entry actually filled at, and a pair on the wrong side of that price is never sent.

## The test

A long's take-profit must sit above the entry's average price, and its stop below it. A short's must sit the other way about.

The figure both are weighed against is what the entry filled at, not anything named when the trade was asked for. A pair that was sensible when it was asked for can fail here, because the entry filled somewhere else.

## What failing costs

At first placement, the entry is closed out as unprotected: there is a position and no cover for it, and that is treated as the failure it is rather than sending a pair that would fire at once.

On a change, the reading answers nothing, and the change is refused. The pair already resting stays where it is.

## Related

- [Protection](protection.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [When protection is lost](when-protection-is-lost.md)
