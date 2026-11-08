---
row: P74-04
baseline: 49aa659
created: 2026-11-13 05:30 UTC
modified: 2026-11-13 06:00 UTC
evidence:
  - claim: "The interface declares twenty-one things, each body being one placeholder"
    source: "`venue_adapter.py` 754, 767, 780, 848, 894, 920, 946, 972, 998, 1016, 1034, 1064, 1088, 1104, 1123, 1133, 1148, 1158, 1176, 1189 and 1204"
  - claim: "It is marked so that a thing can be asked at runtime whether it answers to the interface"
    source: "`venue_adapter.py` 731"
  - claim: "Three name an account's credentials: registering a set, taking one back, and asking what the venue says a set may do"
    source: "`venue_adapter.py` 754, 767 and 780"
  - claim: "One names the bringing of a command's quantity to the venue's rules, and its declared answer is the record carrying either a snapped quantity or a reason"
    source: "`venue_adapter.py` 848, the answer's shape weighed at 399-406"
  - claim: "Three name a sending: an order, a cancel, and a cancel of a linked pair"
    source: "`venue_adapter.py` 894, 920 and 946"
  - claim: "Nine name an asking: an order, a linked pair, the open orders, a balance, the trades, the money moved, the venue's description of itself, a book, and the venue's clock"
    source: "`venue_adapter.py` 972, 998, 1016, 1034, 1064, 1088, 1104, 1123 and 1133"
  - claim: "Two name the venue's trading rules, one fetching and one offering what was fetched"
    source: "`venue_adapter.py` 1158 and 1176"
  - claim: "The last three name reading the venue's health, turning a venue's frame into a report, and closing whatever is open"
    source: "`venue_adapter.py` 1148, 1189 and 1204"
---
# What a venue must offer

Praxis describes what it needs of a venue in one interface, and that interface declares twenty-one things.

## It declares and does not do

Each of the twenty-one has a body of one placeholder. The file says what a venue must answer to, what it must be given and what it must give back, and nothing at all about how any venue does it.

It is marked so that a thing can be asked at runtime whether it answers to the interface, rather than only being checked where it is written.

## What the twenty-one are named for

Three name an account's credentials: registering a set, taking one back, and asking what the venue says a set may do.

One names the bringing of a command's quantity to the venue's rules. Its declared answer is the record carrying either a snapped quantity or a reason for refusal.

Three name a sending: an order, a cancel, and a cancel of a linked pair.

Nine name an asking: an order, a linked pair, the open orders, a balance, the trades, the money moved in or out, the venue's description of itself, a book, and the venue's clock.

Two name the venue's trading rules — one fetching, one offering what was fetched.

The last three name reading the venue's health, turning a venue's frame into a report, and closing whatever is open.

## Why "named for"

The grouping above is read off the names and the declared answers. What any of them does, and whether an asking leaves the venue as it was, is settled where a venue is implemented.

## Related

- [What a venue is](what-a-venue-is.md)
- [What an execution report is held to](what-an-execution-report-is-held-to.md)
