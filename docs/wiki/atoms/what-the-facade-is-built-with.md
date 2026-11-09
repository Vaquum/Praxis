---
row: P99-01
baseline: 49aa659
created: 2026-11-09 07:50 UTC
modified: 2026-11-09 08:20 UTC
evidence:
  - claim: "Two of the configuration's callbacks are wrapped as the facade is built, so an absent one becomes a thing that does nothing"
    source: "`praxis/trading.py` 205, and 206-208, into 143-145"
  - claim: "The symbols a bootstrap filters on are frozen into a set that cannot be changed afterwards"
    source: "`praxis/trading.py` 211, and the clock at 118"
  - claim: "A venue to trade against is built where none was handed in"
    source: "`praxis/trading.py` 212 into 213-215"
  - claim: "The inbound side is built from the manager, that venue and the account credentials"
    source: "`praxis/trading.py` 236 into 237-240"
  - claim: "Fourteen fields are then set, every flag false, every task absent and every collection empty"
    source: "`praxis/trading.py` 241, and 242, and 243, and 244, and 245, and 246, and 247, and 248, and 249, and 250, and 251, and 252, and 253, and 254"
---
# What the facade is built with

Building the facade wraps two callbacks, builds what was left out, and sets every one of its own fields to an empty start.

## The two callbacks wrapped at building

The fund one and the mismatch one, wrapped as the facade is built. An absent one therefore becomes a thing that does nothing, and whoever calls it later need not ask whether it is there.

[The callbacks set through a setter](how-a-callers-callback-is-wrapped.md) are wrapped when they are set instead. So a callback given in the configuration and one given afterwards travel different roads to the same place, and only one of those roads lets an absence survive.

## What is frozen

The symbols a bootstrap filters on, into a set that cannot be changed afterwards. Whatever the caller passed is copied, so a caller holding the original cannot alter what the facade filters on.

## What is built for you

A venue to trade against, where none was handed in. The inbound side, always, from the manager, that venue and the account credentials.

## What starts empty

Fourteen fields: every flag false, every task absent, every collection empty. So the whole of what a facade knows about any account arrives through starting, and a freshly built one knows nothing of any.

## Related

- [What the facade hands out](what-the-facade-hands-out.md)
- [How a caller's callback is wrapped](how-a-callers-callback-is-wrapped.md)
