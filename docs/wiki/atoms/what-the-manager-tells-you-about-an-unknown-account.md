---
row: P133-01
baseline: 49aa659
created: 2026-11-09 10:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Asking which symbols an account is active in refuses where the account is not registered"
    source: "`execution_manager.py` 866, then 867 into 868-869"
  - claim: "Asking for its open orders refuses the same way"
    source: "`execution_manager.py` 918, then 919 into 920-921"
  - claim: "Asking which command fragments it owns refuses the same way, testing for the account rather than reading it"
    source: "`execution_manager.py` 947 into 948-949, against 951-955"
  - claim: "Asking which recovery flattens it posted answers with nothing instead"
    source: "`execution_manager.py` 898, then 899 into 900, against 902"
  - claim: "Asking which of its commands are in flight answers with nothing"
    source: "`execution_manager.py` 979, then 980 into 981"
  - claim: "Asking which are amendable answers with nothing"
    source: "`execution_manager.py` 1024, then 1025 into 1026"
  - claim: "Asking for the published amendable set answers with nothing by one lookup that reads a standing empty where no account is held"
    source: "`execution_manager.py` 1087, the set it reads written after each pass at 3956-3958 and dropped at 2957"
  - claim: "The symbols are gathered from the open orders and from a copy of the positions, and the open orders handed back as a copy of each"
    source: "`execution_manager.py` 871, then 872-873, then 874-875, then 876, against 923"
---
# What the manager tells you about an unknown account

Seven ways of asking the manager about one account divide on what an unregistered account gets: three refuse and four answer with nothing.

## The three that refuse

Which symbols the account is active in. What its open orders are. Which command fragments it owns.

Each reads the account first and raises where it finds none — except the fragments, which test for the account rather than read it, and so raise without ever holding the thing they would have read.

## The four that answer with nothing

Which recovery flattens it posted. Which of its commands are in flight. Which are amendable. And the published amendable set, which answers by one lookup that reads a standing empty where no account is held.

## What the division costs a caller

A caller that asks all seven about an account that has gone must be ready for both — a refusal from three of them and an empty answer from four — and the two are indistinguishable from the account's own point of view.

So an account unregistered between two asks gives a refusal on one road and silence on the next, with nothing in either answer saying the account went.

## What the gathering copies

The symbols are gathered from the open orders and from a copy of the positions. The open orders are handed back as a copy of each order, where the symbols are handed back as a set built here.

## Related

- [What an account is](what-an-account-is.md)
- [Which commands count as amendable](which-commands-count-as-amendable.md)
- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)
