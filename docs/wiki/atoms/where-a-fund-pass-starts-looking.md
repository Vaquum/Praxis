---
row: P104-01
baseline: 49aa659
created: 2026-11-14 05:30 UTC
modified: 2026-11-14 18:00 UTC
evidence:
  - claim: "The window starts at the cursor less an overlap, or at the cutover where no cursor is held"
    source: "`praxis/trading.py` 1138-1139, then 1140"
  - claim: "A start that would fall before the cutover is pulled forward to it"
    source: "`praxis/trading.py` 1142 into 1143"
  - claim: "A venue that refuses the asking ends the pass with a warning"
    source: "`praxis/trading.py` 1145-1148 into 1149, then 1154"
  - claim: "The cutover is seeded from the moment the account was registered, as the spine recorded it"
    source: "`praxis/trading.py` 1103 into 1104 into 1105, then 1111-1113"
  - claim: "Where the spine holds no such registering, the clock at seeding time stands in"
    source: "`praxis/trading.py` 1112"
  - claim: "The cursor is seeded from the latest fund movement the spine holds, and left unset where it holds none"
    source: "`praxis/trading.py` 1106-1109, then 1115 into 1116"
---
# Where a fund pass starts looking

Each pass over an account's money movements asks the venue for a window, and the window's start is chosen from two remembered moments.

## The two moments

A cursor, which is how far the last pass got. A cutover, which is as far back as this account's history is ever worth asking about.

The window starts at the cursor less an overlap, or at the cutover where no cursor is held. A start that would fall before the cutover is pulled forward to it.

## Why the overlap

Asking from slightly before where the last pass finished means the same movements are fetched again. That is deliberate: a movement recorded at the boundary is asked for twice rather than risked once.

The cutover is the floor that stops the overlap reaching into history this account should not be asked about.

## Where the two come from

The cutover is seeded from the moment the account was registered, as the spine recorded it. Where the spine holds no such registering, the clock at seeding time stands in — so an account with no recorded registering is treated as beginning now.

The cursor is seeded from the latest fund movement the spine holds, and left unset where it holds none.

## The pass that asks nothing more

A venue that refuses the asking ends the pass with a warning, leaving both moments where they were.

## Related

- [What holds a fund cursor back](what-holds-a-fund-cursor-back.md)
