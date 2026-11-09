---
row: P108-02
baseline: 49aa659
created: 2026-11-14 07:30 UTC
modified: 2026-11-14 07:30 UTC
evidence:
  - claim: "A permission flag is read only from a mapping, anything else reading as absent"
    source: "`binance_adapter.py` 139"
  - claim: "A flag that is absent or is not a true-or-false value raises, so an unreadable answer fails closed"
    source: "`binance_adapter.py` 140 into 141-142"
  - claim: "A flag that read as a true-or-false value is handed back as it stands"
    source: "`binance_adapter.py` 144"
  - claim: "A moment given without a zone, or with a zone that offers no offset, raises"
    source: "`binance_adapter.py` 160 into 161-162"
  - claim: "A moment left out entirely passes, the check asking only of one that is there"
    source: "`binance_adapter.py` 160, whose first test is the absence"
  - claim: "The simulated venue counts as enabled only where its address holds something other than spaces"
    source: "`binance_adapter.py` 120"
---
# What the adapter refuses to be told

Three small checks stand between what the adapter is told and what it acts on, and each fails in the safe direction.

## A permission flag

Read only from a mapping; anything else reads as absent. A flag that is absent, or that is not a true-or-false value, raises.

So an answer the adapter cannot read is treated as a refusal rather than as permission. The flag is about what the venue allows, and failing closed is the only safe way to misread it.

A flag that did read as a true-or-false value is handed back as it stands.

## A moment

One given without a zone, or with a zone that offers no offset, raises. One left out entirely passes — the check asks only of a moment that is there.

So the adapter will work with no moment at all but never with an ambiguous one.

## The simulated venue

It counts as enabled only where its address holds something other than spaces. An address set to blank or to spaces therefore leaves the real venue in place, rather than half-enabling a simulation that has nowhere to talk to.

## Related

- [How the adapter reckons its headroom](how-the-adapter-reckons-its-headroom.md)
