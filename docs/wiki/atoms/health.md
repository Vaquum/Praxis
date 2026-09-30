---
row: P3-15
baseline: 49aa659
created: 2026-09-30 09:14 UTC
modified: 2026-09-30 16:45 UTC
evidence:
  - claim: "One result is recorded per request, across its retries, with the waiting counted in the time"
    source: "`binance_adapter.py` 578-604"
  - claim: "Recording is skipped for a missing order against the simulator"
    source: "`binance_adapter.py` 632-634"
  - claim: "An order the venue rejects is recorded as the venue having answered"
    source: "`binance_adapter.py` 635-656"
  - claim: "Asking the time is not recorded at all"
    source: "`binance_adapter.py` 2353-2372"
  - claim: "A fixed number of the most recent are kept, the oldest falling out"
    source: "`health_tracker.py` 75-76 with the count at 21"
  - claim: "A window size that is not a whole number above zero is refused"
    source: "`health_tracker.py` 39-42"
  - claim: "A success resets the run of failures; a failure lengthens it"
    source: "either `health_tracker.py` 78 or 80"
  - claim: "The slow-end figure and the failed share are worked out when asked for"
    source: "`health_tracker.py` 123-129 and 136-140, assembled at 110-115"
  - claim: "The limit figure counts the share of the allowance already used"
    source: "`binance_adapter.py` 2330, supplied at 2394-2403 and passed through at `health_tracker.py` 114"
  - claim: "A replay's venue returns a report with every figure at zero"
    source: "`replay_venue_adapter.py` 427 with the defaults at `health_snapshot.py` 33-37"
  - claim: "The decision side reads an all-zero report as an account in good health"
    source: "Nexus `health_evaluator.py` 165-184"
  - claim: "The report is handed to the decision side, which can restrict or halt an account on it"
    source: "`launcher.py` 513-528 into Nexus `health_loop.py` 157-177 and `health_evaluator.py` 165-184"
---
# Health

What Praxis records about how the venue is answering is its **health**: how long requests took, and whether they worked.

It is kept per [account](what-an-account-is.md), since accounts are answered separately and one can be struggling while another is not.

## What counts as a request

One result is recorded per request rather than per attempt, so a call that retried counts once — with the waiting included in how long it took.

Not everything is recorded. Asking the venue the time is not, and a missing order against [the simulated venue](binsim.md) is skipped. An order the venue **rejects** is recorded as a success, because the venue answered: this measures whether the venue replied, leaving what the order did to be judged elsewhere.

[A replay's venue](the-replay-venue.md) measures none of this. It hands back a report with every figure at zero — which the decision side reads as an account in good health, rather than as an account it knows nothing about.

## What is reported

A fixed number of the most recent results are kept and the oldest fall out. From those, two figures are worked out when asked for: a slow-end measure of how long requests are taking, and the share that failed.

Beside them sits the run of failures in a row — a success resets it, a failure lengthens it — and two figures supplied from outside: how much of the venue's allowance has been **used**, and how far the clock has drifted.

## Who reads it

The report goes to the decision side, which can restrict an account to closing out, or halt it entirely, on what the report says.

So health is not only a picture. It is read, and it can stop work being accepted.

## Related

- [What a venue is](what-a-venue-is.md)
- [When an update fails](when-an-update-fails.md)
