---
row: P2-46
baseline: 49aa659
created: 2026-10-12 05:40 UTC
modified: 2026-10-12 06:23 UTC
evidence:
  - claim: "The figures are asked of the venue once per account as it starts, for the symbols known then"
    source: "`trading.py` 554-562, the store filled only at `binance_adapter.py` 2135-2138"
  - claim: "An amount is cut down to the step before it is weighed at all"
    source: "`binance_adapter.py` 1518 into 1314-1317"
  - claim: "So the step test the cut amount meets cannot refuse it"
    source: "`binance_adapter.py` 1194-1198, reached only past the cutting at 1518"
  - claim: "The cut amount must fall between the smallest and the largest size"
    source: "`binance_adapter.py` 1200-1210"
  - claim: "A price must sit on the tick, and price times amount clear the smallest value, for an order carrying a price that is not a market order"
    source: "`binance_adapter.py` 1212-1227"
  - claim: "A trigger price must sit on the tick as well"
    source: "`binance_adapter.py` 1229-1236"
  - claim: "The weighing happens on the way to the venue, against the whole amount"
    source: "`binance_adapter.py` 1520"
  - claim: "A market buy sized in money is sent before any of it"
    source: "`binance_adapter.py` 1468 into 1505-1512, returning ahead of 1518"
  - claim: "A symbol with nothing kept for it is logged and passed over, the order going out unweighed"
    source: "`binance_adapter.py` 1188-1192, the cutting passed over the same way at 1315-1316"
---
# The sizes a venue trades in

A venue trades only in certain sizes: an amount has to sit on a step and fall between a smallest and a largest, and an order carrying a price has to rest on a price tick and be worth at least a smallest value. Praxis keeps those figures for each symbol and weighs an order against them on its way out.

## Where the figures come from

They are asked of the venue once for each account as it starts, covering the symbols that account is known to trade by then. Nothing asks again while the host runs, so a symbol that turns up later has none.

## What is weighed

The amount is first cut down to the step — so an amount off the step is reduced rather than refused, and the step test it then meets can never turn it away. What is weighed is the cut amount, whole, including the part of a [part-shown order](part-shown-orders.md) the venue never displays.

That amount is refused if it falls under the smallest size or over the largest. An order carrying a price that is not a market order is refused as well if the price is off the tick, or if price times amount comes under the smallest value; a trigger price off the tick goes the same way. Each refusal is [put down to Praxis](who-refused-a-send.md) rather than to the venue, and it stops the send.

## What goes out unweighed

A market buy sized in money, rather than in the asset, is sent before any of this is reached.

So is an order for a symbol with no figures kept: a line is logged and it goes out as it stands, uncut and unweighed, whatever its size or price.

## Related

- [Part-shown orders](part-shown-orders.md)
- [When a price change places nothing](when-a-price-change-places-nothing.md)
- [What a venue is](what-a-venue-is.md)

---

Created 2026-10-12 05:40 UTC · Last modified 2026-10-12 06:23 UTC
