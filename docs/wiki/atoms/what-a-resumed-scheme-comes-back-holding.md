---
row: P135-02
baseline: 49aa659
created: 2026-11-09 10:37 UTC
modified: 2026-11-09 10:37 UTC
evidence:
  - claim: "The command is rebuilt as a market order carrying the rebuilt parameters and a replay timeout"
    source: "`execution_manager.py` 1942-1947"
  - claim: "Its live children are the replayed active names whose order is there and whose status is not a terminal one"
    source: "`execution_manager.py` 1950, then 1951, then 1952, then 1953, then 1954 into 1955"
  - claim: "Its deadline is the start's moment plus its timeout where that stands above nought, and nothing where it does not"
    source: "`execution_manager.py` 1957-1961"
  - claim: "A replan replaces the slice plan outright, and the interval comes from the replan where there is one"
    source: "`execution_manager.py` 1963, then 1965 into 1969, then 1971-1978"
  - claim: "The cursor is the replayed one, or nought where no state was recorded"
    source: "`execution_manager.py` 1979"
  - claim: "The timer is the state's where there is no replan, the replan's where there is no state or no place for either, and otherwise whichever of the two stands later in the history"
    source: "`execution_manager.py` 1981-1985, into 2050 into 2051, or 2053 into 2054, or 2056 into 2057, or 2059"
  - claim: "The hold follows one precedence: draining, then protection, then a failed slice, then open"
    source: "`execution_manager.py` 1987-1990, into 282 into 283, or 285 into 286, or 288 into 289, or 291"
  - claim: "The terminal answer it is to end with is carried over, and a draining scheme with live children is marked as still owing its cancels"
    source: "`execution_manager.py` 1993, then 1994-1995"
  - claim: "A scheme open, with no terminal answer owing, with slices left, with no timer and with no live children is given the present moment as its timer"
    source: "`execution_manager.py` 1998-2004 into 2005"
  - claim: "It is then registered, its command installed, the account noted as its owner and the trade's name recorded"
    source: "`execution_manager.py` 2007, then 2008, then 2009, then 2010"
---
# What a resumed scheme comes back holding

A resumed scheme is rebuilt field by field from what the history recorded, and two of those fields are worked out rather than read.

## Rebuilt from the record

The command comes back as a market order carrying the rebuilt parameters and a replay timeout. The cursor is the replayed one, or nought where no state was recorded. The deadline is the start's moment plus its timeout, where that stands above nought.

Its live children are the replayed active names, narrowed to those whose order is still there with a status that is not terminal — so a child that finished while the host was down is not counted as live.

## What a replan overrides

A replan replaces the slice plan outright, and the interval comes from the replan where there is one. The plan the start recorded is then never used.

## The two that are worked out

The timer is the state's where there is no replan, the replan's where there is no state or no place recorded for either, and otherwise whichever of the two stands later in the history.

The hold follows one precedence: draining, then protection, then a failed slice, then open. So a resumed scheme cannot hold anything looser than the running one would have held.

## The nudge

A scheme that is open, owes no terminal answer, has slices left, has no timer and has no live children is given the present moment as its timer. Without it such a scheme would sit with nothing to wake it.

A draining scheme with live children is instead marked as still owing its cancels.

## Related

- [What stops a scheme being resumed](what-stops-a-scheme-being-resumed.md)
- [What a restart puts back](what-a-restart-puts-back.md)
- [A change waiting out a hold](a-change-waiting-out-a-hold.md)
