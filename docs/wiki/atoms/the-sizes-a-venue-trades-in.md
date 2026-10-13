---
row: P2-46
baseline: 49aa659
created: 2026-10-12 05:40 UTC
modified: 2026-10-12 10:12 UTC
evidence:
  - claim: "The figures are asked for as each account starts, and of the venue only for a symbol nothing has asked about yet"
    source: "`trading.py` 554-562, the store read first at `binance_adapter.py` 2136 and filled at 2138"
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
  - claim: "A replay's venue weighs none of it, refusing only an amount that comes out at nothing or less"
    source: "`replay_venue_adapter.py` 455-476"
---
# The sizes a venue trades in

A venue trades only in certain sizes: amounts come in steps between a smallest and a largest, a price rests on a tick, and an order must be worth a smallest value. Praxis keeps those figures per symbol, cuts an amount to the step, and weighs what is left on the way out.

## Where the figures come from

Each account asks as it starts, for the symbols it is known to trade by then, and the venue itself is asked only about a symbol nothing has asked about yet. Nothing asks again later, so a symbol turning up then has none.

## What is weighed

The amount is first cut down to the step, so one off the step is reduced rather than refused and the step test it meets after that can never turn it away. What is weighed is the cut amount, whole, including the part of a [part-shown order](part-shown-orders.md) the venue never displays.

It is refused if it falls under the smallest size or over the largest. An order carrying a price that is not a market order is refused too if the price is off the tick, or price times amount comes under the smallest value; a trigger price off the tick goes the same way. Each refusal is [put down to Praxis](who-refused-a-send.md) rather than the venue, and stops the send.

## What goes out unweighed

A market buy sized in money, rather than in the asset, is sent before any of this. So is an order whose symbol has no figures kept: a line is logged and it goes out uncut, whatever its size. None of it is weighed on the way to [a replay's venue](the-replay-venue.md), which refuses only an amount coming out at nothing or less.

## Related

- [Part-shown orders](part-shown-orders.md)
- [When a price change leaves no new order](when-a-price-change-places-nothing.md)
- [What a venue is](what-a-venue-is.md)

---

Created 2026-10-12 05:40 UTC · Last modified 2026-10-12 10:12 UTC
