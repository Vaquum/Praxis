---
row: N7-11
baseline: 49aa659
created: 2026-10-27 08:14 UTC
modified: 2026-10-27 08:14 UTC
evidence:
  - claim: "An entry asking in money has its sum written as that amount, with no price read into the working out, though the request's own price is carried along"
    source: "`praxis/launcher.py` 1174-1175 returning at 1178-1192, the price carried at 1191"
  - claim: "One asking in size takes a price from the request, or from the last close where the request names none"
    source: "`praxis/launcher.py` 1194-1197, the source of that close wired at 4173-4174"
  - claim: "A size-asking request that names no price and gets no close is not built at all"
    source: "`praxis/launcher.py` 1199-1207, reached only past the money branch at 1174"
  - claim: "The size is then fitted by the venue, rounded down to the step it keeps, and the sum is that fitted size at the price"
    source: "`praxis/launcher.py` 1221-1232 into 1248-1249 and 1251, the rounding at `praxis/infrastructure/binance_adapter.py` 1392"
  - claim: "The fitting refuses a size that falls under the venue's smallest once rounded, and an order worth less than its smallest value, either of which ends the building"
    source: "`praxis/infrastructure/binance_adapter.py` 1398-1406 and 1408-1420, into `praxis/launcher.py` 1234-1246"
  - claim: "Where no rules are held for that symbol the fitting passes the size through unweighed"
    source: "`praxis/infrastructure/binance_adapter.py` 1378-1381"
  - claim: "The one symbol an entry is built against is loaded before a host finishes starting, and a failure to load ends the start, so that unweighed road is not one a strategy reaches"
    source: "`praxis/launcher.py` 2961 over the symbol standing at 194, loaded at `praxis/trading.py` 554-562 and failing the start at 525-528"
  - claim: "On the weighed road a sum of nought is below any smallest value above nought, so the fitting refuses it and no request is built for the stage to read"
    source: "`praxis/infrastructure/binance_adapter.py` 1408-1420 into `praxis/launcher.py` 1234-1246"
  - claim: "The smallest value is copied from whatever the venue reports, with nothing holding it above nought"
    source: "`praxis/infrastructure/binance_adapter.py` 2220-2229"
  - claim: "Any finite close is answered with, nought among them"
    source: "`praxis/arrow_price_store.py` 147-159"
  - claim: "A strategy's own request must carry exactly one of a size and an amount of money, each held above nought where it is the one carried"
    source: "`nexus/strategy/action.py` 179-193, the holdings at 85-89 and 93-99"
---
# What an entry's sum is worked out from

An entry's sum is either the amount of money it asked for, or the size it asked for at a price — and which of those depends on how the strategy asked.

## Asking in money

The sum is written as that amount and no price is read into the working out, though whatever price the request named is carried along for the checks to see.

## Asking in size

A price comes from the request, or from the last close where it names none; a request that gets neither is not built at all.

The size is then fitted by the venue, rounded down to the step it keeps, and the sum is that fitted size at the price — so it can come out below what the strategy asked for.

## What the fitting turns away

A size that falls under the venue's smallest once rounded is refused, as is an order worth less than the venue's smallest value. Either ends the building. Where no rules are held for that symbol, the fitting passes the size through untouched.

## Whether a sum can reach nought

A strategy carries exactly one of a size and an amount of money, held above nought either way. The price is where nought could get in: any finite close is answered with, nought among them. The unweighed road would carry that through, but the symbol an entry is built against is loaded before a host finishes starting, and a failure to load ends the start.

On the weighed road a sum of nought falls below any smallest value above nought, so the fitting refuses it and [the stage](what-the-first-stage-weighs-before-the-mode.md) is never asked — the smallest value being copied from whatever the venue reports, with nothing holding it above nought.

## Related

- [What settles a request before the first stage](what-settles-a-request-before-the-first-stage.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)

---

Created 2026-10-27 08:14 UTC · Last modified 2026-10-27 08:14 UTC
