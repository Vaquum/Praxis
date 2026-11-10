---
row: N6-10
baseline: 49aa659
created: 2026-10-26 16:26 UTC
modified: 2026-11-09 04:13 UTC
evidence:
  - claim: "A stopping host sets the mode to halted at the head of its sequence, before it stops a loop of its own"
    source: "`nexus/startup/shutdown_sequencer.py` 183 into 219-227, before 184-186"
  - claim: "Within the first stage of the walk, a mode other than active refuses an entry, and halted refuses an exit or a change as well"
    source: "`nexus/core/validator/intake_stage.py` 356 into 358-370 and 372-380, reached at 442, the stage standing first at `nexus/core/validator/pipeline_models.py` 50-51"
  - claim: "The refusal returns before that stage's own hooks are called, so what a hook would weigh of the request goes unweighed"
    source: "`nexus/core/validator/intake_stage.py` 443-444 before 446-447, the hook installed at 63-71"
  - claim: "Each refusal names the stage it came from and carries a code of its own"
    source: "`nexus/core/validator/intake_stage.py` 362-369, or 376-383, or 387 where neither applies"
  - claim: "An abort is sent before the walk is asked for at all, so no mode weighs it"
    source: "`nexus/strategy/action_submit.py` 201-203 returning before 242"
  - claim: "A sale a stopping host sends is one a strategy asked for, approved by the host itself rather than by the walk"
    source: "`nexus/startup/shutdown_sequencer.py` 325-328 into 382-384 and 398-407, against `nexus/strategy/action_submit.py` 242"
---
# What the halted mode turns away

Halted is the mode [a stopping host sets first](what-a-stopping-host-halts-first.md), and it is what [the walk's first stage](what-each-check-weighs.md) reads when a strategy asks for something while the stop is under way.

## The three it refuses

An entry is refused under any mode but active. Under halted an exit and a change are refused too. Each refusal names the stage it came from and carries a code of its own, so the caller can tell the mode apart from the other grounds that stage has.

The refusal returns before that stage's hooks are called, so whatever a hook would have weighed of the request goes unweighed.

## The two that go anyway

[An abort](the-roads-around-the-checks.md) is sent before the walk is asked for at all, so no mode weighs it. A strategy asking to abandon its work during the stop has that sent whatever the mode says.

[A sale the host itself sends as it stops](the-sale-a-host-sends-as-it-stops.md) is one a strategy asked for too, but the host approves it rather than putting it to the walk. So the same close a strategy cannot get through the ordinary road goes out on this one.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [The roads around the checks](the-roads-around-the-checks.md)

---

Created 2026-10-26 16:26 UTC · Last modified 2026-11-09 04:13 UTC
