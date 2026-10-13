---
row: P2-47
baseline: 49aa659
created: 2026-10-13 06:40 UTC
modified: 2026-10-13 06:40 UTC
evidence:
  - claim: "No snapshot landed, that moment ahead of the clock, and an age past the threshold are turned away alike"
    source: "`praxis/binsim/server.py` 338-342"
  - claim: "A key matching no account is turned away as not signed in, and a stale book before the send is read at all"
    source: "`praxis/binsim/server.py` 793-796 called at 325, the book weighed at 338-342 before 344-349"
  - claim: "A name an order was booked under before is turned away, the name being taken only as the order settles"
    source: "`praxis/binsim/ledger.py` 534-537 against 576-579, answered at `praxis/binsim/server.py` 505-509"
  - claim: "An order either balance cannot cover is turned away, and neither balance is written"
    source: "`praxis/binsim/ledger.py` 547-557 before the writes at 576-579, answered at `praxis/binsim/server.py` 510-518"
  - claim: "An amount outside the smallest and largest, or off the step, is turned away"
    source: "`praxis/binsim/server.py` 614-621 and 623-631"
  - claim: "An order worth less than the smallest value is turned away, weighed against a price the book is read for"
    source: "`praxis/binsim/server.py` 686-694, the price at 663-666"
  - claim: "A buy sized in money alone is walked again for the largest amount on the step, and that second walk can come back with nothing"
    source: "`praxis/binsim/server.py` 440 into 594-599, nothing at 596-597"
  - claim: "A buy sized in money whose walk the book cannot cover is turned away for want of depth"
    source: "`praxis/binsim/server.py` 430-438"
  - claim: "An order sized in coin is walked once, and one the book cannot fill is turned away the same way"
    source: "`praxis/binsim/server.py` 455 and 465-472"
  - claim: "A send is read for its own shape as well — symbol, side, name, one amount above nought, and a type that can only be at the market, with money sizing a buy alone"
    source: "`praxis/binsim/server.py` 351-362, 363-379, 381-385, 389-394, 397-416 and 446-451, each figure read at 700-723"
---
# When binsim turns an order away

[The simulated venue](binsim.md) refuses a send it cannot honour. A key matching no account goes first, as not signed in, and a stale book next — only then is the send read for its shape: symbol, side, name, one amount in coin or, for a buy, money, and a type only ever at the market. Each refusal is decided before anything is written, so a refused order leaves the account as it was.

## Before the book is read

[The book](binsims-book.md) must be fresh, by [an age read off the clock as a snapshot lands](what-a-binsim-snapshot-is-turned-away-for.md). No snapshot landed, that moment ahead of the clock, and an age past the threshold are treated alike: the send is refused as stale. A clock jumping back makes the second reachable.

## Against the account

A name the account [in the ledger](binsims-ledger.md) has booked an order under is refused, so one cannot be booked twice, and a refused send never takes a name. So is an order either balance cannot cover, weighed before either write.

## Against the venue's own sizes

The amount must fall between [the smallest and largest the venue trades in](the-sizes-a-venue-trades-in.md) and sit on its step, and the order be worth a smallest value, weighed at the middle of the book's two best prices rather than any it names.

## The second walk

A buy sized in money is walked across the book for what that money buys, and a walk it cannot cover is refused for want of depth — as is an order in coin the book cannot fill. Where the money is covered, that buy is walked again for the largest amount on the step and booked from that second walk, which can come back with nothing and leave it refused for its size.

## Related

- [Binsim](binsim.md)
- [Binsim's book](binsims-book.md)
- [Binsim's ledger](binsims-ledger.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)

---

Created 2026-10-13 06:40 UTC · Last modified 2026-10-13 06:40 UTC
