---
row: N84-02
baseline: 49aa659
created: 2026-11-09 04:45 UTC
modified: 2026-11-09 04:45 UTC
evidence:
  - claim: "A fill's notional must be a finite figure, and must stand above nought"
    source: "`nexus/core/capital_controller/capital_controller.py` 859 into 860-861, then 863 into 864-865"
  - claim: "Its fees must be a finite figure, and may stand at nought but not below"
    source: "`nexus/core/capital_controller/capital_controller.py` 867 into 868-869, then 871 into 872-873"
  - claim: "All four are weighed before the lock is taken"
    source: "`nexus/core/capital_controller/capital_controller.py` 875, standing after 873"
  - claim: "An order the book does not hold is answered as a failure rather than raised"
    source: "`nexus/core/capital_controller/capital_controller.py` 876 into 878-879"
  - claim: "So is an order in any state but working, and a notional larger than what the order has left"
    source: "`nexus/core/capital_controller/capital_controller.py` 888-889, or 892-893"
  - claim: "An order is taken out of the book where nothing remains of it or the fill ends it, and put back otherwise"
    source: "`nexus/core/capital_controller/capital_controller.py` 950 into 951, or 952-953"
  - claim: "An ending fill leaving something outstanding and a residual below nought is answered as a failure"
    source: "`nexus/core/capital_controller/capital_controller.py` 940 into 941"
  - claim: "A fill that got through answers a success carrying nothing else"
    source: "`nexus/core/capital_controller/capital_controller.py` 972"
  - claim: "A working total left within a hair of nought is snapped to nought"
    source: "`nexus/core/capital_controller/capital_controller.py` 969 into 970"
---
# What a fill against a reservation refuses

A fill reported against money set aside is weighed twice over: once on its own figures, which raises, and once against the order it names, which answers.

## The four figures

The notional must be a finite figure standing above nought. The fees must be a finite figure too, and may stand at nought but not below.

So a fill of nothing is refused and a fill with no fee is allowed, and all four are weighed before the lock is taken — a badly reported fill holds the book up for nobody.

## What answers instead of raising

An order the book does not hold. An order in any state but working. A notional larger than what the order has left.

Each is answered as a failure carrying a reason, not raised. The line is drawn between a figure that cannot be read and a figure that reads fine but does not fit what the book holds.

## What the book keeps

An order is taken out of the book where nothing remains of it or the fill ends it, and put back otherwise. So the book holds only orders with something still outstanding.

## The residual that cannot be released

An ending fill that leaves something outstanding, where the residual to release stands below nought, is answered as a failure. A fill that got through answers a success carrying nothing else.

## The hair either side of nought

A working total left within a hair of nought is snapped to nought. The arithmetic can leave a residue far smaller than any trade, and the sweep keeps that residue from standing as money at work forever.

## Related

- [What becomes of money set aside](what-becomes-of-money-set-aside.md)
- [What a strategy's budget is worked out from](what-a-strategys-budget-is-worked-out-from.md)
