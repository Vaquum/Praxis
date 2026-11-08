---
row: P65-02
baseline: 49aa659
created: 2026-11-12 23:30 UTC
modified: 2026-11-12 23:30 UTC
evidence:
  - claim: "The quantity, the price and the fee are held to being finite in one test naming all three, and only then each to its own sign"
    source: "`ledger.py` 393-396, then 398-399, then 401-402, then 404-405"
  - claim: "The quantity and the price must stand above nought and the fee at or above it, so a fill charging nothing is allowed"
    source: "`ledger.py` 398, and 401, against 404"
  - claim: "A fee asset left out becomes the one the side receives, and one given must equal it"
    source: "`ledger.py` 415-416, then 418-422"
  - claim: "A moment left out becomes the present one in universal time, one carrying no zone is refused, and one carrying a zone is moved to universal time"
    source: "`ledger.py` 743-744, then 746-747, then 749"
  - claim: "The notional is worked out from the quantity and the price before the ledger's lock is taken"
    source: "`ledger.py` 425, ahead of 427"
  - claim: "Whether the account is registered is asked only inside the lock, past every check on the figures"
    source: "`ledger.py` 428-429, with 393-424 standing before it"
  - claim: "Past that come the weighings of the two balances, which are the last things that can refuse the fill"
    source: "`ledger.py` 432 into 726-736"
---
# The order a fill's refusals stand in

A fill offered to [binsim's ledger](binsims-ledger.md) passes seven checks before the ledger is touched, and whether the account exists is asked after every one of them.

## The figures

The quantity, the price and the fee are held to being finite in one test naming all three. A complaint from it names all three values, whichever was at fault.

Each is then held to its own sign, in a test of its own. The quantity and the price must stand above nought; the fee need only stand at or above it, so a fill charging nothing is allowed.

On a buy the fee is then weighed against the quantity received, by [a check the sell has no counterpart for](the-guard-a-sell-does-not-get.md).

## The fee's asset

Left out, it becomes the asset the side receives. Given, it must equal that asset.

So naming the asset is a way of asserting what the ledger would have chosen, and naming the other one is refused rather than honoured.

## The moment

Left out, it becomes the present moment in universal time. Carrying no zone, it is refused. Carrying a zone, it is moved to universal time, so every fill is filed in one zone whatever zone it arrived in.

## The account, and then the balances

The notional is worked out before the lock is taken. The lock is then taken, and only inside it is the account looked for.

So a fill for an account that was never registered is refused after every check on its figures has passed, and a caller offering nonsense figures for an account that does not exist is told about the figures.

Past the account come [the weighings of the two balances](what-settling-a-fill-moves.md), which are the last things that can refuse the fill.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [What settling a fill moves](what-settling-a-fill-moves.md)
