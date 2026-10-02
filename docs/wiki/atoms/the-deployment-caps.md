---
row: P4-27
baseline: 49aa659
created: 2026-10-02 09:11 UTC
modified: 2026-10-02 09:19 UTC
evidence:
  - claim: "Six ceilings are read from the settings: an order's size in money, a position's size, how often orders may go out, how wide the book may be, how old the book's figures may be, and how far the price worked out of the book may sit from the one expected"
    source: "`launcher.py` 760-767"
  - claim: "The last of them is weighed before a send, against a price worked out of the book"
    source: "`execution_manager.py` 4064-4098"
  - claim: "Four are refused if given anything but a positive finite decimal"
    source: "`launcher.py` 663-678, called at 761, 762, 764 and 766"
  - claim: "The rate and the book's age are refused if given anything but a positive whole number"
    source: "`launcher.py` 694-707, called at 763 and 765"
  - claim: "A book age that does not exceed the two seconds between polls refuses the start later, as an account's runtime is put together"
    source: "`launcher.py` 338-349 against the interval at 197, reached from 4097-4099"
  - claim: "An empty setting counts as unset for all six"
    source: "`launcher.py` 665-666 and 696-697"
  - claim: "On paper an unset cap is carried as nothing and the start goes on"
    source: "`launcher.py` 769-770"
  - claim: "On live every unset cap is gathered and named together, and the start refused"
    source: "`launcher.py` 772-786"
---
# The deployment caps

A host's **caps** are six ceilings [its settings](the-settings-a-host-is-given.md) can put on what it may do: the money an order may be worth, the size a position may reach, how often orders may go out, how wide [the book](the-order-book.md) may be, how old the book's figures may be, and how far the price worked out of [the book](the-order-book.md) may sit from the one expected.

## What each must look like

Four of them take a positive finite decimal, and anything else refuses the start. The rate and the book's age take a positive whole number instead — so a rate of one and a half is refused where a spread of one and a half is taken.

This holds in either mode. What paper makes optional is the setting, rather than the shape of what is in it. An empty setting counts as unset throughout, so on paper it is taken rather than refused.

## When one is missing

On paper a cap left unset is carried as nothing, and the start goes on with no ceiling of that kind.

On live every unset cap is gathered up and named together, and the start refused. One message lists all of them, so a deployment short of three learns about three.

## One checked twice

The book's age is parsed as a positive whole number here, and weighed again later, as an account's runtime is put together: it must exceed the two seconds between polls. So one second and two seconds both pass the first test and refuse the start at the second.

## Where the last one is weighed

The slippage ceiling is weighed before a send, against [a price worked out of the book](how-the-likely-price-is-checked.md) rather than against anything that has traded.

## Related

- [Which settings are refused](which-settings-are-refused.md)
- [The settings a host is given](the-settings-a-host-is-given.md)
