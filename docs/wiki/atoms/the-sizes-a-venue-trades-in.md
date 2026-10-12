---
row: P2-46
baseline: 49aa659
created: 2026-10-12 05:40 UTC
modified: 2026-10-12 05:40 UTC
evidence:
  - claim: "The figures are asked of the venue once per account as it starts, for the symbols known then"
    source: "`trading.py` 554-562, the store filled only at `binance_adapter.py` 2135-2138"
  - claim: "An amount must sit on the step and fall between the smallest and the largest size"
    source: "`binance_adapter.py` 1194-1210"
  - claim: "A price must sit on the tick, and price times amount must clear the smallest value"
    source: "`binance_adapter.py` 1212-1227"
  - claim: "A trigger price must sit on the tick as well"
    source: "`binance_adapter.py` 1229-1236"
  - claim: "The weighing happens on the way to the venue, against the whole amount"
    source: "`binance_adapter.py` 1520"
  - claim: "A symbol with nothing loaded is logged and passed over, the order going out unweighed"
    source: "`binance_adapter.py` 1188-1192"
---
# The sizes a venue trades in

A venue trades only in certain sizes: an amount has to sit on a step and fall between a smallest and a largest, and an order carrying a price has to rest on a price tick and be worth at least a smallest value. Praxis keeps those figures for each symbol and weighs an order against them on its way out.

## Where the figures come from

They are asked of the venue once for each account as it starts, covering the symbols that account is known to trade by then. Nothing asks again while the host runs, so a symbol that turns up later has none.

## What is weighed

The whole amount goes to the weighing, including the part of a [part-shown order](part-shown-orders.md) the venue never displays. An amount off the step, under the smallest size or over the largest is refused, as is a price off the tick or an order worth too little, and a trigger price off the tick with them. Each refusal is [put down to Praxis](who-refused-a-send.md) rather than to the venue, and it stops the send.

## When nothing is weighed

A symbol with no figures kept for it is passed over: a line is logged and the order goes out as it stands, whatever its size or price.

## Related

- [Part-shown orders](part-shown-orders.md)
- [When a price change places nothing](when-a-price-change-places-nothing.md)
- [What a venue is](what-a-venue-is.md)

---

Created 2026-10-12 05:40 UTC · Last modified 2026-10-12 05:40 UTC
