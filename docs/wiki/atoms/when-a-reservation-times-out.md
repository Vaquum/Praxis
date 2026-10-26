---
row: N5-01
baseline: 49aa659
created: 2026-10-25 11:00 UTC
modified: 2026-10-26 11:00 UTC
evidence:
  - claim: "Reservations are put on a heap under the moment each expires as they are made"
    source: "`nexus/core/capital_controller/capital_controller.py` 418"
  - claim: "The walk takes them off that heap while the expiry on top is at or before the moment it is given"
    source: "`nexus/core/capital_controller/capital_controller.py` 480-482"
  - claim: "A reservation released or spent leaves its heap entry behind, so what sits on top is the earliest entry rather than the earliest live hold"
    source: "`nexus/core/capital_controller/capital_controller.py` 512 and 553, against 482-486"
  - claim: "One already gone from the register is passed over"
    source: "`nexus/core/capital_controller/capital_controller.py` 482-486"
  - claim: "Each one it does find takes its whole total off the money the account has set aside, and asks the same of the strategy's own figure, which drops the strategy where what is left lands near nought"
    source: "`nexus/core/capital_controller/capital_controller.py` 487-491 into 1096-1115"
  - claim: "It is logged with how long it had been held"
    source: "`nexus/core/capital_controller/capital_controller.py` 492-500"
  - claim: "The walk runs at the head of a request for money, once the request has been read for shape"
    source: "`nexus/core/capital_controller/capital_controller.py` 327 after 300-324"
  - claim: "A send runs it too, on each road out it reaches past its own reading of what it was given"
    source: "`nexus/core/capital_controller/capital_controller.py` 578, or 556, or 568, each past 542-551"
  - claim: "A send finding its reservation gone walks first and then answers that it is not there"
    source: "`nexus/core/capital_controller/capital_controller.py` 553-560"
  - claim: "One finding it expired gives the total back itself before answering, rather than leaving it to the walk"
    source: "`nexus/core/capital_controller/capital_controller.py` 563-574"
---
# When a reservation times out

A reservation times out when the moment it was set to expire has been reached, and a walk gives its money back.

## The heap and the walk

Reservations go onto a heap under the moment each expires as they are made. A reservation released or spent leaves its entry behind, so what sits on top is the earliest entry rather than the earliest hold still standing. The walk takes them off while the expiry on top is at or before the moment it is handed, and stops at the first that is later. One already gone from the register — released or spent — is passed over.

Each one it does find takes its whole total off the money the account has set aside, and asks the same of the strategy's own figure — which drops that strategy from the figures where what is left lands near nought. Each is logged with how long it had been held.

## When it runs

At the head of a request for money, once the request has been read for shape. And on each road out of [a send](how-nexus-sets-money-aside.md) that it reaches past its own reading of what it was given.

## The send's own two roads

A send finding its reservation gone from the register walks anyway before answering that it is not there, so the figures are tidy even on the road that does nothing else.

A send finding its reservation still there and already past its moment gives the total back itself before answering, rather than leaving it to the walk — the reservation is on the heap, but the send is holding it and will not wait.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What a strategy's committed figure moves on](what-moves-a-strategys-committed-figure.md)

---

Created 2026-10-25 11:00 UTC · Last modified 2026-10-25 11:00 UTC
