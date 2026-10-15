---
row: P4-58
baseline: 49aa659
created: 2026-10-14 16:00 UTC
modified: 2026-10-14 16:00 UTC
evidence:
  - claim: "A host shutting down refuses a new request, a cancellation and a change alike"
    source: "`trading.py` 1878-1880, 1904-1906 and 1913-1915"
  - claim: "Each then requires the named account to be ready"
    source: "`trading.py` 1881, 1907 and 1916"
  - claim: "Ready means the account's own start finished, which also requires the host to have been started"
    source: "`trading.py` 836-838 and 835 into 822-825"
  - claim: "Every one of them raises, so the caller is told by the raise rather than by a report"
    source: "`trading.py` 1879-1880, 824-825 and 837-838"
  - claim: "An account becomes ready only once its start has finished, so the checks below never see work from an account still starting"
    source: "`trading.py` 606-608 against `execution_manager.py` 3672"
---
# What the host refuses first

Three ways in — placing a request, cancelling one, changing one — share one guard, and it runs before anything reaches [the account's books](what-an-account-is.md) or [its worker](how-waiting-work-is-drained.md). A caller turned away here is told by a raise, and nothing is written down.

## Shutting down

A host that has begun [stopping](stopping-a-host.md) refuses all three. There is no queue to join: the answer comes back on the call.

## Not ready

Each way in then asks whether the named account is ready, and ready means one thing — that account's own [start](starting-a-host.md) ran to the end. An account still starting, one whose start failed, and a name the host has never had are all the same answer here.

Being ready also requires the host itself to have been started, since nothing is marked ready before that.

## What it means further in

An account is marked ready only after its start has finished. So work arriving through these three ways in cannot belong to an account that is still starting, and the checks further in that wait for a start to finish are there for work that arrives another way — [what a restart puts back](what-a-restart-puts-back.md), and the host's own [abandonments](where-an-abandonment-lands.md) as it stops.

## Related

- [Starting a host](starting-a-host.md)
- [Stopping a host](stopping-a-host.md)
- [Cancellation](how-a-trade-is-cancelled.md)

---

Created 2026-10-14 16:00 UTC · Last modified 2026-10-14 16:00 UTC
