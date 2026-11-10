---
row: P112-02
baseline: 49aa659
created: 2026-11-09 08:37 UTC
modified: 2026-11-09 09:06 UTC
evidence:
  - claim: "Against the simulator the asking answers with nothing at all, before any check is made"
    source: "`binance_adapter.py` 1954 into 1955"
  - claim: "Both ends of the window are weighed for carrying a zone, and each is sent as whole milliseconds only where it was given"
    source: "`binance_adapter.py` 1957, and 1958, then 1962 into 1963, and 1965 into 1966"
  - claim: "Money in and money out are asked after separately, their answers joined afterwards, and the whole handed back in order of the moment each movement happened"
    source: "`binance_adapter.py` 1968-1970, then 1971-1973, joined at 1975, then 1985"
  - claim: "The paging walks from an offset that starts at nothing, each page asked with the window's parameters and that offset"
    source: "`binance_adapter.py` 2012-2013, then 2015, then 2016-2020, then 2021"
  - claim: "Every page's rows are added to one list"
    source: "`binance_adapter.py` 2022"
  - claim: "A page shorter than the limit ends the walk and answers everything gathered"
    source: "`binance_adapter.py` 2024 into 2025"
  - claim: "Otherwise the offset moves on by a whole page and the walk goes round"
    source: "`binance_adapter.py` 2027"
---
# How fund history is paged

Money moved in and out is asked after in pages, and the walk ends when a page comes back short.

## The simulator

Against it the asking answers with nothing at all, before any check is made. So no window is weighed and no request is sent, and a caller cannot tell an empty history from a simulator that serves none.

## The window

Both ends are weighed for carrying a zone. Each is sent as whole milliseconds, and only where it was given — so a window open at one end is sent with that end left out rather than filled in.

## The two askings

Money in and money out are asked after separately, and their answers joined afterwards. So each gets its own paging, and a failure part-way through the second leaves the first's pages fetched and discarded. What survives both is handed back in order of the moment each movement happened, so the two kinds arrive interleaved rather than one after the other.

## The walk

From an offset that starts at nothing. Each page is asked with the window's parameters and that offset, and every page's rows are added to one list.

A page shorter than the limit ends the walk and answers everything gathered. Otherwise the offset moves on by a whole page and the walk goes round.

So a history whose length is an exact multiple of the page size costs one extra request, which comes back empty and ends the walk. There is no count from the venue to check against — the short page is the only signal.

## Related

- [What the four asking calls share](what-the-four-asking-calls-share.md)
