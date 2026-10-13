---
row: P4-37
baseline: 49aa659
created: 2026-10-03 20:11 UTC
modified: 2026-10-10 11:30 UTC
evidence:
  - claim: "Whatever was attached to the root of Python's logging is detached, and one handler put in its place"
    source: "`praxis/infrastructure/observability.py` 80-82"
  - claim: "Detaching them does not close them"
    source: "`praxis/infrastructure/observability.py` 81"
  - claim: "That touches the root alone, so a handler attached anywhere below it stays where it is"
    source: "`praxis/infrastructure/observability.py` 80-82"
  - claim: "The arrangement's own route is given a writer of its own rather than the root's handler"
    source: "`praxis/infrastructure/observability.py` 62 against 80-82"
  - claim: "Asking for plain text calls Python's own setting-up"
    source: "`launcher.py` 4853-4856"
  - claim: "That call is made with nothing forcing it through"
    source: "`launcher.py` 4853-4856, passing no force"
  - claim: "The level is handed to Python's own setting-up as it stands, nothing in Praxis reading it first"
    source: "`launcher.py` 4854 within the call at 4853-4856"
  - claim: "The other route reads the level itself and falls back where it does not know it"
    source: "`praxis/infrastructure/observability.py` 45"
  - claim: "Keeping a logger once fetched is asked for, and a logger is fetched by name"
    source: "`praxis/infrastructure/observability.py` 63 against 125"
---
# What the logging arrangement misses

[The arrangement a host sets up](what-a-host-writes-about-itself.md) is narrower than it looks. Three things it does not do are worth knowing.

## The root alone is cleared

Whatever was attached to the root of Python's logging is detached, and one handler put in its place. Detaching them does not close them.

The root is all that is touched. A handler attached to some logger below it stays where it is.

The arrangement's own route is the other way about: it is given a writer of its own rather than the root's handler. So clearing the root neither captures that route nor stops it.

## Plain text may change nothing

Asking for plain text calls Python's own setting-up, and nothing forces that call through. What that call then does where a handler is already attached to the root is Python's own affair.

The level goes over as it stands, nothing in Praxis reading it first. The other route does read it, and falls back to its own default where the name means nothing to it.

## A logger is kept once fetched

Keeping a logger once it has been fetched is asked for when the arrangement is set up, and a logger is fetched by name. What that keeping is keyed on is the library's own affair, not something these lines settle.

## Related

- [What a host writes about itself](what-a-host-writes-about-itself.md)
- [Starting a host](starting-a-host.md)
