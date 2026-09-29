---
row: P3-14
baseline: 49aa659
created: 2026-09-29 06:12 UTC
modified: 2026-09-29 08:01 UTC
evidence:
  - claim: "A name is built from a two-letter mark, part of the request's name, and a number"
    source: "`generate_client_order_id.py` 154"
  - claim: "Each way of working has its own two letters"
    source: "`generate_client_order_id.py` 23-31, chosen at 149"
  - claim: "A way of working with no letters set is refused"
    source: "`generate_client_order_id.py` 135-137"
  - claim: "The part taken is the request's name with hyphens dropped, cut to sixteen"
    source: "`generate_client_order_id.py` 57, used at 150"
  - claim: "The number must sit between nothing and 999"
    source: "`generate_client_order_id.py` 139-141 with the limit at 22"
  - claim: "The number behind the extra mark must be nothing or more"
    source: "`generate_client_order_id.py` 143-145"
  - claim: "A request name with fewer than sixteen characters after its hyphens is refused"
    source: "`generate_client_order_id.py` 105-110, called at 147"
  - claim: "A further mark is added whenever the number given for it is above nothing"
    source: "`generate_client_order_id.py` 152"
  - claim: "Callers pass a ladder's generation, or a protection's version, into that number"
    source: "`execution_manager.py` 6185-6186 and 9430-9435"
  - claim: "A name longer than thirty-six characters is refused"
    source: "`generate_client_order_id.py` 156-158 with the limit at 21"
  - claim: "A protective pair is sent with one name for the pair, its two orders unnamed by Praxis"
    source: "`binance_adapter.py` 863-879"
  - claim: "Their names are read back from the venue's reply"
    source: "`binance_adapter.py` 1002-1012"
  - claim: "The name is written down before the send, and that same name is passed to the asking"
    source: "recorded at `execution_manager.py` 4242-4285, passed at 5518-5523"
---
# How an order is named

Praxis names an order before sending it, and works the name out rather than drawing it at random. The same inputs always give the same name.

A name has three parts: two letters saying how the work is being carried out, the first sixteen characters of the request's name with its hyphens dropped, and a number saying which order this is within that request.

## What is refused

A way of working with no letters set is refused, and so is a number outside nothing to 999. The number behind the extra mark must itself be nothing or more.

A request whose name has fewer than sixteen characters left after its hyphens are dropped is refused, since there would be too little to take. And a finished name longer than thirty-six characters is refused — a limit fixed in Praxis itself, whatever venue is being used.

## The extra mark

A further mark is added to the end whenever the number given for it is above nothing.

That number is not a count of attempts. Callers pass a ladder's generation into it, or a protection's version, so the very first send of a replacement can carry the mark already.

## What Praxis does not name

A [protective pair](protection.md) goes to the venue under a single name for the pair. Praxis does not name the two orders inside it; those names come back in the venue's reply and are read from there.

## Finding an order again

The name is written down before the send. When [a send goes unclear](when-a-send-is-unclear.md), that same recorded name is what the asking is made with.

## Related

- [What a trade is](what-a-trade-is.md)
- [Protection](protection.md)
