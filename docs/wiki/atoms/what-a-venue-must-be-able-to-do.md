---
row: P4-13
baseline: 49aa659
created: 2026-10-03 17:54 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "Twenty-one operations are declared for anything called a venue"
    source: "`venue_adapter.py` 741, 756, 769, 782, 850, 896, 922, 948, 974, 1000, 1018, 1036, 1066, 1090, 1106, 1125, 1135, 1150, 1160, 1178 and 1191"
  - claim: "Each is declared and left empty, so the declaration is all there is to it"
    source: "`venue_adapter.py` 754, 780 and the ellipsis closing each of the twenty-one"
  - claim: "The rounding one snaps an amount and may refuse it, leaving it alone where no rules are held"
    source: "`binance_adapter.py` 1378-1422"
  - claim: "The open-orders one answers for one account and one pair"
    source: "`binance_adapter.py` 1829-1832"
  - claim: "The one named for the exchange's own figures answers with one pair's rules"
    source: "`binance_adapter.py` 2220-2229"
  - claim: "The rules are held after loading and given back from that store, or nothing where none is held"
    source: "`binance_adapter.py` 2135-2138 and 2153"
  - claim: "Several records the answers come in are declared alongside, each naming its fields"
    source: "`venue_adapter.py` 123-126, 139-140, 160-168, 237-243, 264-266, 313-317, 419-421 and 433-437"
  - claim: "So are the kinds of failure, four of which name extra detail"
    source: "`venue_adapter.py` 614-617, 661-663, 690-693 and 710-714"
  - claim: "Being a venue is declared checkable at run time, which tests for the names alone"
    source: "`venue_adapter.py` 731-732"
  - claim: "Nothing in Praxis itself makes that check; only its tests do"
    source: "`test_venue_adapter.py` 321, 372 and 379, and `test_replay_venue_adapter.py` 52"
  - claim: "The replay runner passes its venue through a cast, which checks nothing there"
    source: "`run_replay.py` 140"
  - claim: "A venue carrying every name need not do every one: the replaying venue refuses the feed-reading one"
    source: "`replay_venue_adapter.py` 440-441"
---
# What a venue must be able to do

A **venue** in Praxis is not a particular exchange. It is a list of twenty-one operations declared in one place, with the records its answers come in, and the kinds of failure it may raise, declared beside them.

## The twenty-one

An account registered, and unregistered. What that account's key is allowed to do.

An amount snapped to what the trading pair allows — which may refuse it, and which leaves it alone where no rules for the pair are held.

An order sent, one cancelled, a linked pair cancelled. One order asked about, one linked pair asked about, and the orders still open for one account and one pair.

Balances, trades, and money moved into or out of the account. One pair's rules — despite the name of that operation pointing at the exchange. [A book](the-order-book.md), and the time.

[How it is faring](health.md). A pair's rules loaded, and given back afterwards from where they were put, or nothing where none are held. A report read into a shape Praxis knows. Closing.

## What the list is worth

Each of the twenty-one is declared and left empty, so the declaration is the whole of it.

The list is declared checkable while running, and that check tests for the names alone — not for what they take, what they give back, or whether they work. Nothing in Praxis itself makes the check; only its tests do. [The replay runner](replay.md) passes its venue through a cast, which checks nothing there either.

So carrying every name is not doing every one. [The replaying venue](the-replay-venue.md) carries the feed-reading operation and refuses it when called.

## Related

- [What a venue is](what-a-venue-is.md)
- [The replay venue](the-replay-venue.md)
