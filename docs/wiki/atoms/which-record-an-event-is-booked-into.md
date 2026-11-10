---
row: P162-01
baseline: 49aa659
created: 2026-11-09 12:31 UTC
modified: 2026-11-09 12:31 UTC
evidence:
  - claim: "A registration or a movement of funds is booked into the money record and goes no further"
    source: "`execution_manager.py` 2072, then 2073, then 2075"
  - claim: "An alert of a mismatch is booked nowhere and advances no record"
    source: "`execution_manager.py` 2077, then 2079"
  - claim: "Every other event advances the trading record"
    source: "`execution_manager.py` 2081"
  - claim: "A fill is also carried into the admitted totals kept for its command"
    source: "`execution_manager.py` 2083, then 2084"
  - claim: "A fill and a closed trade are each booked into the money record as well"
    source: "`execution_manager.py` 2086, then 2087"
  - claim: "A failure booking into the money record is swallowed where it happens"
    source: "`execution_manager.py` 2091, then 2093"
---
# Which record an event is booked into

Praxis keeps two running pictures of an account — the trading record of its orders and the money record of its costs — and every event is routed to one, both, or neither.

## The money record alone

A registration, and a movement of funds in or out, are booked into the money record and go no further. The trading record never hears of them.

## Neither record

An alert that the venue's figures and Praxis's disagree is booked nowhere and advances no record at all. It is a thing to be told about rather than a thing that happened to the account.

## The trading record, and sometimes more

Every other event advances the trading record. A fill does that and two further things: it is carried into the admitted totals kept for its command, and it is booked into the money record. A closed trade is booked into the money record too.

## What a failure there costs

A failure booking into the money record is swallowed where it happens. So the money record can fall behind the trading record while the orders carry on, and nothing on the trading side is stopped or told.

That is the price of the order the writes fall in on a fill's road: the trading record first, the command's totals next, and the money record last, by a call whose failure reaches no further than a log line.

## Related

- [What a fill changes](what-a-fill-changes.md)
- [What an account is](what-an-account-is.md)
- [The part of a fill a command counts](the-part-of-a-fill-a-command-counts.md)
