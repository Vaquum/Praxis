---
row: P139-01
baseline: 49aa659
created: 2026-11-09 10:54 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Each of the four readings looks the account up first and refuses a name the manager does not hold"
    source: "`execution_manager.py` 2789, then 2790 into 2791-2793, and 2810, then 2811 into 2812-2814, and 2831, then 2832 into 2833-2835, and 2880, then 2881 into 2882-2884"
  - claim: "Reading an account's positions hands back a snapshot of them"
    source: "`execution_manager.py` 2794"
  - claim: "Reading its balances, its per-asset balances and its per-trade results each hand back what the ledger's own reading gives"
    source: "`execution_manager.py` 2815, and 2836, and 2885"
  - claim: "Every one of those readings of the ledger takes the ledger's own lock and hands back something freshly made"
    source: "`account_ledger.py` 154, then 155, and 187, then 188"
  - claim: "Reading the open orders hands back a copy of each order"
    source: "`execution_manager.py` 923"
  - claim: "Reading the trading state hands back the account's own object"
    source: "`execution_manager.py` 2898, then 2899"
  - claim: "That object is the one the account's own work writes its orders and positions into"
    source: "`execution_manager.py` 2794, reading the same object 2899 hands over"
  - claim: "Asking which trade a command belongs to reads one mapping that spans every account, with no account named at all"
    source: "`execution_manager.py` 2912"
---
# Which readings hand back a copy

Most ways of reading an account's figures hand back something detached from the account, and one hands back the account's own object.

## The detached ones

The positions come back as a snapshot. The balances, the per-asset balances and the per-trade results each come back as [what the ledger's own reading gives](what-a-reading-of-the-ledger-hands-back.md) — freshly made, under the ledger's own lock. The open orders come back as a copy of each order.

So a caller can hold any of those, read them at leisure, and the account moves on without it.

## The one that is not

Reading the trading state hands back the account's own object — the same one the account's work writes its orders and positions into.

A caller holding it holds the account's state itself. Reading a figure off it later gives whatever the account has since done, and writing to it writes to the account.

## The one that names no account

Asking which trade a command belongs to reads a single mapping that spans every account. No account is named and none is checked, so a command's trade can be looked up by anyone who knows the command's name.

## Related

- [What a reading of the ledger hands back](what-a-reading-of-the-ledger-hands-back.md)
- [What the manager tells you about an unknown account](what-the-manager-tells-you-about-an-unknown-account.md)
- [What an account is](what-an-account-is.md)
