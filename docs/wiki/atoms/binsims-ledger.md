---
row: P3-07
baseline: 49aa659
created: 2026-09-28 10:52 UTC
modified: 2026-09-28 17:34 UTC
evidence:
  - claim: "It keeps balances and fills per account"
    source: "`ledger.py` 597 for balances, 613 for fills"
  - claim: "It is read from a saved file where one exists"
    source: "`ledger.py` 245-248"
  - claim: "Registering an account mints a key for it"
    source: "`ledger.py` 303"
  - claim: "A key that is not proper text names no account"
    source: "either `ledger.py` 354 or 359, whichever the key fails"
  - claim: "A protected request also needs a signature, which is not checked"
    source: "`server.py` 785-798"
  - claim: "A fill moves the balances"
    source: "`ledger.py` 444-445"
  - claim: "Binsim charges its fee in the asset the side receives"
    source: "`ledger.py` 138, taken off at 706-709"
  - claim: "Its one pair charges a buy's fee in BTC, which the Praxis-side test looks for"
    source: "`server.py` 98 with `ledger.py` 138, against `trading_state.py` 84-85"
  - claim: "One holder at a time may write the state"
    source: "`ledger.py` 76, refused at 77-84"
  - claim: "Registering against a directory a service holds is refused"
    source: "`__main__.py` 250-255 and 311-312"
---
# Binsim's ledger

What [the simulated venue](binsim.md) keeps per account is a **ledger**: the balances that account holds and the fills it has been given. It stands where a real exchange would keep an account.

It is read from a saved file where one exists, so balances survive the service stopping and starting again.

## Keys and callers

An account is registered from the command line, and registering mints a key for it. A key that is not proper text names no account at all.

Naming the account is not the whole of getting in. A protected request must also carry a signature — which binsim requires to be there and never checks.

## What a fill does

A fill moves the balances, coin one way and money the other, and takes a fee off what the account receives.

Binsim charges that fee in the asset the side receives: coin on a buy, money on a sell.

For the one pair binsim knows, that lines up with [the Praxis side](the-commission-and-the-amount.md). A buy's fee is charged in BTC, which is what the subtraction there tests for, so both ends take it off the same way.

## One writer

Only one holder at a time may write the saved state, and a second is refused.

That is why registering an account against a directory a running service holds is refused: the service holds the state, and the registering would write it whole from underneath.

## Related

- [Binsim](binsim.md)
- [Binsim's book](binsims-book.md)
