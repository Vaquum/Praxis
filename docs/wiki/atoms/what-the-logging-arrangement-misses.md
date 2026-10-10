---
row: P4-37
baseline: 49aa659
created: 2026-10-03 20:11 UTC
modified: 2026-10-10 09:36 UTC
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
  - claim: "The level is handed to Python's own setting-up as it stands, nothing in Praxis reading it first"
    source: "`launcher.py` 4854 within the call at 4853-4856"
  - claim: "The other route reads the level itself and falls back where it does not know it"
    source: "`praxis/infrastructure/observability.py` 45"
  - claim: "A logger is kept on the thing it was fetched through, so fetching the same name again builds another"
    source: "`praxis/infrastructure/observability.py` 63 against 125"
---
# What the logging arrangement misses

[The arrangement a host sets up](what-a-host-writes-about-itself.md) is narrower than it looks. Three things it does not do are worth knowing.

## The root alone is cleared

Whatever was attached to the root of Python's logging is detached, and one handler put in its place. Detaching them does not close them.

The root is all that is touched. A handler attached to some logger below it stays where it is.

The arrangement's own route is the other way about: it writes to standard output directly, without passing through the root. So clearing the root neither captures that route nor stops it.

## Plain text may change nothing

Asking for plain text calls Python's own setting-up, and nothing forces that call through. Python's own rule then applies: where a handler is already attached to the root, that call does nothing at all, the level it was given included.

Either way the level goes over as it stands; nothing in Praxis reads it first. The other route does read it, and falls back to its own default where the name means nothing to it.

## A logger is kept, but not by name

A logger is kept on the thing it was fetched through, so reusing that same thing reuses the logger. Fetching the same name a second time builds another.

## Related

- [What a host writes about itself](what-a-host-writes-about-itself.md)
- [Starting a host](starting-a-host.md)
