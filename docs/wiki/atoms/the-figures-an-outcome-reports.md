---
row: P2-43
baseline: 49aa659
created: 2026-09-27 07:37 UTC
modified: 2026-09-27 13:58 UTC
evidence:
  - claim: "On the ordinary path the figure moves on as each slice is sent"
    source: "`execution_manager.py` 5923, set past the still-active child at 5920-5921"
  - claim: "Replacing a ladder's rungs instead sets both figures to the new plan's length once all are placed"
    source: "`execution_manager.py` 9315-9317, past the placing loop at 9301-9313"
  - claim: "A scheme's outcome copies that count"
    source: "`execution_manager.py` 6515-6516"
  - claim: "The plain builder reports one of one whatever happened"
    source: "`execution_manager.py` 10792-10793"
  - claim: "The durable row keeps no slice counts"
    source: "`execution_manager.py` 10817-10829, which names neither"
  - claim: "A rebuilt outcome puts one of one in their place"
    source: "`launcher.py` 1688-1689"
  - claim: "Every piece actually handed over is built without slice counts"
    source: "`outcome_translator.py` 265-270, 289-301, 314-325, 331-340 and 354-366"
  - claim: "The progress itself is kept elsewhere and restored"
    source: "`execution_manager.py` 6311-6322, restored at 1970-1979"
  - claim: "How far along it is cannot be given where no target was"
    source: "`trade_outcome.py` 182-185"
  - claim: "The plain builder takes the target from the command's amount"
    source: "`execution_manager.py` 10789, the amount being one or the other by `trade_command.py` 86-88"
  - claim: "An orphan found at a restart is given a standing target of one and nothing filled"
    source: "`execution_manager.py` 2309-2317 with the figure at 177"
  - claim: "An unfinished scheme found at the same restart keeps its real target and fills"
    source: "`execution_manager.py` 2752-2758"
---
# The figures an outcome reports

Two figures an [outcome](what-an-outcome-is.md) carries mean different things depending on which part of Praxis made it.

## The slices

The count is of parts **sent**, not parts finished. On the ordinary path it moves on as each part goes out, while that slice's order may still be resting at the venue. The outcome copies it as it stands, so a part sent and unfilled still counts.

Replacing a set of orders across price levels works differently. Nothing moves on as each new order is placed; both figures are set to the new plan's size once all of them are, so a replacement that stops part way leaves the old count standing.

A plain order reports one of one, whatever happened to it.

The outcome's own durable row keeps no slice counts. An outcome rebuilt from that row puts one of one in their place. That figure goes no further: those resent reports carry no slice counts, and sending them reaches no host-supplied receiver.

The progress is not lost, only absent from that row. It is kept separately, and restored when the work is picked up again.

## How far along

An outcome can be asked how far along it is, and answers with the amount filled against the target.

The plain builder takes that target from the amount the request asked for. An order sized in money carries no amount, so such an outcome gives no answer rather than a made-up one.

A restart does two different things, depending on what it finds. Work it finds unfinished and cannot resume is given a standing target of one with nothing filled, so it answers zero. Work carried out as several orders keeps its real target and its real fills, and answers properly.

## Related

- [Outcomes](what-an-outcome-is.md)
