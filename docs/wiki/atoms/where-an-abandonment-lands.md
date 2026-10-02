---
row: P4-24
baseline: 49aa659
created: 2026-10-01 18:14 UTC
modified: 2026-10-02 08:51 UTC
evidence:
  - claim: "An abandonment for a command already ended does nothing"
    source: "`execution_manager.py` 8482-8487"
  - claim: "One for work fed out in slices or laddered stops the rest being scheduled and attempts a cancel for the children already out"
    source: "`execution_manager.py` 8489-8491 into 6545-6551, 6557-6558 and 6595-6597"
  - claim: "A child the venue refuses or cannot find is left active, the rest still attempted"
    source: "`execution_manager.py` 6447-6468"
  - claim: "A ladder caught mid-change takes another path, which gives up on the first child it fails to cancel"
    source: "`execution_manager.py` 6553-6555 into 9049-9057 and 9152-9174"
  - claim: "One whose order is at the venue has a cancel sent for it, a pair through the call meant for pairs"
    source: "`execution_manager.py` 8519-8531"
  - claim: "A cancel the venue refuses leaves the order where it is, with no cancellation written down"
    source: "`execution_manager.py` 8534-8536, skipping the record written at 8538-8547"
  - claim: "The command is reported cancelled all the same, and treated as ended"
    source: "`execution_manager.py` 8568-8576 into 10567-10614"
  - claim: "One whose command was accepted but has no order yet is marked, and the marked command is dropped at each point an order would go out"
    source: "`execution_manager.py` 8500-8506, read at 4154-4168, 4482-4497, 5275-5290, 5713-5730 and 6074-6083"
  - claim: "One for a command never accepted is logged as a warning and nothing more"
    source: "`execution_manager.py` 8507-8512"
---

# Where an abandonment lands

An **abandonment** tells an [account's worker](how-waiting-work-is-drained.md) to give up on one command. A [host stopping](what-becomes-of-work-still-open.md) sends one for every command still in flight, and what it does depends on how far that command had got.

## Already finished

A command already ended takes nothing.

## Fed out in parts

[Work fed out in slices](work-fed-out-over-time.md) or laddered has the rest of it stopped from being scheduled, and a cancel attempted for the children already out. One the venue refuses or cannot find stays active, and the others are still attempted. A ladder caught mid-change takes another path again, which gives up at the first child it fails to cancel.

## Already at the venue

A command whose order is at the venue has a cancel sent for it. Where the venue refuses that cancel, the order stays where it is, unrecorded as cancelled. The command is reported cancelled all the same, and treated as ended.

## Not yet sent

A command accepted but not yet sent is marked, and the mark is read at each point an order would have gone out. One the account never accepted is logged as a warning and left there.

## Related

- [What becomes of work still open](what-becomes-of-work-still-open.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
