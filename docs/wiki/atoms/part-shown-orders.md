---
row: P2-22
baseline: 49aa659
created: 2026-09-28 07:18 UTC
modified: 2026-09-28 08:52 UTC
evidence:
  - claim: "The settings carry a shown amount and a price to rest at, both above zero"
    source: "`iceberg_params.py` 30-31, required positive at 37-41"
  - claim: "The shown amount cannot be above the whole"
    source: "`validate_trade_command.py` 353-355"
  - claim: "Praxis refuses it unless it clears the venue's smallest size, step and value on its own"
    source: "`validate_trade_command.py` 429-432"
  - claim: "One limit order for the whole amount is sent, at that price, with the shown amount named on it"
    source: "`execution_manager.py` 5322-5331, the figure chosen at 5296"
  - claim: "Where the shown amount equals the whole, nothing is named"
    source: "`execution_manager.py` 5296"
  - claim: "The shown amount reaches the venue as a field of its own"
    source: "`binance_adapter.py` 825"
  - claim: "Naming one also sets how long the order rests"
    source: "`binance_adapter.py` 826"
  - claim: "The builder that carries it refuses it on anything but a limit order"
    source: "`binance_adapter.py` 771-772"
  - claim: "Two kinds of send reach the venue without passing that builder"
    source: "either `binance_adapter.py` 1505-1512 or 1522-1536, against the ordinary path at 1542-1548"
  - claim: "That builder refuses again where the shown amount is not below the whole"
    source: "`binance_adapter.py` 821-823"
  - claim: "The sending path does not send successive portions, nor wait for one to fill before the next"
    source: "`execution_manager.py` 5322-5404, which sends once and goes on to report"
  - claim: "Changing the order gives it a new name and cancels the old"
    source: "`execution_manager.py` 8695-8716, the replacement sent at 10324-10352"
---
# Part-shown orders

A **part-shown order** is a single order for the whole amount, resting at a named price, of which the venue displays only part at a time. Praxis sends one order, not several: the whole amount goes in one go, at the given price, with the amount to show named alongside it.

## What must be given

The settings carry how much to show at a time and the price the order rests at. Both must be above zero.

The shown amount cannot be larger than the whole. Praxis also refuses it unless it clears the venue's smallest allowed size on its own, sits on the venue's step, and is worth enough by itself.

## When nothing is hidden

Where the amount to show equals the whole, nothing is held back and no shown amount is named. What goes out is a plain limit order, so asking to show everything is not an error.

## What Praxis does and does not do

The sending path sends that one order and goes on to report it. It does not send portion after portion, nor wait for one to fill before the next.

Praxis hands the figure over and does nothing further with it. What the venue displays, and when it shows the next part, is past what this code can show.

Naming a shown amount also settles how long the order rests. The builder carrying it refuses the amount on anything but a limit order, and refuses again where it is not below the whole. Two kinds of send miss that builder entirely: a market order sized in money, and a linked pair.

Left alone, the order keeps one name and one record. [Changing it](where-the-order-type-decides.md) does not: the old order is cancelled and the replacement gets a name of its own.

## Related

- [Order types](order-types.md)
- [What a fill is](what-a-fill-is.md)
