---
row: P125-01
baseline: 49aa659
created: 2026-11-09 09:49 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "The listener is started only where a port was given and the loop stands"
    source: "`launcher.py` 3267 into 3268"
  - claim: "Its building is handed to the loop and waited on for ten seconds, with nothing wrapped around that wait"
    source: "`launcher.py` 3270-3273, then 3274"
  - claim: "One application serves the health road, the figures road, a status read, and four asks that change something"
    source: "`launcher.py` 3294, then 3295-3301"
  - claim: "It is bound to every address of the host at the port it was given, and handed back"
    source: "`launcher.py` 3302, then 3303, then 3304, then 3305, then 3306"
  - claim: "Stopping does nothing where no listener stands or the loop is missing"
    source: "`launcher.py` 3280 into 3281"
  - claim: "It hands the cleanup to the loop and waits ten seconds for it"
    source: "`launcher.py` 3283-3286, then 3288"
  - claim: "The listener is forgotten after that wait, whether the wait answered or raised"
    source: "`launcher.py` 3291, past 3287-3288"
---
# What the one listener serves

Every road into a running host is served by one listener, started on the host's own loop and bound to every address it has.

## The roads

The health road, the figures road, a status read, and four asks that change something — halting, resuming, cancelling everything and closing everything.

So whatever reaches the health road can reach the asks, and the only thing between an ask and the account is [the credentials each ask weighs](what-the-operators-two-sweeps-answer-with.md).

## Starting it

Only where a port was given and the loop stands. The building is handed to the loop and waited on for ten seconds — and nothing is wrapped around that wait, so a failure binding the port leaves the start altogether.

That is unlike [the host's background work](where-the-hosts-two-sets-of-background-work-differ.md), whose builds are waited on the same way and whose failures are reported and set aside. A port that cannot be bound stops the host; a sampler that cannot be built does not.

## Stopping it

Nothing happens where no listener stands or the loop is missing. Otherwise the cleanup is handed to the loop and waited ten seconds.

The listener is then forgotten after that wait, whether the wait answered or raised — again unlike the background work, which keeps what it could not stop. So a host whose listener would not shut down has no record of it to try again with.

## Related

- [Starting a host](starting-a-host.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)
- [Where the host's two sets of background work differ](where-the-hosts-two-sets-of-background-work-differ.md)
