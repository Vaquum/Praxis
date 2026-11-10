---
row: N72-06
baseline: 49aa659
created: 2026-11-08 21:25 UTC
modified: 2026-11-08 21:25 UTC
evidence:
  - claim: "Each strategy the manifest names is built, and the name it is filed under is that strategy's own name trimmed"
    source: "`nexus/startup/sequencer.py` 509-512, trimmed at 510"
  - claim: "Each built strategy is wrapped before being filed, and the runner is written over the field only once the whole collection is built"
    source: "`nexus/startup/sequencer.py` 512, then 514"
  - claim: "The whole of the building sits inside one attempt naming the ordinary kind of failure, so such a failure anywhere in it becomes one complaint carrying that failure's words"
    source: "`nexus/startup/sequencer.py` 506 and 515 around 507-514, raising at 516"
  - claim: "The complaint names the step and not the strategy, and keeps the original failure as its cause"
    source: "`nexus/startup/sequencer.py` 516, naming the step alone and raising from the failure"
  - claim: "The trimming of that name can change nothing, the manifest's own record having already refused a name differing from itself trimmed"
    source: "`nexus/startup/sequencer.py` 510, against `nexus/infrastructure/manifest.py` 136-142"
  - claim: "A manifest that is not in hand stops the building with its own complaint"
    source: "`nexus/startup/sequencer.py` 503-504"
---
# How the strategies are built

Starting a host builds every strategy the manifest names, all inside one attempt.

## What is built

Each strategy in turn, filed under its own name trimmed, and wrapped before it is filed.

The runner is written over the field only once the whole collection is built. So a building that fails partway leaves the field holding whatever runner was there before, and the strategies it had built exist only in what the failure discarded.

## One attempt around all of it

The whole of the building sits inside a single attempt naming the ordinary kind of failure. Such a failure anywhere in it — a file that will not import, a class that will not build, one strategy of six — becomes one complaint carrying that failure's own words. A failure of another kind passes the attempt untouched.

That complaint names the step and not the strategy. Which of them failed is in the words carried over, or in the cause the complaint keeps attached to itself.

## The trimming that can change nothing

A strategy's name is trimmed before it is used as a key.

That trimming can change nothing. [The manifest's own record](what-the-strategy-records-refuse.md) refuses a name differing from itself trimmed, so every name arriving here is trimmed already.

So the key is the name, and two strategies cannot collide by padding — the collision is refused a step earlier, where the manifest was read.

## Related

- [Starting a host](starting-a-host.md)
- [The key this record will not trim for you](the-key-this-record-will-not-trim-for-you.md)
