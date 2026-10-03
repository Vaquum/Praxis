---
row: P4-10
baseline: 49aa659
created: 2026-10-03 17:00 UTC
modified: 2026-10-03 17:06 UTC
evidence:
  - claim: "An abandonment names the command, the account and a reason, each of which must be something rather than nothing"
    source: "`trade_abort.py` 40-41 into `_require_str.py` 28-30"
  - claim: "Its moment must carry a zone and an offset, and nothing on it changes afterwards"
    source: "`trade_abort.py` 43-45, frozen at 18"
  - claim: "It asks for the command's order to be cancelled where one is out"
    source: "`execution_manager.py` 8489-8536"
  - claim: "An account never registered refuses it"
    source: "`execution_manager.py` 2995-2998"
  - claim: "An account whose start failed refuses it, that account's worker skipping every pass without draining anything"
    source: "`execution_manager.py` 3000-3012, the state left at 3643-3661 from `trading.py` 522 and 606-623, skipping at `execution_manager.py` 3903-3905"
  - claim: "An account whose worker has finished refuses it too"
    source: "`execution_manager.py` 3000-3001, the worker tied to its task at 832-835"
  - claim: "A worker poisoned but still running takes abandonments, carrying on round its loop"
    source: "`execution_manager.py` 3910-3941 and 3969-3971, poisoned at 3773-3780"
  - claim: "A command the host never accepted refuses it, the store of accepted ones spanning every account"
    source: "`validate_trade_abort.py` 40-44, the store made at `execution_manager.py` 693, filled at 3522 and passed in at 3014-3018"
  - claim: "A command belonging to another account refuses it"
    source: "`validate_trade_abort.py` 46-51"
  - claim: "A command already ended makes it do nothing, rather than refusing"
    source: "`validate_trade_abort.py` 53 into `execution_manager.py` 3020-3025"
  - claim: "What survives goes onto a queue the worker drains before taking new work"
    source: "`execution_manager.py` 3027, drained at 3910-3941 ahead of 3980-3984"
---
# Abandoning work outright

An **abandonment** tells Praxis to give up on one [command](what-a-command-must-carry.md) — not to alter it, as [a change](changing-work-already-sent.md) does, but to ask that it stop. Where an order is already out, that means asking the venue to cancel it.

## What it carries

The name of the command, the account, and a reason. Each must be something rather than nothing. Its moment must carry a zone and an offset, and nothing on it changes once it is made.

## What refuses it

An account never registered refuses it. So does one whose start failed: that account's worker skips every pass without draining anything, so an abandonment left on its queue would sit there for good. So does one whose worker has finished, which cannot resume.

A worker poisoned but still running is not refused. It goes on round its loop and goes on taking abandonments.

A command the host never accepted refuses it — the store of accepted commands spans every account, so this catches a name the host has never seen at all. A command belonging to a different account than the abandonment names refuses it separately.

## What makes it do nothing

A command that has already ended. Here the abandonment is not refused: it is noted and dropped, with nothing queued, nothing cancelled and no outcome made.

## Where it goes

What survives goes onto a queue [the worker](how-waiting-work-is-drained.md) drains before taking new work. [What it then does](where-an-abandonment-lands.md) depends on how far the command had got.

## Related

- [Where an abandonment lands](where-an-abandonment-lands.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
