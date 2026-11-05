---
row: N9-05
baseline: 49aa659
created: 2026-11-03 15:40 UTC
modified: 2026-11-05 11:10 UTC
evidence:
  - claim: "The call is made inside a catch, which turns whatever the store raised into a startup failure naming the step it failed at"
    source: "`nexus/startup/sequencer.py` 481 under the catch at 482-483"
  - claim: "The start sequence holds no handler anywhere between the step that raises and its own return"
    source: "`nexus/startup/sequencer.py` 177 inside the span at 164-189, which carries none"
  - claim: "The build above it holds none either, between the call it makes on the sequence and the caller it returns to"
    source: "`praxis/launcher.py` 4085 through 3992"
  - claim: "On a replay the failure reaches no catch inside the run, only the run's closing step, which sets the stop flag and runs the host's stopping before it leaves"
    source: "`praxis/replay/run_replay.py` 150 inside the try at 146, the finally at 174 setting the flag at 175 and stopping at 176"
---
# What a failed checkpoint costs a start

A start that cannot write [the checkpoint](what-a-checkpoint-holds.md) it asked for gives up the whole start, and what becomes of the host from there is the host's own business.

## Where the failure is caught

At the call. The catch there turns whatever the store raised into a startup failure naming the step it failed at.

Nothing on the road out catches that one. The start sequence carries no handler anywhere between the step that raises and its own return, and the build above it carries none either, between the call it makes on the sequence and the caller it returns to.

## What the live host makes of it

[The account's own thread](what-a-failure-at-startup-does.md) catches it, and that article has what the catch does next.

## What a replay makes of it

[A replay](replay.md) has no such thread. The failure reaches no catch inside the run, only the run's closing step, which sets the stop flag and runs the host's stopping before the failure leaves.

So the stopping is run over a host whose start never finished, and the failure carries out of the run to [the record kept of it](what-a-replay-run-reports-back.md).

## Related

- [Which hosts the checkpoint timer runs on](which-hosts-the-checkpoint-timer-runs-on.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)
- [What a replay run reports back](what-a-replay-run-reports-back.md)
