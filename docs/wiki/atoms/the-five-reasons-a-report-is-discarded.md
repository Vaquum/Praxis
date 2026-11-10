---
row: P101-01
baseline: 49aa659
created: 2026-11-09 07:57 UTC
modified: 2026-11-09 08:20 UTC
evidence:
  - claim: "A payload whose kind is anything but an execution report is dropped without a word"
    source: "`praxis/trading.py` 1708 into 1709"
  - claim: "A venue that is not the Binance one drops it without a word too"
    source: "`praxis/trading.py` 1711 into 1712"
  - claim: "A parse that fails on any of four named kinds of failure is reported and dropped"
    source: "`praxis/trading.py` 1714-1715 into 1716, then 1725"
  - claim: "An account the manager holds no state for is dropped with a warning"
    source: "`praxis/trading.py` 1726 into 1727-1728, then 1729"
  - claim: "A leg's name is turned into its parent's, falling back to the name itself"
    source: "`praxis/trading.py` 1731-1733, reached from 570 into 572-573"
  - claim: "The order is looked for among the live ones and then among the closed, with which one it came from remembered"
    source: "`praxis/trading.py` 1735-1736, then 1737 into 1738-1739"
  - claim: "An order in neither book is noted at the quietest level the log has and dropped"
    source: "`praxis/trading.py` 1740, then 1744"
---
# The five reasons a report is discarded

A report arriving on the venue's socket can be discarded five ways, and how loudly says how surprising it is.

## The two that say nothing

A payload whose kind is anything but an execution report. A venue that is not the Binance one. Both are dropped without a word, because both are ordinary — the socket carries other kinds, and another venue was never going to parse this.

## The two that complain

A parse that fails on any of four named kinds of failure is reported and dropped. An account the manager holds no state for is dropped with a warning.

These are the surprising ones: a payload that said it was an execution report and would not parse, and a report for an account this side does not know.

## The one in between

An order in neither book is noted at the quietest level the log has and dropped. It is neither ordinary nor alarming: the order may have been closed and swept long before, so the note is there to be found rather than to be seen.

## Finding the order at all

A leg's name is turned into its parent's, falling back to the name itself — so an order that is nobody's leg travels the same road. The order is then looked for among the live ones and then among the closed, with which book it came from remembered.

## Related

- [What a report becomes](what-a-report-becomes.md)
