---
row: P2-25
baseline: 49aa659
created: 2026-09-25 08:00 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "The order is marked expired before the venue is asked anything"
    source: "`execution_manager.py` 4415-4417"
  - claim: "A linked pair is cancelled by its own call, any other order by the single-order one"
    source: "either `execution_manager.py` 4419-4424 or 4426-4430"
  - claim: "A venue with no such order leaves the mark standing, so the expiry is recorded"
    source: "`execution_manager.py` 4431-4432 leaving the flag set at 4417, appended at 4436-4444"
  - claim: "Any other venue failure clears it, so no expiry is recorded against the order"
    source: "`execution_manager.py` 4433-4435, skipping 4436-4444"
  - claim: "The request is reported expired on both of those"
    source: "`execution_manager.py` 4446-4448"
  - claim: "A cancel reply lacking a field, or carrying an unfamiliar status, reaches neither"
    source: "raised at `binance_adapter.py` 1690, 1691 or 897, escaping both arms at `execution_manager.py` 4431-4435, logged at 4012-4019"
  - claim: "For a linked pair only a missing list id does that, the status being supplied"
    source: "raised at `binance_adapter.py` 1735, supplied instead at 1736"
  - claim: "A body that will not parse is a venue error, so that one is reported"
    source: "wrapped at `binance_adapter.py` 660-662, or raised at 1143-1152, caught at `execution_manager.py` 4433-4435"
  - claim: "On a run's child cancel the same body is caught and skipped, leaving the run awaiting its children"
    source: "`execution_manager.py` 6461-6468, the run held open at 6355-6356"
  - claim: "A field failure there stops the account only where the drain or a wind-up asked"
    source: "reaching `execution_manager.py` 4025-4026 from either 3960 or 8382, logged instead at either 3944-3951 or 7303-7308"
---
# The expiry cancel

When an order is found past its [deadline](deadlines.md), Praxis marks it expired, asks the [venue](what-a-venue-is.md) to cancel it, and reports. The mark comes first, so what the venue says next only decides how much is written down.

## What the venue's answer changes

A venue that reports no such order leaves the mark standing, and the expiry is recorded against the order itself.

Any other venue failure clears the mark instead. Nothing is recorded against the order, and the failure is carried in the reason.

Either way the request is reported expired. So being told a request expired does not say whether the order at the venue was actually stopped.

## When nothing is reported at all

A cancel reply that [lacks a field, or carries an unfamiliar status](a-reply-that-cannot-be-read.md), reaches neither of those endings. It leaves the whole attempt before any report is built, and only a log is left behind.

For a linked pair that is narrower: its status is supplied rather than read, so only a missing list id does it.

A body that will not parse at all is different again — that counts as a venue failure, so the request is still reported expired.

## The same reply on other cancels

A run's children are cancelled elsewhere, and there the same unreadable body is caught and skipped, leaving the run waiting on children. A failure reading a *field* there stops the account, but only where the drain or a wind-up asked; an abort or the repair sweep logs it and carries on.

## Related

- [Deadlines](deadlines.md)
- [Order placement](how-an-order-is-placed.md)
