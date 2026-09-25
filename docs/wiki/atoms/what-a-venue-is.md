---
row: P2-11
baseline: 49aa659
created: 2026-09-24 20:13 UTC
modified: 2026-09-25 18:58 UTC
evidence:
  - claim: "Execution holds one venue and calls it by name throughout"
    source: "stored once at `execution_manager.py` 679"
  - claim: "Outside execution, two places do ask what it really is"
    source: "`praxis/trading.py` 569 and 1711"
  - claim: "A live report stream is opened only where the venue is the exchange adapter"
    source: "opened at `praxis/trading.py` 581-588 under the test at 569, the handler returning early otherwise at 1711-1712"
  - claim: "Praxis asks a venue to place an order"
    source: "`execution_manager.py` 4269-4280"
  - claim: "It asks a venue to cancel one, and a linked pair by its own call"
    source: "either `execution_manager.py` 8527-8531 or 8521-8525"
  - claim: "It asks what became of an order, and of a linked pair separately"
    source: "either `execution_manager.py` 5519-5523 or 5582"
  - claim: "It asks what the account holds and what it has traded"
    source: "`execution_manager.py` 6662-6664 and 8061"
  - claim: "It asks for the book before pricing an order"
    source: "`execution_manager.py` 4194-4197"
  - claim: "It asks for the symbol rules, for settled transfers, and for what the keys are allowed to do"
    source: "`praxis/trading.py` 562 and 1146, and `praxis/launcher.py` 3098"
  - claim: "Snapping a quantity to the grid does not ask the venue at all; it reads rules already cached"
    source: "`binance_adapter.py` 1378-1392, returning the original where nothing is cached at 1380-1381"
  - claim: "A refusal arrives as a named kind, and which kind decides whether it is chased or recorded"
    source: "a client error becoming a rejection at `binance_adapter.py` 1151-1152 only once the named kinds at 1118-1120, 1122-1133, 1135-1137 and 1147-1149 have not claimed it; one code is then wrapped at 1645-1651 and chased at `execution_manager.py` 4282-4286, the rest re-raised at `binance_adapter.py` 1652 and recorded instead at `execution_manager.py` 4292-4295"
  - claim: "An unfamiliar status on a plain send is recorded failed like any refused value"
    source: "`binance_adapter.py` 893-897 by way of 950, recorded at `execution_manager.py` 4296-4299, the alternative arm to 4292-4295"
  - claim: "Where a pair the venue calls finished has no leg reporting a status it knows, the whole is taken as cancelled"
    source: "`binance_adapter.py` 983-994 returning at 1008-1013"
  - claim: "A pair the venue calls unfinished has its leg statuses left unread"
    source: "`binance_adapter.py` 983 reached only for the finished case"
  - claim: "Leg fills are read before the pair's own status is judged at all"
    source: "`binance_adapter.py` 969-979, ahead of 996-1000"
  - claim: "Leg names are read only once that status is one it knows"
    source: "`binance_adapter.py` 1002-1005, past the raise at 996-1000"
  - claim: "An unfamiliar status for the pair itself still raises"
    source: "`binance_adapter.py` 996-1001"
  - claim: "Most other senders record it too"
    source: "`execution_manager.py` 5347-5350, 6008-6013, 6235-6240 and 10368-10374"
  - claim: "A flatten send and a first protective send let it leave"
    source: "`execution_manager.py` 7791 and 4979-5015"
  - claim: "A flatten chases every venue error rather than the two"
    source: "`execution_manager.py` 7791-7813"
  - claim: "The same failure while chasing a single order escapes every handler, since it is raised inside one"
    source: "`binance_adapter.py` 1027-1039 raised within `execution_manager.py` 4282-4286, so it never reaches the alternative arm at 4292-4299"
  - claim: "A linked pair the venue calls refused is written off, one it calls finished has its legs asked about, and anything else is taken as live"
    source: "either `execution_manager.py` 5606-5614, 5616-5619, or 5620-5621"
  - claim: "A leg carrying an unfamiliar status escapes the chase"
    source: "raised at `binance_adapter.py` 893-897 from 1033, outside `execution_manager.py` 5677"
  - claim: "From a plain send that ends with nothing reported; under a slice it ends the run rejected"
    source: "either logged at `execution_manager.py` 4012-4019, or finalized at 5866-5882"
---
# What a venue is

A **venue** is whatever Praxis sends orders to. Execution holds exactly one and calls it by name rather than by what it is, so the same code runs against a live exchange or a simulator.

Outside execution, two places do ask what it really is: a live stream of execution reports opens only where the venue is the exchange adapter, and the handler for those reports returns early otherwise.

## What Praxis asks of one

**Do this**: place an order, cancel one, cancel a linked pair.

**Tell me**: what became of an order or a linked pair, what the [account](what-an-account-is.md) holds and has traded, what the [order book](the-order-book.md) looks like now, what the symbol's rules are, what transfers have settled, and what the keys may do.

One thing that sounds like an ask is not. Snapping an amount onto the venue's grid reads rules already cached, and hands the amount straight back where nothing is.

## What comes back when it refuses

A refusal arrives as a named kind, and the kind decides what happens. On an ordinary send two mean the fate is undecided and are [chased up](when-a-send-is-unclear.md); the rest are recorded failed. A flatten chases every one.

An unfamiliar status is recorded the same way by most senders, though a flatten or a first protective send lets it leave. On a pair the venue calls finished, legs reporting nothing it knows make the whole read as cancelled; called anything else, their statuses go unread. The same failure while chasing is not — it happens inside the handler doing the chasing, so it escapes every arm and [ends with nothing reported](a-reply-that-cannot-be-read.md). What follows depends on who was chasing: from a plain send nothing is reported, under a slice the run ends rejected.

## Related

- [What an account is](what-an-account-is.md)
- [Order placement](how-an-order-is-placed.md)
