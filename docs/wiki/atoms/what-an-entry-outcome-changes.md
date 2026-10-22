---
row: N1-06
baseline: 49aa659
created: 2026-10-18 13:00 UTC
modified: 2026-10-20 12:30 UTC
evidence:
  - claim: "The outcome's type chooses the handler, and everything that is not an acknowledgement, a fill or a refusal goes to the cancellation handler, an expiry included"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 152-161"
  - claim: "An outcome whose name has been seen before is dropped as a success that changes nothing, and one naming a different command than its context names is refused, both before any handler runs"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 130-140 and 142-150"
  - claim: "The name of an outcome a handler succeeded on is recorded, which is what the dropping reads"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 163-165"
  - claim: "What sent orders hold is filled as Praxis registers the command, before the send rather than at it"
    source: "`praxis/launcher.py` 2086-2093"
  - claim: "An acknowledgement of an entry moves money from what sent orders hold to what resting orders hold, and one for anything else returns a success having moved none"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 197 and the move at `nexus/core/capital_controller/capital_controller.py` 639-640, against `nexus/infrastructure/praxis_connector/outcome_processor.py` 191-195"
  - claim: "A fill takes the filled amount and the fee estimated on it out of what resting orders hold, and puts the filled amount and the fee actually charged into what the position holds, the difference between the two fees going to the reserve"
    source: "`nexus/core/capital_controller/capital_controller.py` 955 against 956, the estimate worked out at 902-922 and the difference at 924 and 957"
  - claim: "A refusal and a cancellation each give back what the order still holds, from whichever of the two holdings it sat in, and take it out of the tracking"
    source: "`nexus/core/capital_controller/capital_controller.py` 673-676 with 687-688, and 1002-1005"
  - claim: "An acknowledgement is refused unless the order is one sent, and a fill unless it is one resting; a refusal and a cancellation take it from whichever of the two it is"
    source: "`nexus/core/capital_controller/capital_controller.py` 620-625 and 885-890 against 673-676 and 1002-1005"
  - claim: "A giving-back that fails ends an entry's outcome as a failure, so its name goes unrecorded, where the same failure on an exit is passed over"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 312-317 and 344-349, against 163-165"
---
# What an entry outcome changes

An outcome is what Praxis sends back about a command, and its kind chooses what happens to it. An acknowledgement, a fill and a refusal each have their own handling; everything else, an expiry included, is handled as [a cancellation](how-a-trade-is-cancelled.md).

## Two outcomes that change nothing

One whose name has been seen before is dropped, reported as a success that moved nothing. One naming a command its context does not is refused. Both are decided before any handling runs, and every outcome handled successfully has its name recorded, which is what the dropping reads.

## Where the money goes

[Money set aside for a command](how-nexus-sets-money-aside.md) becomes what sent orders hold as Praxis registers the command, before the send. From there each kind of outcome moves it on:

- An acknowledgement of an entry moves it to what resting orders hold, and is refused for an order not still sent. One for anything else moves none.
- A fill takes the filled amount and the fee estimated on it out of what resting orders hold, and puts that amount and the fee actually charged into what the position holds. One finishing the order releases the remainder too, and one for an order not yet resting is refused. The difference between those two fees goes to [the fee reserve](what-the-fee-reserve-absorbs.md), which can refuse the move outright.
- A refusal and a cancellation each give back what the order still holds, from whichever holding it sat in, and drop it from the tracking.

A giving-back that fails ends an entry's outcome as a failure, and a failed outcome has no name recorded, so the same one arriving again is tried. On an exit it is passed over.

[What a fill does to the position](when-an-entrys-position-grows.md) is its own matter.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What the fee reserve absorbs](what-the-fee-reserve-absorbs.md)
- [When an entry's position grows](when-an-entrys-position-grows.md)
- [What Nexus does when a command does not get across](what-nexus-does-when-a-command-does-not-get-across.md)

---

Created 2026-10-18 13:00 UTC · Last modified 2026-10-20 12:30 UTC
