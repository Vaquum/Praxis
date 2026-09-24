---
row: P1-10
baseline: 49aa659
created: 2026-09-23 20:04 UTC
modified: 2026-09-24 08:02 UTC
evidence:
  - claim: "A body that will not parse as JSON is wrapped as a transport failure"
    source: "`binance_adapter.py` 592 caught at 660-662, leaving at 680, wrapped at 1637-1643"
  - claim: "A venue error whose own body will not parse is recorded failed"
    source: "`binance_adapter.py` 1143-1145 raised at 1151-1152, recorded at `execution_manager.py` 4292-4295"
  - claim: "An unrecognised status on a single order is recorded failed"
    source: "`binance_adapter.py` 897, recorded at `execution_manager.py` 4296-4299"
  - claim: "A field that will not convert escapes every handler on the send path"
    source: "`binance_adapter.py` 940, outside the handler at `execution_manager.py` 4296"
  - claim: "It is then only logged, with the intent already recorded"
    source: "logged at `execution_manager.py` 4012-4019, the intent written at 4264"
  - claim: "The same failure on a lookup leaves the send neither adopted nor written off"
    source: "raised in `binance_adapter.py` 1027-1039, escaping `execution_manager.py` 5533-5542"
  - claim: "On a slice it ends the whole run instead"
    source: "escaping the handler at `execution_manager.py` 6008, finalized at 5866-5882"
  - claim: "On a protective order it can stop the account"
    source: "escaping the handlers at `execution_manager.py` 4979-5015, reaching 4025"
---
# A reply that cannot be read

When the venue answers in a way Praxis cannot make sense of, what happens next depends on where the reading fails and which path the send took. The endings below are the ones worth knowing; they are not a complete list.

## It may be treated as a transport failure

A body that fails to parse as JSON stops before the part that reads fields. It is wrapped as a transport failure, and so it is [chased up](when-a-send-is-unclear.md) like any other.

## It may be recorded as a failed send

A venue error whose own body will not parse is recorded failed. So is a status Praxis does not recognise on a single order — even though the venue has accepted it by then.

## It may go nowhere at all

A field that will not convert inside an otherwise readable body escapes every handler on the send path. [The worker](how-waiting-work-is-drained.md) logs it, the intent stays recorded, and nothing downstream learns what became of the request.

The same unreadability elsewhere lands differently again: on a lookup it leaves the send neither adopted nor written off; on a slice it ends the whole run; on a protective order it can stop the account outright.

## Related

- [When a send's outcome is unknown](when-a-send-is-unclear.md)
- [Order placement](how-an-order-is-placed.md)
