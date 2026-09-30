---
row: P3-16
baseline: 49aa659
created: 2026-09-30 07:02 UTC
modified: 2026-09-30 08:50 UTC
evidence:
  - claim: "A connection is opened per account where the venue uses the Binance adapter"
    source: "`praxis/trading.py` 581-589, on the branch at 569"
  - claim: "The simulated venue uses that adapter too"
    source: "`praxis/trading.py` 215-218 with `launcher.py` 4715-4719"
  - claim: "A frame that will not parse while listening is passed over"
    source: "`binance_ws.py` 402-405"
  - claim: "A parsed frame carrying no event is logged and dropped"
    source: "`binance_ws.py` 406-409"
  - claim: "An unreadable answer during setting up is raised instead"
    source: "`binance_ws.py` 238-264"
  - claim: "The handler acts on one kind of frame and ignores the others"
    source: "`praxis/trading.py` 1708-1709"
  - claim: "A closed or failed connection ends the listening"
    source: "`binance_ws.py` 414-415"
  - claim: "The wait before trying again doubles up to a ceiling, then is drawn at random below it"
    source: "`binance_ws.py` 344-347"
  - claim: "A successful connection resets that ceiling"
    source: "`binance_ws.py` 355"
  - claim: "Reconnecting sets the account reconciling and asks the venue what it missed"
    source: "`praxis/trading.py` 1455-1464 with the gate at 1400-1407"
  - claim: "Fills also reach Praxis by being asked for"
    source: "`praxis/trading.py` 1020-1067"
---
# The venue feed

The **venue feed** is a connection Praxis keeps open to the venue, one per [account](what-an-account-is.md), over which the venue says what has happened to that account's orders without being asked. It is opened where the venue uses the Binance adapter — which [the simulated venue](binsim.md) does as well, so the feed runs against that too.

It is the ordinary way a [fill](what-a-fill-is.md) on a resting order arrives, though not the only one: fills are also [asked for](where-duplicates-stop.md) when Praxis reconciles.

## What arrives, and what is used

A frame that will not parse while listening is passed over, and one that parses but carries no event is logged and dropped. Either way the listening goes on.

That forgiveness belongs to listening. An answer that cannot be read while the connection is being set up is raised instead, and the setting up fails.

Of the frames that do carry an event, the handler acts on one kind and ignores the rest.

## When it breaks

A connection that closes, or errors, ends the listening. Praxis waits, then opens a new one.

The wait grows: a ceiling that doubles each failure up to a limit, with the actual wait drawn at random below that ceiling. The random factor reduces the chance of accounts retrying together. A connection that succeeds resets the ceiling.

## What reconnecting means

A new connection is not a resumption. Anything the venue sent while Praxis was away went to nobody, and the feed cannot say what that was.

So reconnecting sets the account reconciling and asks the venue what it missed.

## Related

- [What a venue is](what-a-venue-is.md)
- [What an account is](what-an-account-is.md)
