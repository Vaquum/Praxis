---
row: N1-08
baseline: 49aa659
created: 2026-10-18 16:30 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "An abandonment a strategy asks for is sent before the walk is reached, so no stage runs for it"
    source: "`nexus/strategy/action_submit.py` 201-203 returning before the walk at 242"
  - claim: "A stopping host keeps only the exits and abandonments its strategies ask for, logging the rest and leaving them out"
    source: "`nexus/startup/shutdown_sequencer.py` 343 and 356-363, nothing kept returning at 365-366"
  - claim: "An exit naming a trade the record has no position for is dropped before any send"
    source: "`nexus/startup/shutdown_sequencer.py` 540-547, returned on at 394-396"
  - claim: "An exit sent as the host shuts down writes its own allowed answer and sends on that"
    source: "`nexus/startup/shutdown_sequencer.py` 394-407, the answer written at 401"
  - claim: "The walk's own skipping set names an abandonment with the exits and cancellations"
    source: "`nexus/core/validator/pipeline_executor.py` 162-176"
  - claim: "No action skips intake, though a walk whose order puts another stage first can refuse there and never reach it"
    source: "`nexus/core/validator/pipeline_executor.py` 170-176 naming the other five, the order accepted at 81-99 and walked at 47-73"
  - claim: "Nothing builds a request carrying an abandonment, the one request built outside the walk being an exit"
    source: "`nexus/startup/shutdown_sequencer.py` 556-558"
  - claim: "A shutdown whose wait runs out abandons each command still pending, sent the same way with no request built and no walk"
    source: "`nexus/startup/shutdown_sequencer.py` 793-800"
  - claim: "A strategy asks for one of four things, and a cancellation is not among them"
    source: "`nexus/strategy/action.py` 29-32 against `nexus/core/validator/pipeline_executor.py` 165"
  - claim: "The shutdown's exit is sent straight to Praxis, and a send raising an ordinary failure is logged and passed over, an interrupt going straight past the catch"
    source: "`nexus/startup/shutdown_sequencer.py` 406-414, catching `Exception` rather than `BaseException`"
---
# The roads around the checks

Three kinds of order reach Praxis without going through [the checks a decision passes](the-checks-a-decision-passes.md).

## An abandonment a strategy asks for

A strategy asking to abandon its work has that sent before the walk is reached, so not one stage runs for it, intake included — and no action skips intake.

The walk's own skipping set names an abandonment, as though one could arrive and skip five stages of six. Nothing builds a request carrying one, so that entry decides nothing: the only request built outside the walk is an exit.

[A cancellation](how-a-trade-is-cancelled.md) is named there on the same terms. The four things a strategy asks for are to enter, to exit, to change and to abandon, so a walk that runs is for an entry, an exit or a change, and those two entries never match.

## An exit sent as the host shuts down

[A host stopping with work in flight](../spines/stopping-a-host-with-work-in-flight.md) keeps the exits and abandonments its strategies ask for, logging anything else and leaving it out. An exit naming a trade the record has no position for is dropped before any send. It builds the request the stages would read, then writes an allowed answer itself and sends on that.

So [the stages](what-each-check-weighs.md) a closing exit would have skipped anyway are skipped here too, and intake with them.

A send raising an ordinary failure is logged there and passed over, the shutdown carrying on. An interrupt goes straight past that catch.

## An abandonment the shutdown runs out of time for

Where the wait for that closing runs out, each command still pending is abandoned — sent the same way, with no request built and no walk, and the same handling for a send that fails.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [Stopping a host with work in flight](../spines/stopping-a-host-with-work-in-flight.md)
- [Abandoning work outright](abandoning-work-outright.md)

---

Created 2026-10-18 16:30 UTC · Last modified 2026-10-23 07:08 UTC
