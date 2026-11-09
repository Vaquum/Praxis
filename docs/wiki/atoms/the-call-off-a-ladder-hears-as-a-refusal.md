---
row: P188-02
baseline: 49aa659
created: 2026-11-09 14:21 UTC
modified: 2026-11-09 14:21 UTC
evidence:
  - claim: "A ladder with a call-off standing against it ends before its first rung, reported as cancelled with no parts at all"
    source: "`execution_manager.py` 6074, then 6075, then 6077-6082"
  - claim: "The report is built with a count of parts of nought"
    source: "`execution_manager.py` 6081, carried to 8411-8424"
  - claim: "The outcome's own type refuses a count of parts at or below nought"
    source: "`praxis/core/domain/trade_outcome.py` 146, then 147-148"
  - claim: "The raise travels out of the command's handling and is swallowed there, so no report goes out at the time"
    source: "`execution_manager.py` 4009, then 4012, past 4020"
  - claim: "The command is left accepted with no intent recorded against it and no scheme standing for it"
    source: "`execution_manager.py` 2254-2258"
  - claim: "The next boot finds it in that shape and refuses it as an orphan"
    source: "`execution_manager.py` 2270, then 2271-2275, built at 2309-2321"
  - claim: "So the caller hears about the call-off at the next boot, and hears it as a refusal"
    source: "`execution_manager.py` 2302, and 2319, against 6079"
---
# The call-off a ladder hears as a refusal

A ladder whose [cancellation](how-a-trade-is-cancelled.md) arrives before its first rung goes out is reported to Nexus at the next boot, and reported as refused rather than cancelled.

## Where it starts

A call-off standing against the command when the ladder starts ends it there, reported as cancelled with no parts at all. The report is built with a count of parts of nought.

## Where it stops

The outcome's own type refuses a count of parts at or below nought. The raise travels out of the command's handling and is swallowed there, so no report goes out at the time.

## What the command is left as

Accepted, with no intent recorded against it and no scheme standing for it — which is exactly the shape the next boot looks for in an orphan. That boot refuses it, under the boot's own reason.

## What the caller hears

A refusal, at the next boot, where the call-off said cancelled. The report is not lost; it is late, and it carries the wrong word for why the command ended.

## Related

- [Cancellation](how-a-trade-is-cancelled.md)
- [What a boot's rejection of an orphan says](what-a-boots-rejection-of-an-orphan-says.md)
- [The three kinds of orphan a boot finds](the-three-kinds-of-orphan-a-boot-finds.md)
