---
row: N76-04
baseline: 49aa659
created: 2026-11-13 07:30 UTC
modified: 2026-11-13 07:30 UTC
evidence:
  - claim: "A plain reading of the log keeps only the records of a strategy event, unpacking each and passing over every record of a state change"
    source: "`nexus/infrastructure/state_store.py` 345 into 346-350"
  - claim: "A refresh of the loss windows reads the log itself, from inside the lock it holds, rather than being handed events"
    source: "`nexus/infrastructure/state_store.py` 378, inside 377"
  - claim: "The moment the refresh measures its windows back from is read off the clock as the refresh runs"
    source: "`nexus/infrastructure/state_store.py` 379, used at 380"
  - claim: "The refresh derives its losses only where the log left events, and leaves them empty where it left none"
    source: "`nexus/infrastructure/state_store.py` 380"
  - claim: "A strategy the derived losses do not name has all three of its windows set to nought"
    source: "`nexus/infrastructure/state_store.py` 387, then 388-390"
---
# What a refresh of the loss windows reads

A refresh re-reckons a host's rolling losses, and it reads the whole log again to do it.

## The plain reading

A plain reading of the log keeps only the records of a strategy event, unpacking each. Every record of a state change is passed over, so the reading hands back events alone however much else the log holds.

## Where the refresh gets its events

From that reading, made itself, inside the lock the refresh already holds. Nothing is handed to it.

So each refresh walks the whole log from the front, taking every record the log still holds after [the last checkpoint cut it](what-the-thirty-day-cut-leaves.md).

## The moment

Read off the clock as the refresh runs, and the windows measured back from it. So the same log refreshed an hour later measures from an hour later, which is the point of refreshing at all: an event sitting inside a window at one refresh falls outside it at a later one.

## Where the log left nothing

The losses are derived only where the log left events behind. Where it left none they stay empty, and a strategy the derived losses do not name has all three of its windows set to nought — so [the pass that writes them](where-a-realized-result-is-written-down.md) can only ever lower a window that no event now falls inside.

## Related

- [What a recovery takes before it rebuilds](what-a-recovery-takes-before-it-rebuilds.md)
- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
