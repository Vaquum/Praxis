---
row: P66-02
baseline: 49aa659
created: 2026-11-13 00:00 UTC
modified: 2026-11-13 00:00 UTC
evidence:
  - claim: "The book, the ledger and the two long-lived parts are built before anything is started, and the saved state is read as the ledger is built"
    source: "`__main__.py` 183-185, then 186, then 188-204"
  - claim: "Handlers for the two stopping signals are put in place before any of those parts is started"
    source: "`__main__.py` 209-213, ahead of 219"
  - claim: "Each handler does one thing: it sets the event the run waits on"
    source: "`__main__.py` 213"
  - claim: "The poller is started and then the server, the starting of the poller setting its loop going without waiting for a first reading"
    source: "`__main__.py` 219, then 220, the loop set going at `feed.py` 157"
  - claim: "So the server can begin answering while the book is still empty, nothing here waiting for the first reading to land"
    source: "`__main__.py` 220 reached straight after 219"
  - claim: "A line naming seven of the nine settings and every registered account is written once both have started, the token and the directory left out of it"
    source: "`__main__.py` 222-232"
  - claim: "The run then waits on the event and does nothing else until it is set"
    source: "`__main__.py` 234"
  - claim: "The stopping runs however the attempt ended, and stops the server before the poller, the reverse of the starting"
    source: "`__main__.py` 236, then 238, then 239"
---
# The order the simulated venue starts and stops in

Running [the simulated venue](binsim.md) builds four things, starts two of them, and waits.

## Built before anything starts

The book, the ledger, the poller that fills the book, and the server. The saved state is read as the ledger is built, so the accounts are in hand before a port is opened.

## The handlers come first

Handlers for the two stopping signals are put in place before any part is started. Each does one thing: it sets the event the run waits on.

So a signal arriving during the starting is not lost. The handler is already there, and the stopping below runs as intended.

## Starting

The poller first, then the server. Starting the poller sets its loop going and answers at once, without waiting for a first reading to land, and nothing here primes the book separately.

So the server can begin answering while the book is still empty. The window is as long as the first reading takes, and what a caller meets inside it is settled by [the book](binsims-book.md) rather than here.

A line naming seven of the nine settings and every registered account is written once both have started, which is the service saying it is ready. The token and the directory are left out of it.

## Waiting

The run waits on the event and does nothing else until it is set. Everything the service does while running is done by the two parts already started.

## Stopping

The stopping runs however the attempt ended — including where one of the two starts failed.

The server is stopped before the poller, the reverse of the starting, so the thing that answers callers goes quiet before the thing that feeds it.

## Related

- [Binsim](binsim.md)
- [What the simulated venue's settings must be](what-the-simulated-venues-settings-must-be.md)
