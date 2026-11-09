---
row: P118-01
baseline: 49aa659
created: 2026-11-09 09:17 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "Four sets of limits are made as the walk is built: the risk limits empty, the price limits worked out from the account's settings, the platform caps taken from the caller where one came and made empty where none did, and the health policy empty"
    source: "`launcher.py` 964, then 965, then 966, then 967"
  - claim: "The hooks the first check runs are built once, before any check is made"
    source: "`launcher.py` 959-963"
  - claim: "Three checks read nothing beyond what they were built holding: the first its hooks, the second its limits, the fourth the account's money"
    source: "`launcher.py` 970, and 973, and 983"
  - claim: "The other three call a provider as each decision arrives, for a price reading, a health reading and a platform reading"
    source: "`launcher.py` 976-980, and 986-990, and 995-999, the platform one handed back at 625 and the price one at 3790"
  - claim: "Two of those hand the decision's own context to the provider, where the health one hands it nothing"
    source: "`launcher.py` 979, and 998, against 988"
  - claim: "The health reading used where a caller supplies none is one fixed set of figures: no latency, no failures in a row, no failure share, the whole allowance free, and no clock drift"
    source: "`launcher.py` 540-546"
  - claim: "The platform reading used the same way is empty and the price reading is nothing at all, neither of them reading the decision it was handed"
    source: "`launcher.py` 554, and 647"
  - claim: "The six are gathered under the stage each belongs to and handed over as the walk"
    source: "`launcher.py` 1001-1008, then 1010"
---
# What each check is built holding

[Each of the six checks](the-checks-a-decision-passes.md) a decision passes is built as a small routine holding what it needs, and what it holds decides whether it can see anything change.

## Made once

Four sets of limits, as the walk is built: the risk limits empty, the price limits [worked out from the account's settings](how-the-price-limits-are-built-from-the-configuration.md), the platform caps taken from the caller where one came and made empty where none did, and the health policy empty.

The hooks the first check runs are built once too, before any check is made, so whatever they remember between decisions is remembered for the account's whole run.

So the platform caps are the one set an operator reaches, and the other three are empty for as long as the host is up.

## Read afresh

Three of the six read nothing beyond what they were built holding: the first its hooks, the second its limits, the fourth the account's money. Those three cannot see a figure change without the walk being built again.

The other three call a provider as each decision arrives — for a price reading, a health reading, and [a platform reading](what-the-platform-ceilings-weigh.md). Two of them hand the decision's own context to the provider; the health one hands it nothing, so its reading cannot depend on what is being decided.

## What a provider gives where none is supplied

The health reading is one fixed set of figures: no latency, no failures in a row, no failure share, the whole allowance free, no clock drift. The platform reading is empty. The price reading is nothing at all, and neither of those two reads the decision it was handed.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [What the platform ceilings weigh](what-the-platform-ceilings-weigh.md)
- [How the price limits are built from the configuration](how-the-price-limits-are-built-from-the-configuration.md)
