---
row: P2-39
baseline: 49aa659
created: 2026-09-26 19:03 UTC
modified: 2026-09-27 07:37 UTC
evidence:
  - claim: "A plan is worked out from the rows alone, for one account"
    source: "`launcher.py` 1728-1745"
  - claim: "Where each outcome was to be sent, and the ids already settled, are gathered first"
    source: "`launcher.py` 1733-1736"
  - claim: "Then the outcomes produced are walked"
    source: "`launcher.py` 1749-1751"
  - claim: "An id counts as settled when it was acknowledged, or when an earlier start gave up on it"
    source: "`launcher.py` 1735-1736"
  - claim: "Each produced outcome is rebuilt from its rows and put through translation afresh"
    source: "`launcher.py` 1772-1773"
  - claim: "Each piece translation returns is judged settled on its own"
    source: "`launcher.py` 1773-1777"
  - claim: "Translation returns a list of pieces"
    source: "`outcome_translator.py` 227-245"
  - claim: "It returns none at all for a command it considers ended"
    source: "`outcome_translator.py` 156-164"
  - claim: "A piece for a command already ended is dropped by translation"
    source: "`outcome_translator.py` 156-164"
  - claim: "A produced outcome with no recorded destination is passed over and logged"
    source: "`launcher.py` 1755-1762"
  - claim: "The plan is read from the record and carried out at startup"
    source: "`launcher.py` 4521-4540"
  - claim: "Each piece is handed over as though new, by the routing call alone"
    source: "`launcher.py` 1814-1816 into 4534-4539"
---
# How an undelivered outcome is replayed

An [outcome](what-an-outcome-is.md) whose [handing over did not finish](how-an-outcome-is-delivered.md) is still in [the record](the-event-spine.md), and the next start goes looking for it.

What it offers again are the pieces it routes onward itself. A caller the host was given to wrap is not offered anything a second time.

## Working out what is owed

Before anything is sent, a plan is worked out from the rows alone, for one [account](what-an-account-is.md) at a time.

Three kinds of row go into it: where each outcome was to be sent, the outcomes actually produced, and the ids already settled. An id counts as settled two ways — it was acknowledged as received, or an earlier start gave up on it.

Every produced outcome is rebuilt from its own rows and put through translation again. Translation is what decides the pieces actually owed: one produced row may come out as several, or as none at all. Each piece is judged settled or not on its own id, worked out afresh rather than remembered.

An outcome produced with no record of where it was to go is passed over, with a line in the log. There is nowhere to send it, so it waits for someone to look.

## Sending it again

At startup the record is read, the plan built from it, and each pair in it handed over as though new.

Each piece is offered as though new, and [what becomes of it](outcomes-that-never-come-back.md) decides whether a later start sees it again.

## Related

- [Outcomes that never come back](outcomes-that-never-come-back.md)
- [How an outcome is delivered](how-an-outcome-is-delivered.md)
- [Outcomes](what-an-outcome-is.md)
