---
row: P3-23
baseline: 49aa659
created: 2026-09-29 07:04 UTC
modified: 2026-09-29 08:45 UTC
evidence:
  - claim: "A flag is set before the first sending"
    source: "`execution_manager.py` 4906"
  - claim: "A second attempt turns back on finding it set"
    source: "`execution_manager.py` 4884-4885"
  - claim: "Three places put it up for the first time, and all pass that guard"
    source: "`execution_manager.py` 4635, 4715 and 4753"
  - claim: "Changing the prices sends a replacement pair without passing the first-placement guard"
    source: "`execution_manager.py` 9671, its own check being at 9395"
  - claim: "The record is kept with the resting pair's name on it"
    source: "`execution_manager.py` 5031-5037"
  - claim: "A later change to the prices works from that name"
    source: "read at `execution_manager.py` 9387, used at 9429 and 9454-9455"
  - claim: "A cancellation reaching the outcome producer reports an ending for the exit request"
    source: "`execution_manager.py` 10662-10741"
  - claim: "A cancellation made while changing the prices is written down without going there"
    source: "`execution_manager.py` 9598-9612"
  - claim: "Recovery puts up a closing order under that same exit request"
    source: "the name derived at `execution_manager.py` 7608, sent at 7707-7709"
  - claim: "That request is put back after having been dropped as finished"
    source: "`execution_manager.py` 7814"
  - claim: "A closing order finished with something filled as that send returns reports a second ending, unguarded"
    source: "`execution_manager.py` 7859-7883, against the guards at 4786, 8482, 8622 and 10663"
  - claim: "A fill arriving later on the venue's feed meets one of those guards"
    source: "`execution_manager.py` 10663"
---
# When protection is put up again

[Protection](protection.md) is put up once and guarded against being put up twice over. A flag is set before that first sending, and a second attempt finding it set turns back rather than raising another pair. Three places put protection up for the first time, and all pass that guard.

Changing the prices later is not one of them. A replacement pair is sent directly, without passing through that first-placement guard — though the changing has a check of its own.

The record is kept with the resting pair's name on it, and a change to those prices works from that name.

## Two endings under one name

A [cancellation](how-a-trade-is-cancelled.md) that reaches the outcome producer reports an ending for the exit request that carried the protection. One made while the prices are being changed is written down without going there.

Recovery can then put up a closing order under **that same exit request** — the name is worked out from the opening request rather than made fresh, so it comes out the same. The request is put back after having been dropped as finished.

If that closing order comes back finished with something filled, a second ending is reported, and nothing checks whether one was reported before. A fill arriving later on the venue's feed instead meets a guard and is turned back, so it is the immediate fill that does it.

## What that means for a reader

A caller treating the first ending as final has the trade's end wrong: reported cancelled, then filled.

Whether that is intended is [an open question](../register.md), recorded as U-05.

## Related

- [Protection](protection.md)
- [Outcomes](what-an-outcome-is.md)
