---
row: P3-22
baseline: 49aa659
created: 2026-10-01 09:10 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A host is told which ways of working it may drive, as a list of names in its settings"
    source: "`launcher.py` 851 and 856-862"
  - claim: "Work naming one outside the list is refused rather than queued"
    source: "`execution_manager.py` 3481-3495"
  - claim: "Unset or empty leaves the plain single order alone"
    source: "`launcher.py` 851-853"
  - claim: "The plain single order is in the list however the list is written"
    source: "`launcher.py` 855, `trading_config.py` 176-177, `execution_manager.py` 681-685"
  - claim: "A name that is not a known way of working stops the host as the settings are read"
    source: "`launcher.py` 861-869, read at 4969-4975 before the host is built at 4984-5000, and exited on at 5003-5008"
  - claim: "Binsim takes market orders only"
    source: "`server.py` 88, tested and refused at 381-385"
  - claim: "Three ways of working rest something other than a market order"
    source: "`live_only_modes.py` 21-27 and 41, with the protective pair at `execution_manager.py` 4968-4978, the part-shown order at 5322-5331 and the ladder at 6209-6218"
  - claim: "Naming one of the three while binsim is the venue stops the host there too"
    source: "`launcher.py` 871-876, reached from 4969-4975 before the host is built at 4984-5000"
  - claim: "Binsim is the venue only in paper mode and only where an address for it is given"
    source: "`launcher.py` 4971-4974 and 4715-4719"
  - claim: "Paper with no such address goes to the test venue instead, and the guard holds back none of the three there"
    source: "`launcher.py` 4717-4721 leaving 4971-4974 false, so 871 never fires"
  - claim: "A live host given that address is refused outright"
    source: "`launcher.py` 4723-4726"
  - claim: "The guard reads the settings, so a host built in code never passes through it"
    source: "`launcher.py` 4969-4975 against the direct build at `run_replay.py` 121-144 and `trading.py` 212-231"
---
# Ways of working a host may drive

A host is told which **ways of working** it may drive, as a list of names in its settings. Work naming one outside the list is [turned away](what-turns-work-away.md) rather than queued.

Leave the list unset or empty and the plain single order is left alone. It is in the list however the list is written — added whether or not anyone named it, and added again twice over further down.

A name that is not a known way of working stops the host as the settings are read, rather than failing the first request to use it.

## Three the simulator cannot take

[Binsim](binsim.md) takes market orders only. Three ways of working rest something else at the venue — [a protective pair](protection.md), [an order part-shown to the market](part-shown-orders.md), and [a ladder](orders-at-several-prices.md) — so naming one of those while binsim is the venue stops the host there too, instead of leaving it to be refused order by order.

## Which venue counts

Where a host starts from its settings, binsim is the venue only in paper mode and only where an address for binsim is given. Paper with no such address goes to the test venue instead, and this guard holds back none of the three there.

A live host given that address is refused outright, so that pairing cannot be started from settings at all.

The guard sits in that reading. A host built in code, handed [its venue](what-a-venue-is.md) directly, never passes through it.

## Related

- [Binsim](binsim.md)
- [What turns work away](what-turns-work-away.md)
