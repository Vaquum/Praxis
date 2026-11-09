---
row: P128-02
baseline: 49aa659
created: 2026-11-15 08:30 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "The two folders and the reader over them are settled, and the account's accounting wiring published part way through the build, under its own lock"
    source: "`launcher.py` 4147, then 4150, then 4153, then 4348-4353, then 4354 into 4355"
  - claim: "The outcomes a previous run recorded but never acknowledged are re-delivered after that, still inside the build"
    source: "`launcher.py` 4547, past 4354-4355"
  - claim: "The actions the startup sequence held over are drained next"
    source: "`launcher.py` 4549, past 4547"
  - claim: "Only then are the loops built: the predicting one, a timer one where the settings carry timers, the consuming one, and the rest"
    source: "`launcher.py` 4551-4559, then 4563 into 4564-4569, then 4573-4581, then 4583-4589"
  - claim: "The runtime itself is handed back at the end of all of it"
    source: "`launcher.py` 4635"
  - claim: "The host publishes that runtime only once the build has answered, and starts the loops after"
    source: "`launcher.py` 3993 into 3994, then 3995"
---
# What runs before an account's loops do

Two things happen inside an account's build that send orders and move figures, and both of them run before any of the account's loops exists.

## The order

The account's accounting wiring is published part way through, under its own lock. Then the outcomes a previous run recorded but never acknowledged are re-delivered. Then the actions the startup sequence held over are drained.

Only after all three are the loops built — the predicting one, a timer one where the settings carry timers, the consuming one, and the rest — and the runtime handed back at the end.

## What the window means

The host publishes the runtime only once that build has answered, and starts the loops after that.

So during the replay and the drain, the account is one the figures can be moved for and not one anything can be asked of. That is exactly the split [the two mappings](the-two-mappings-an-account-lives-in.md) keep, and this is the window it was kept for: an outcome re-delivered here is accounted for, where an operator asking about the account in the same moment is refused.

## Why the wiring comes first

The replay routes its outcomes through the same working-through a live outcome takes, and that reads the wiring. Publishing it earlier in the build is what lets a replayed outcome reach the figures at all.

## Related

- [The two mappings an account lives in](the-two-mappings-an-account-lives-in.md)
- [When an account can be delivered to](when-an-account-can-be-delivered-to.md)
- [The order an account's loops start and stop in](the-order-an-accounts-loops-start-and-stop-in.md)
