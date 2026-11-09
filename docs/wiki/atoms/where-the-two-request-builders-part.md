---
row: P119-02
baseline: 49aa659
created: 2026-11-15 04:00 UTC
modified: 2026-11-15 04:00 UTC
evidence:
  - claim: "An entry carrying no size is reported and dropped, and an exit carrying none is dropped the same way"
    source: "`launcher.py` 1209 into 1217, and 1295 into 1303"
  - claim: "Where the action names no side, an entry takes a buy and an exit a sell"
    source: "`launcher.py` 1172, against 1376"
  - claim: "Every road that builds a request estimates the fee as the sum times the rate"
    source: "`launcher.py` 1176, or 1252, and 1375"
  - claim: "An entry's sum is worked out against a reference price and an exit's against the price its position was entered at"
    source: "`launcher.py` 1251, against 1374"
  - claim: "An entry's size starts as the action's own and stays there where no adapter was given"
    source: "`launcher.py` 1219, past 1221"
  - claim: "The snapped amount replaces the action's own on both roads, each after its own refusal has been weighed"
    source: "`launcher.py` 1248-1249, and 1371-1372"
  - claim: "Which level an exit's refusal is reported at is chosen by whether the whole remainder was meant"
    source: "`launcher.py` 1324"
---
# Where the two request builders part

An entry and an exit are built by two routines of their own, and the two agree on more than they differ on.

## What both do

Drop an action carrying no size, reporting it first. Hand the venue's snapping the action's amount, weigh whatever refusal comes back, and only then let the snapped amount replace the action's own. Estimate the fee as the sum times the rate — on every road either of them takes, including the one an entry sized in money answers on.

## What each works from

An entry's sum is worked out against [a reference price](what-an-entrys-sum-is-worked-out-from.md): the action's own, or a provider's where the action carries none, and the action is dropped where neither gives one.

An exit's sum is worked out against the price its position was entered at. There is nothing to fall back on and nothing to drop for, because a position the exit refers to always carries that price.

## The side each assumes

Where the action names no side, an entry takes a buy and an exit a sell. Neither looks at the position or the market to decide it.

## Where an entry is lenient

Its size starts as the action's own and stays there where no adapter was given, so a host built without one sizes an order at whatever the strategy asked for.

## The one refusal reported two ways

Which level an exit's refusal is reported at is chosen by whether the whole remainder was meant. So a full close the venue turns away for being too small is reported as ordinary news, and any other turned-away exit as a problem.

## Related

- [What an entry's sum is worked out from](what-an-entrys-sum-is-worked-out-from.md)
- [What Praxis works out for an exit](what-praxis-works-out-for-an-exit.md)
- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)
