---
row: N1-01
baseline: 49aa659
created: 2026-10-16 09:10 UTC
modified: 2026-10-22 08:39 UTC
reviewed: 2026-10-22 08:39 UTC
evidence:
  - claim: "A reservation is refused before any limit where money is deployed with no record of which strategy holds it, or where that record does not add up to the deployed total"
    source: "`nexus/core/capital_controller/capital_controller.py` 340-365 before 367"
  - claim: "What is set aside is the order's worth and the fees expected with it"
    source: "`nexus/core/capital_controller/capital_controller.py` 324, held at 419"
  - claim: "The first limit weighs the order's worth alone against a fraction of the pool"
    source: "`nexus/core/capital_controller/capital_controller.py` 369-377"
  - claim: "The strategy's budget is weighed against its deployment plus the worth and the fees together"
    source: "`nexus/core/capital_controller/capital_controller.py` 378-386"
  - claim: "Free capital is the pool less positions, working orders, money in flight, the fee reserve and what is already set aside"
    source: "`nexus/core/domain/capital_state.py` 109-115, read at `nexus/core/capital_controller/capital_controller.py` 387-395"
  - claim: "Everything deployed, plus what this order and its fees come to, is weighed against four fifths of the pool"
    source: "`nexus/core/capital_controller/capital_controller.py` 331-336 and 396-406, the fraction at 44"
  - claim: "The fee reserve is left out of that sum, and taken off free capital all the same"
    source: "`nexus/core/capital_controller/capital_controller.py` 331-336 against `nexus/core/domain/capital_state.py` 109-115"
  - claim: "A reservation carries a moment it runs out at, and one claimed past it is released and refused"
    source: "`nexus/core/capital_controller/capital_controller.py` 414 against 563-575"
  - claim: "Expired ones are cleared as another call comes through, rather than by time passing"
    source: "`nexus/core/capital_controller/capital_controller.py` 578"
---
# How Nexus sets money aside

Partway through the checks a decision passes before it is sent, Nexus sets aside what the trade would cost: the order's worth and the fees expected with it. Two bookkeeping checks come first, and then four limits.

## Before the limits

A reservation is refused outright where the account has money deployed and no record of which strategy holds it, and where that record does not add up to the deployed total. Either says the books are out and must be put right before more is set aside.

## Four limits

The first weighs the order's worth on its own, fees excluded, against a fraction of the pool, so no single order takes more than its share.

The second weighs the strategy's own budget, where the fees do count: what it already has deployed, plus this worth and these fees, must stay inside it.

The third weighs free capital: the pool less the positions held, the orders working, the money already in flight, a reserve kept for fees, and everything already set aside.

The fourth weighs everything deployed — positions, working orders, money in flight, what is set aside — plus what this order and its fees come to, against four fifths of the pool. The fee reserve is left out of that sum and taken off free capital all the same, so the last fifth is not held clear of everything.

## It runs out

Each reservation carries a moment it expires at, set from the life asked for as it is granted. [What becomes of it then](what-becomes-of-money-set-aside.md) — claimed, refused, or swept — is its own matter.

## Related

- [What becomes of money set aside](what-becomes-of-money-set-aside.md)
- [What Nexus does when a command does not get across](what-nexus-does-when-a-command-does-not-get-across.md)
- [What an account is](what-an-account-is.md)

---

Created 2026-10-16 09:10 UTC · Last modified 2026-10-22 08:39 UTC
