---
row: P120-02
baseline: 49aa659
created: 2026-11-09 09:27 UTC
modified: 2026-11-09 09:27 UTC
evidence:
  - claim: "The record is built from a request fetched through whatever the caller handed in, and nothing is built where that answers with nothing"
    source: "`launcher.py` 1499, then 1500 into 1501"
  - claim: "A request carrying no side is reported and nothing is built"
    source: "`launcher.py` 1503 into 1508"
  - claim: "Whether it counts as an entry is settled from the action's kind rather than from the request"
    source: "`launcher.py` 1510"
  - claim: "A request carrying no size stops the building only where the action was not an entry"
    source: "`launcher.py` 1512 into 1517"
  - claim: "The trade name is the forced one where one was given, and the request's own otherwise"
    source: "`launcher.py` 1519"
  - claim: "The building is wrapped, and a refusal from the record's own demands is reported and nothing built"
    source: "`launcher.py` 1521-1522 into 1533, then 1538"
  - claim: "One caller hands over the request the checks already used, where the other hands over a way to build one again"
    source: "`launcher.py` 2183, against 4329"
  - claim: "Which of the two runs is settled by whether the road out carries a command name of Praxis's own"
    source: "`launcher.py` 4239-4255, against 4270 into 4271"
  - claim: "The caller that hands over the ready request has just raised the position's pending amount, and whether the whole remainder was meant is worked out against that amount"
    source: "`launcher.py` 2161-2164 before 2179-2184, with 1307, then 1308"
---
# What rebuilding an order's record is given

An order's record is built from the request the checks read, and the two callers that build one hand over that request in two different ways.

## What the building refuses

Nothing is built where the request cannot be had at all. A request carrying no side is reported and nothing is built. A request carrying no size stops the building only where the action was not an entry, since an entry's size may legitimately be absent.

Whether the record counts as an entry is settled from the action's kind rather than from the request. The [trade name](what-a-trade-is.md) is the forced one where one was given, and the request's own otherwise.

The building itself is wrapped: a refusal from the record's own demands is reported and nothing is built, so a malformed record is never registered rather than registered and worked around.

## The two callers

One hands over the request the checks already used. The other hands over a way to build one again. Which of the two runs is settled by whether the road out carries a command name of Praxis's own.

## Why one of them cannot rebuild

The caller that hands over the ready request has just raised [the position's pending amount](what-a-pending-sale-is.md) — and whether the whole remainder was meant is worked out against that amount.

So a request built again at that point would read the raised figure, find less remaining than the action asked for, and record a full close as a part one. Handing over the request made before the raise is what keeps the two in step.

## Related

- [What a pending sale is](what-a-pending-sale-is.md)
- [What Praxis works out for an exit](what-praxis-works-out-for-an-exit.md)
- [What a pending sale does to the dust](what-a-pending-sale-does-to-the-dust.md)
