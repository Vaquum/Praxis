---
row: P4-37
baseline: 49aa659
created: 2026-10-03 20:11 UTC
modified: 2026-10-09 07:31 UTC
evidence:
  - claim: "Whatever was attached to the root of Python's logging is detached, and one handler put in its place"
    source: "`praxis/infrastructure/observability.py` 80-82"
  - claim: "Detaching them does not close them"
    source: "`praxis/infrastructure/observability.py` 81"
  - claim: "That touches the root alone, so a handler attached anywhere below it stays where it is"
    source: "`praxis/infrastructure/observability.py` 80-82"
  - claim: "The arrangement's own route does not pass through the root at all"
    source: "`praxis/infrastructure/observability.py` 62 against 80-82"
  - claim: "Asking for plain text calls Python's own setting-up"
    source: "`launcher.py` 4853-4856"
  - claim: "Nothing forces that call through, so where a handler is already attached to the root it does nothing"
    source: "`launcher.py` 4853-4856, passing no force"
  - claim: "Where it does run, the level is checked there and an unknown one raises"
    source: "`launcher.py` 4854"
  - claim: "A logger is kept on the thing it was fetched through, so fetching the same name again builds another"
    source: "`praxis/infrastructure/observability.py` 63 against 125"
---
# What the logging arrangement misses

[The arrangement a host sets up](what-a-host-writes-about-itself.md) is narrower than it looks. Three things it does not do are worth knowing.

## The root alone is cleared

Whatever was attached to the root of Python's logging is detached, and one handler put in its place. Detaching them does not close them.

The root is all that is touched. A handler attached to some logger below it stays where it is. A logger set to keep its lines to itself bypasses the root handler entirely.

The arrangement's own route is the other way about: it writes to standard output directly, without passing through the root. So clearing the root neither captures that route nor stops it.

## Plain text may change nothing

Asking for plain text calls Python's own setting-up, and nothing forces that call through. Where a handler is already attached to the root, it does nothing at all — which includes not checking the level it was given. A handler attached further down does not hold it back.

Where it does run, that level is checked there, and an unknown one raises rather than falling back.

## A logger is kept, but not by name

A logger is kept on the thing it was fetched through, so reusing that same thing reuses the logger. Fetching the same name a second time builds another.

## Related

- [What a host writes about itself](what-a-host-writes-about-itself.md)
- [Starting a host](starting-a-host.md)
