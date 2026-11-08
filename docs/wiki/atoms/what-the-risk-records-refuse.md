---
row: N45-01
baseline: 49aa659
created: 2026-11-12 02:30 UTC
modified: 2026-11-12 03:00 UTC
evidence:
  - claim: "A strategy's record refuses a name that is not text with something left once trimmed"
    source: "`nexus/core/domain/risk_state.py` 49-51"
  - claim: "It refuses a high mark that is not finite or stands below nought, and holds its three losses to the same"
    source: "`nexus/core/domain/risk_state.py` 53-55, or 57-61"
  - claim: "Its two profit figures are held to being finite alone, so either may stand below nought"
    source: "`nexus/core/domain/risk_state.py` 63-67"
  - claim: "The account's record holds twelve figures to being finite and at or above nought: its high mark on its own, then eleven more"
    source: "`nexus/core/domain/risk_state.py` 175-177, and 179-191 into 192-195"
  - claim: "Three more are held to being finite alone: what it has realized, what it has not, and its equity"
    source: "`nexus/core/domain/risk_state.py` 197-201"
  - claim: "Equity is not a profit figure but a total: the starting capital plus both"
    source: "`nexus/core/domain/risk_state.py` 238-239, written at 302"
  - claim: "Its mapping of strategies refuses a value of the wrong kind, and a key differing from the name inside its value"
    source: "`nexus/core/domain/risk_state.py` 203-206, or 207-209"
---
# What the risk records refuse

Two records say [how far down things are](how-far-down-the-account-is.md): one per strategy, one for the account. Each sorts its figures into two kinds as it is built.

## The figures that may not go below nought

On a strategy's record: its high mark and its three rolling losses. On the account's: twelve figures, its own high mark checked on its own and eleven more walked together.

The eleven are the marks, the falls from them, the worst those falls have been — and the capital the account started with, which is held to the same rule though it is neither.

Each must be finite and stand at or above nought. A loss is carried as a positive figure here, so one below nought is a contradiction rather than a gain.

## The figures that may

On a strategy's record: what it has made, realized and unrealized. On the account's: the same two, and its equity.

Each must be finite, and nothing more is asked. The first two are signed, so a figure below nought is a loss. Equity is not a profit figure at all but a total — the starting capital plus both of the others — and it is held to the same loose rule.

## The name, and the filing

A strategy's record refuses a name that is not text with something left once the blank space is trimmed off.

The account's mapping of those records refuses a value of the wrong kind, and a key differing from the name inside its own value — [the same pair](the-keys-that-must-match-what-they-hold.md) the state a host holds makes of its two keyed mappings.

## Related

- [How far down the account is](how-far-down-the-account-is.md)
- [The figures the account does not store](the-figures-the-account-does-not-store.md)
- [The keys that must match what they hold](the-keys-that-must-match-what-they-hold.md)
