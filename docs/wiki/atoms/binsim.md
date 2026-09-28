---
row: P3-05
baseline: 49aa659
created: 2026-09-28 10:41 UTC
modified: 2026-09-28 17:28 UTC
evidence:
  - claim: "It answers over the web, on the paths the real venue uses"
    source: "`server.py` 192-203"
  - claim: "It answers the time, the trading rules, the book and the account"
    source: "`server.py` 194-198"
  - claim: "It takes an order sent to it"
    source: "`server.py` 201"
  - claim: "It knows one trading pair"
    source: "`server.py` 98, used at 121"
  - claim: "Its paths carry nothing for cancelling, nor for linked pairs"
    source: "`server.py` 192-203, which lists neither"
  - claim: "Asking after one order is answered with no such order"
    source: "`server.py` 291-295"
  - claim: "Asking for the open ones, or for past trades, is answered with an empty list"
    source: "`server.py` 302 and 309"
  - claim: "Accounts are registered from the command line"
    source: "`__main__.py` 275 and 282"
---
# Binsim

A simulated exchange named **binsim** can be put in place of a real one, and Praxis pointed at it. It is a program of its own, answering over the web on the same paths the real venue uses.

It is not [the venue a replay uses](the-replay-venue.md). That one lives inside the replaying program; this one runs separately, keeps [a book](binsims-book.md) and [balances](binsims-ledger.md), and is spoken to over the network.

## How far it goes

It knows one trading pair and no others. It gives the time, the trading rules, the current book and what an account holds, and it takes an order sent to it.

Its paths carry nothing for cancelling an order, and nothing for [linked pairs](order-types.md). Work needing either cannot be done against it at all.

## The three fixed answers

Asking after one order is met with **no such order**, whatever became of it. Asking for the open orders, or for past trades, is met with an empty list.

Those answers are fixed rather than wrong-by-accident, and they are still answers: [a send that went unclear](when-a-send-is-unclear.md) asks after its order, is told it does not exist, and takes the branch that declares the send failed. That branch is exercised.

What is not exercised is anything needing a truthful history — recovery that reads back what the venue really did, and reconciling against its record of past trades.

## Related

- [Binsim's book](binsims-book.md)
- [Binsim's ledger](binsims-ledger.md)
