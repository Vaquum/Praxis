---
row: P4-23
baseline: 49aa659
created: 2026-10-01 18:04 UTC
modified: 2026-10-11 19:38 UTC
evidence:
  - claim: "A cancel the venue refuses in the second pass is logged as a warning and the next order taken up"
    source: "`trading.py` 735-742"
  - claim: "Trading then waits for the open orders and the commands in flight to clear, up to a time it is configured with"
    source: "`trading.py` 744-762"
  - claim: "Running out of that time is logged as a warning and the stopping goes on"
    source: "`trading.py` 763-764"
  - claim: "Each feed is closed, and an ordinary failure closing one is logged and the next taken up"
    source: "`trading.py` 766-773"
  - claim: "The venue is closed, and a failure closing it is logged and passed over"
    source: "`trading.py` 775-780"
  - claim: "Every account is unregistered, and the first ordinary failure there is raised once the rest have been tried"
    source: "`trading.py` 782-796"
  - claim: "That raise leaves trading marked as started"
    source: "`trading.py` 795-798"
  - claim: "It also carries out of the host, which closes neither the record's connection nor the loop"
    source: "`trading.py` 796 into `launcher.py` 3918-3919, ahead of 3921-3938"
---
# What stopping leaves undone

Stopping a [host](stopping-a-host.md) carries on through three things going wrong: a cancel the venue refuses, a drain that runs out of time, and a close that fails. Each is logged and the next step taken up, so stopping can finish with things still open.

## Passed over

A cancel the venue refuses in the second pass is logged as a warning, and the next order is taken up. Nothing comes back to it.

Trading then waits for the open orders and the commands in flight to clear, up to a time it is configured with. Running out of that time is logged as a warning and the stopping goes on regardless, so orders can still be resting when the host finishes.

Each feed is closed next, then the venue. A failure in either is logged and the one after is taken up.

## The one that is not

Every [account](what-an-account-is.md) is then unregistered. A failure there is kept, the remaining accounts are tried, and the first failure kept is raised at the end.

That raise is the exception to those three. Trading is left marked as started, and the raise carries out into the host — which goes on to close neither its connection to [the record](the-event-spine.md) nor its loop.

## Related

- [Stopping a host](stopping-a-host.md)
- [What becomes of work still open](what-becomes-of-work-still-open.md)
