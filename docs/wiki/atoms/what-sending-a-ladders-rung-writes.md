---
row: P171-02
baseline: 49aa659
created: 2026-11-16 06:00 UTC
modified: 2026-11-16 06:00 UTC
evidence:
  - claim: "The rung's name carries its place in the grid and the generation it belongs to"
    source: "`execution_manager.py` 6185-6187"
  - claim: "One moment is taken before the send and carried into the intent"
    source: "`execution_manager.py` 6188, then 6190-6204, the moment set at 6192"
  - claim: "The intent is recorded and applied before the venue is called"
    source: "`execution_manager.py` 6205, then 6206, then 6208"
  - claim: "A second moment is taken after the venue answers, and the send recorded with that one"
    source: "`execution_manager.py` 6229, then 6242-6247, the moment set at 6244, then 6248, then 6249"
  - claim: "A rescue that found nothing, a venue failure, and params the adapter refused each record the failure and answer nothing"
    source: "`execution_manager.py` 6227, or 6230, then 6231-6233, then 6234, or 6235, then 6236-6239, then 6240"
  - claim: "Each fill given as the rung was taken is recorded, and only one the record answered with a place carried into the figures"
    source: "`execution_manager.py` 6268, then 6269 into 6270"
  - claim: "The rung's name is the answer where the send stands"
    source: "`execution_manager.py` 6281"
---
# What sending a ladder's rung writes

Sending one rung of a ladder writes the intent before the venue is called and the send afterwards, each stamped with its own moment, so the pair brackets the venue call in time.

## The name

The rung's name carries its place in the grid and the generation it belongs to, so a rung of a new grid never wears the name a cancelled rung of the same place wore.

## Before and after

One moment is taken before the send and carried into the intent, which is recorded and applied before the venue is called.

A second is taken after the venue answers, and the send recorded with that one. Reading the two records together gives the span the call took.

## The three ways it answers nothing

A rescue that found nothing, a venue failure, and params the adapter refused. Each records the failure and answers nothing, and the caller reads that nothing as a rung that is not resting.

## The fills that came with it

Each fill given as the rung was taken is recorded, and only one the record answered with a place is carried into the figures. The rung's name is the answer where the send stands.

## Related

- [How a ladder's rungs are found again](how-a-ladders-rungs-are-found-again.md)
- [How a ladder's change moves from one phase to the next](how-a-ladders-change-moves-from-one-phase-to-the-next.md)
- [What is written down when a flatten goes out](what-is-written-down-when-a-flatten-goes-out.md)
