---
row: N7-05
baseline: 49aa659
created: 2026-10-27 08:14 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "A mark is put on the record Praxis keeps of a command where its handover timed out and a record for it still stands"
    source: "`praxis/launcher.py` 1975-1978, reached from `nexus/strategy/action_submit.py` 338-341"
  - claim: "What timed out is the wait for a name to come back, and Praxis answers with one as it queues the command, the send to the venue being the account's worker later"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 186 over `praxis/core/execution_manager.py` 3550 into 3582, the sending at 3984 into 3993-4009"
  - claim: "The watch takes the moment once and gathers the records carrying such a mark whose own moment is far enough back against that one moment"
    source: "`praxis/launcher.py` 2284, then 2286-2293"
  - claim: "The gathering is done under the registry's own lock, and the longest of those waits worked out after that lock is let go"
    source: "`praxis/launcher.py` 2286-2293, then 2298"
  - claim: "It answers at once where it gathers none, and otherwise works out the longest of those waits and a list of the names taking at most ten"
    source: "`praxis/launcher.py` 2295-2298 and 2299-2301, the cap standing at 212"
  - claim: "A mark is lifted where an outcome for that command is worked through and the working through reports success"
    source: "`praxis/launcher.py` 4363 into 4374-4378"
  - claim: "A duplicate outcome reports success without applying anything, and lifts the mark the same way"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 137-140 answered at `praxis/launcher.py` 4374"
  - claim: "Only an ending drops the record, so a successful acknowledgement lifts the mark and leaves the record standing"
    source: "`praxis/launcher.py` 4380-4382, the endings named at `nexus/infrastructure/praxis_connector/trade_outcome_type.py` 37-42"
  - claim: "A working through that reports a failure leaves the mark, and an ending still drops the record, which takes the command off the watch with the mark on it"
    source: "`praxis/launcher.py` 4364 falling past 4374-4378, before 4380-4382"
  - claim: "A raise out of that working through never reaches the dropping at all"
    source: "`praxis/launcher.py` 4363 raising past 4380"
---
# The watch over handovers that timed out

A command whose handover timed out carries a mark on the record Praxis keeps of it, and a watch of Praxis's own gathers the marks that have stood long enough.

## Where the mark comes from

[A handover that times out](what-nexus-does-when-a-command-does-not-get-across.md) puts the mark on that record, where a record for the command still stands. What the mark leaves open is whether Praxis took the command on at all: the wait that timed out was the wait for Praxis to answer with a name for it, and [the worker that sends to the venue](how-waiting-work-is-drained.md) runs later than that answer.

## What a pass does

It takes the moment once and gathers the records carrying a mark whose own moment is far enough back, every age weighed against that one moment, so a pass judges them all against the same instant. The gathering is done under the registry's own lock. Where it gathers none it answers at once. Otherwise it works out the longest of those waits and a list of the names, taking at most ten of them.

## How a command leaves the watch

A mark is lifted where [an outcome](what-an-outcome-is.md) for that command is worked through and the working through reports success. A duplicate outcome reports success without applying anything, and lifts the mark the same way.

Only an ending drops the record, so a successful acknowledgement lifts the mark and leaves the record standing. A working through that reports a failure leaves the mark — but an ending still drops the record, which takes the command off the watch with its mark on it. A raise out of the working through never reaches that dropping at all, so the record and its mark both stand.

## Related

- [What Nexus does when a command does not get across](what-nexus-does-when-a-command-does-not-get-across.md)
- [What a stopping host halts first](what-a-stopping-host-halts-first.md)

---

Created 2026-10-27 08:14 UTC · Last modified 2026-11-09 10:25 UTC
