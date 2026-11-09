---
row: P149-02
baseline: 49aa659
created: 2026-11-09 11:36 UTC
modified: 2026-11-09 11:36 UTC
evidence:
  - claim: "A command is refused where the account is not registered, where it has fail-stopped, and where it failed its startup and stays parked"
    source: "`execution_manager.py` 3429, then 3430 into 3431-3432, or 3434 into 3435-3436, or 3438 into 3443"
  - claim: "A name supplied by the caller must not be empty"
    source: "`execution_manager.py` 3445, then 3446 into 3447-3448"
  - claim: "It is then held to what a client order id can be built from"
    source: "`execution_manager.py` 3450"
  - claim: "A name already accepted, or already held as a command, is refused as in use"
    source: "`execution_manager.py` 3452-3455 into 3456-3457"
  - claim: "Where no name is supplied one is made instead"
    source: "`execution_manager.py` 3458 into 3459"
  - claim: "The command is then built from the name and everything the caller gave"
    source: "`execution_manager.py` 3461-3470"
---
# What a caller-supplied command name must be

A caller may name its own command rather than take a made-up name, and a supplied name is held to three things the made-up one never has to meet.

## Before the name is looked at

The account must be registered, must not have fail-stopped, and must not have failed its startup and stayed parked. All three are refused before anything about the name is weighed.

## The three the name must meet

It must not be empty. It must be something [a client order id](how-an-order-is-named.md) can be built from. And it must be neither already accepted nor already held as a command — either of those refuses it as in use.

The in-use test reads two places, so a name is in use while its command is waiting to be dequeued and also while it is held as a live command.

## When none is supplied

One is made instead, and none of the three tests applies to it. So a made-up name is trusted to be well formed and unique by the way it is made rather than by being checked.

## What follows either way

The command is built from the name and everything the caller gave.

## Related

- [How an order is named](how-an-order-is-named.md)
- [What a queue reservation is for](what-a-queue-reservation-is-for.md)
- [How an order is placed](how-an-order-is-placed.md)
