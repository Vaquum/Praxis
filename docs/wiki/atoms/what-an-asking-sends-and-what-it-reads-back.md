---
row: P113-02
baseline: 49aa659
created: 2026-11-14 10:00 UTC
modified: 2026-11-14 10:00 UTC
evidence:
  - claim: "An asking after no assets at all answers with nothing, before the venue is troubled"
    source: "`binance_adapter.py` 1851 into 1852"
  - claim: "Otherwise the whole account is asked for with no parameters, and the asked-for assets are picked out of what comes back"
    source: "`binance_adapter.py` 1854, then 1856-1858"
  - claim: "An asking after trades refuses a starting name together with either end of a window"
    source: "`binance_adapter.py` 1896 into 1897-1898"
  - claim: "Both ends of that window are weighed for carrying a zone before anything is built"
    source: "`binance_adapter.py` 1900, and 1901"
  - claim: "The symbol always goes, and the starting name, each end and a limit go only where given"
    source: "`binance_adapter.py` 1903, then 1905 into 1906, and 1908 into 1909, and 1911 into 1912, and 1914 into 1915"
  - claim: "Every trade that comes back is read by the one parsing"
    source: "`binance_adapter.py` 1917, then 1919"
  - claim: "Money in and money out are read by two parsings that take the same two fields under the same two names"
    source: "`binance_adapter.py` 2033-2035, and 2053-2055"
---
# What an asking sends and what it reads back

Two askings about an account send very different things: one sends nothing and filters the answer, the other builds parameters and trusts the answer.

## The asking that sends nothing

An asking after no assets at all answers with nothing, before the venue is troubled. Otherwise the whole account is asked for with no parameters, and the asked-for assets are picked out of what comes back.

So the filtering happens here rather than at the venue, and asking after one asset costs the same request as asking after twenty.

## The asking that builds

An asking after trades refuses a starting name together with either end of a window — the venue takes one or the other, not both.

Both ends of that window are weighed for carrying a zone before anything is built. The symbol always goes; the starting name, each end and a limit go only where given.

So the request carries exactly what the caller asked for, and the answer is read as it comes.

## The two parsings that match

Money in and money out are read by two parsings that take the same two fields under the same two names. The two kinds of movement arrive in the same shape and are read by separate routines that agree.

## Related

- [How fund history is paged](how-fund-history-is-paged.md)
- [When a request is signed afresh](when-a-request-is-signed-afresh.md)
