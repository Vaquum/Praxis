---
row: N72-03
baseline: 49aa659
created: 2026-11-13 03:30 UTC
modified: 2026-11-13 04:00 UTC
evidence:
  - claim: "The runner and the manifest must both be in hand, each missing one stopping the starting with its own complaint"
    source: "`nexus/startup/sequencer.py` 568-569, and 571-572"
  - claim: "An ordinary failure of reading the saved events becomes a complaint that stops the starting, carrying the failure's own words"
    source: "`nexus/startup/sequencer.py` 574-577"
  - claim: "A reading that comes back with nothing answers at once, so the same road serves whether anything was saved or not"
    source: "`nexus/startup/sequencer.py` 579-580"
  - claim: "The strategies an event may name are the manifest's own, each name trimmed"
    source: "`nexus/startup/sequencer.py` 582"
  - claim: "Each event's name is trimmed too, so a name padded on either side still matches"
    source: "`nexus/startup/sequencer.py` 585"
  - claim: "An event naming a strategy the manifest does not have warns and is passed over"
    source: "`nexus/startup/sequencer.py` 587-589"
  - claim: "An ordinary failure while a strategy is handed an event is logged and the next event is handed on, with nothing undone of what that strategy had already changed"
    source: "`nexus/startup/sequencer.py` 591-594"
---
# Which saved events a strategy is handed

A host coming back up hands each strategy the events saved against it, so a strategy can rebuild what it was keeping.

## What must be in hand

The runner and the manifest. Each missing one stops the starting with its own complaint.

## Reading the events

An ordinary failure of the reading becomes a complaint that stops the starting, carrying the failure's own words.

A reading that comes back with nothing answers at once. So one road serves whether anything was saved or not, and an empty reading leaves this step with nothing to do.

## Which names are allowed

The manifest's own strategy names, each trimmed. Each event's name is trimmed too, so a name padded on either side still matches.

An event naming a strategy the manifest does not have warns and is passed over.

## A strategy that fails

An ordinary failure is logged, and the next event is handed on.

So the handing over is not stopped by one strategy's failure, and the events after it still arrive. What that strategy had already changed before it failed is left as it is, nothing here undoing any of it.

The opposite choice is made a few steps later, where a strategy's ordinary failure during the startup question stops the boot.

## Related

- [What a strategy's startup answer does](what-a-strategys-startup-answer-does.md)
- [Starting a host](starting-a-host.md)
