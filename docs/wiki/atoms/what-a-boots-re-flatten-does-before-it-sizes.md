---
row: P172-02
baseline: 49aa659
created: 2026-11-16 06:30 UTC
modified: 2026-11-16 13:30 UTC
evidence:
  - claim: "The bracket is rebuilt in memory with the entry's name worked out from the command"
    source: "`execution_manager.py` 8228-8230, then 8231-8233, then 8234"
  - claim: "The account's waiting news is drained to empty before anything is sized"
    source: "`execution_manager.py` 8235"
  - claim: "An account poisoned by that draining abandons the recovery"
    source: "`execution_manager.py` 8237, then 8245"
  - claim: "What is left open is the entry's delivered figure less the closing command's own fills"
    source: "`execution_manager.py` 8247, then 8248, then 8249"
  - claim: "The close is then re-attempted with the names the pair could still rest under"
    source: "`execution_manager.py` 8255-8257"
  - claim: "That close asks after each of those names before placing anything"
    source: "`execution_manager.py` 7627, then 7628, then 7636"
---
# What a boot's re-flatten does before it sizes

A close that a boot finds unconfirmed at the venue is attempted again, and the figures it is sized from are read only after the account's waiting news has been drained.

## The draining first

The bracket is rebuilt in memory, with the entry's name worked out from the command. Then the account's waiting news is drained to empty.

Only after that is what remains open read: the entry's delivered figure less the closing command's own fills. So news that arrived before the boot, and was waiting, counts towards the figure rather than arriving after the close was sized.

## When the draining itself is the problem

An account poisoned by that draining abandons the recovery. The news it would have sized from cannot be trusted, and nothing is placed.

## The guard that still applies

The close is re-attempted with the names the pair could still rest under, and that close asks after each of those names before placing anything. A boot's attempt is held to the same test as a live one: a protective leg found still working stops it.

## Related

- [How an unfinished close is recovered](how-an-unfinished-close-is-recovered.md)
- [When a flatten places nothing](when-a-flatten-places-nothing.md)
- [How a cancelled protection pair is judged still working](how-a-cancelled-protection-pair-is-judged-still-working.md)
