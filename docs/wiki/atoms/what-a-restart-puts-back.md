---
row: P4-46
baseline: 49aa659
created: 2026-10-13 11:25 UTC
modified: 2026-10-13 11:25 UTC
evidence:
  - claim: "A ladder comes back holding the rungs whose order has not ended, with the count already posted"
    source: "`execution_manager.py` 1359-1361 into 1371-1376"
  - claim: "It comes back with no timer, so the pass only finishes it once every rung settles"
    source: "`execution_manager.py` 1378"
  - claim: "One whose change was in flight comes back with that change's stage set"
    source: "`execution_manager.py` 1453 and 1464"
  - claim: "A run fed out over time comes back at its recorded cursor"
    source: "`execution_manager.py` 1979"
  - claim: "A recorded replan's amounts and gap replace the original ones"
    source: "`execution_manager.py` 1963-1969 and 1975-1977"
  - claim: "The timer is taken from whichever of the progress mark and the replan was written later"
    source: "`execution_manager.py` 1981-1985 into 2050-2057"
  - claim: "A pair confirmed resting comes back active rather than being put up again"
    source: "`execution_manager.py` 1667-1674, the pair's mark read at 1622"
  - claim: "One whose change never settled comes back unknown, for the watch to ask about"
    source: "`execution_manager.py` 1831-1835, from the unsettled change at 1822"
  - claim: "A scheme's hold is rebuilt under the precedence the running one keeps, a protection freeze winning whatever the order and no thaw lifting it"
    source: "`execution_manager.py` 282-289, called at 1987"
---
# What a restart puts back

A restart replays [the record](the-event-spine.md) and rebuilds the live work it finds, each kind at the point it had reached. Nothing already standing at the venue is sent again.

## Orders at several prices

[A ladder](orders-at-several-prices.md) rests all its rungs at once, so a resumed one has nothing left to plan or place. It comes back holding the rungs whose order has not ended, with the count already posted, and no timer at all — so the account's pass only finishes it once every rung settles.

One whose change was in flight at the stop comes back with that change's stage set, for the same driver to carry on from.

## Work fed out over time

[A run fed out over time](work-fed-out-over-time.md) comes back at its recorded cursor. Where a change to its schedule was recorded, that plan's amounts and gap replace the original ones, and the timer is taken from whichever of the progress mark and the change was written later.

## Protection

[A protective pair](protection.md) confirmed resting comes back active, rather than being put up a second time. One whose change never settled comes back unknown instead, so [the watch](when-protection-is-lost.md) can ask the venue what became of it.

## The hold it comes back under

A scheme's hold is rebuilt from the freeze marks replayed, under the precedence the running one keeps: winding up outranks a protection freeze, which outranks a failed-slice freeze. A protection freeze wins whatever order the marks arrived in, and no thaw lifts it — so a restart cannot resume a scheme running where the live one would have held it.

## Related

- [The event spine](the-event-spine.md)
- [Work fed out over time](work-fed-out-over-time.md)
- [Orders at several prices](orders-at-several-prices.md)

---

Created 2026-10-13 11:25 UTC · Last modified 2026-10-13 11:25 UTC
