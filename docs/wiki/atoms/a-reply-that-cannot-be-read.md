---
row: P1-10
baseline: 49aa659
created: 2026-09-23 20:04 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "On a send, a body that will not parse as JSON is wrapped as a transport failure"
    source: "`binance_adapter.py` 592 caught at 660-662, leaving at 680, wrapped at 1637-1643"
  - claim: "On an expiry cancel it stays a venue error, so the request is still reported"
    source: "caught at `execution_manager.py` 4433-4435"
  - claim: "On a run's child cancel it is caught and skipped, leaving the run awaiting its children"
    source: "`execution_manager.py` 6461-6468, the run held open at 6355-6356"
  - claim: "On a plain send, a venue error whose own body will not parse is recorded failed"
    source: "`binance_adapter.py` 1143-1145 raised at 1151-1152, recorded at `execution_manager.py` 4292-4295"
  - claim: "A flatten chases that same error and can adopt the order instead"
    source: "`execution_manager.py` 7791-7812"
  - claim: "An unrecognised status on a plain send is recorded failed"
    source: "`binance_adapter.py` 897, recorded at `execution_manager.py` 4296-4299"
  - claim: "On a flatten send the same status escapes, that sender catching venue errors alone"
    source: "`execution_manager.py` 7791-7813"
  - claim: "A field that will not convert escapes every handler on the send path"
    source: "`binance_adapter.py` 940, outside the handler at `execution_manager.py` 4296"
  - claim: "It is then only logged, with the intent already recorded"
    source: "logged at `execution_manager.py` 4012-4019, the intent written at 4264"
  - claim: "The same failure on a lookup from a plain send leaves it neither adopted nor written off"
    source: "raised in `binance_adapter.py` 1027-1039, escaping `execution_manager.py` 5533-5542"
  - claim: "The same lookup failure under a slice ends the run rejected instead"
    source: "escaping the arm at `execution_manager.py` 6008, finalized at 5866-5882"
  - claim: "On a slice it ends the whole run instead"
    source: "escaping the handler at `execution_manager.py` 6008, finalized at 5866-5882"
  - claim: "On a protective order it can stop the account"
    source: "escaping the handlers at `execution_manager.py` 4979-5015, reaching 4025"
  - claim: "On a cancel, a missing id or status leaves nothing reported"
    source: "raised at `binance_adapter.py` 1690 or 1691, escaping both arms at `execution_manager.py` 4431-4435"
  - claim: "So does a status present but unfamiliar on that same cancel"
    source: "`binance_adapter.py` 897 reached from 1691, escaping `execution_manager.py` 4431-4435"
  - claim: "The same failure cancelling a run's children stops the account, where the drain or the wind-up was the caller"
    source: "leaving `execution_manager.py` 6454-6458 to reach 4025-4026 from either 3960 or 8382"
  - claim: "A child cancel whose body will not parse is caught instead, leaving the run awaiting its children"
    source: "`execution_manager.py` 6461-6468, the run held open at 6355-6356"
  - claim: "From the sweep or an abort it is logged and the account carries on"
    source: "either `execution_manager.py` 7303-7308 or 3944-3951"
---
# A reply that cannot be read

When the venue answers in a way Praxis cannot make sense of, what happens depends on where the reading fails and who was reading. The endings below are the ones worth knowing; others exist.

## It may be treated as a transport failure

On a send, a body that fails to parse as JSON stops before the part that reads fields, and is wrapped as a transport failure and [chased up](when-a-send-is-unclear.md).

On a cancel it is a plain venue error instead, and [what that means](the-expiry-cancel.md) depends on which cancel it was.

## It may be recorded as a failed send

On a plain send, a venue error whose own body will not parse is recorded failed. So is a status Praxis does not recognise, and that one comes off a reply the venue sent to accept the order. A flatten differs on both: it chases the first and can adopt, and lets the second escape.

## It may go nowhere at all

A field that will not convert inside an otherwise readable body escapes every handler on the send path. [The worker](how-waiting-work-is-drained.md) logs it and the intent stays recorded, with nothing learning what became of the request.

Elsewhere the ending depends on the caller: on a lookup from a plain send it leaves the send neither adopted nor written off; under a slice it ends the run rejected; on a protective order it can stop the account.

## Related

- [When a send's outcome is unknown](when-a-send-is-unclear.md)
- [Order placement](how-an-order-is-placed.md)
