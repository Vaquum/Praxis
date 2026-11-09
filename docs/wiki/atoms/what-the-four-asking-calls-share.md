---
row: P112-01
baseline: 49aa659
created: 2026-11-09 08:37 UTC
modified: 2026-11-09 08:37 UTC
evidence:
  - claim: "All four refuse where neither name was given, three of them with the same wording"
    source: "`binance_adapter.py` 1676 into 1677-1678, or 1719 into 1720-1721, or 1761 into 1762-1763, or 1797 into 1798-1799"
  - claim: "Three begin their parameters with the symbol, and the one asking after a list begins with none"
    source: "`binance_adapter.py` 1680, and 1723, and 1765, against 1801"
  - claim: "Both order-level calls name the venue's own identifier one way and the caller's another"
    source: "`binance_adapter.py` 1682 into 1683, and 1767 into 1768, then 1685 into 1686, and 1770 into 1771"
  - claim: "Both list-level calls name the venue's own identifier alike"
    source: "`binance_adapter.py` 1725 into 1726, and 1803 into 1804"
  - claim: "The two list-level calls name the caller's identifier differently from each other"
    source: "`binance_adapter.py` 1728 into 1729, against 1806 into 1807"
  - claim: "Each sends through the signed road and reads what comes back by its own parsing"
    source: "`binance_adapter.py` 1688 into 1689-1692, or 1773 into 1774, or 1809 into 1810, or 1731"
---
# What the four asking calls share

Four calls ask the venue about an order or cancel one, and they are built to the same shape with two places where they part.

## What all four do

Refuse where neither identifier was given — three of them with the same wording. Then build parameters, send through the signed road, and read what comes back by their own parsing.

So none of them asks the venue to find an order by anything but a name, and none of them accepts being given no name at all.

## The symbol

Three begin their parameters with the symbol. The one asking after an order list begins with none.

So that call asks the venue about a list without saying which market it belongs to, where the other three always say.

## The names they use

Both order-level calls name the venue's own identifier one way and the caller's another, and they agree with each other.

Both list-level calls name the venue's own identifier alike. They name the caller's identifier differently from each other.

So of the four, one pair agrees on both names and the other pair agrees on one. A caller's own name for an order list is sent under one key when cancelling and another when asking — and only the venue can say whether both are right.

## Related

- [What signing a request adds](what-signing-a-request-adds.md)
