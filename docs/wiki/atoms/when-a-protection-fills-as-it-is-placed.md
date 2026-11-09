---
row: P156-02
baseline: 49aa659
created: 2026-11-15 22:30 UTC
modified: 2026-11-15 22:30 UTC
evidence:
  - claim: "Each fill carried back by the venue's answer is written to the record and applied only where the write answered with a place"
    source: "`execution_manager.py` 5056, then 5057 into 5058"
  - claim: "The protective order is then read back from the account's own state"
    source: "`execution_manager.py` 5072"
  - claim: "An order already in a terminal state having filled something has the exit's outcome built from the admitted totals"
    source: "`execution_manager.py` 5073-5077 into 5078-5080, then 5082-5084"
  - claim: "That outcome's average price is the admitted money over the admitted amount, and nothing where nothing was admitted"
    source: "`execution_manager.py` 5090-5091"
  - claim: "The three protective prices and the average entry price were already set on the bracket, and its protection already called active, before any of this"
    source: "`execution_manager.py` 5031-5036, ahead of 5072"
---
# When a protection fills as it is placed

A protective pair can come back from the venue already filled, and the placing reads its own order back to find out.

## The fills that came with the answer

Each is written to the record and applied only where the write answered with a place. A duplicate write answers with none, and nothing is applied — the same guard [the flatten recovery](why-a-flatten-is-recovered-only-once.md) relies on.

## Reading the order back

The protective order is read from the account's own state, after those fills have been applied. So what it says reflects the fills just written rather than what the venue reported directly.

An order found already in a terminal state having filled something has the exit's outcome built from [the admitted totals](two-ways-of-asking-what-a-command-filled.md), its average price the admitted money over the admitted amount.

## What was already true by then

The three protective prices, the average entry price, and the word active were all set on the bracket before the order was read back.

So a protection that filled the moment it was placed is first recorded as active and then given an outcome, in that order — and a reader catching the bracket in between sees a live protection for a position that has already closed.

## Related

- [When a bracket's protection becomes active](when-a-brackets-protection-becomes-active.md)
- [Why a flatten is recovered only once](why-a-flatten-is-recovered-only-once.md)
- [Two ways of asking what a command filled](two-ways-of-asking-what-a-command-filled.md)
