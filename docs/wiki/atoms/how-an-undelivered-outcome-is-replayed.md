---
row: P2-39
baseline: 49aa659
created: 2026-09-26 19:03 UTC
modified: 2026-09-27 13:46 UTC
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
  - claim: "Each report is judged accounted for on its own"
    source: "`launcher.py` 1773-1777"
  - claim: "The turning returns a list of reports"
    source: "`outcome_translator.py` 227-245"
  - claim: "It returns none at all for a command it considers ended"
    source: "`outcome_translator.py` 156-164"
  - claim: "A piece for a command already ended is dropped by translation"
    source: "`outcome_translator.py` 156-164"
  - claim: "A produced outcome with no recorded destination is passed over and logged"
    source: "`launcher.py` 1755-1762"
  - claim: "The plan is read from the record and carried out at startup"
    source: "`launcher.py` 4521-4540"
  - claim: "Each report is sent as though new, by the routing call alone"
    source: "`launcher.py` 1814-1816 into 4534-4539"
---
# How an undelivered outcome is replayed

An [outcome](what-an-outcome-is.md) whose [handing over did not finish](how-an-outcome-is-delivered.md) is still in [the record](the-event-spine.md), and the next startup goes looking for it.

## Working out what is still unsent

Before anything is sent, Praxis works out a list from the records alone, for one [account](what-an-account-is.md) at a time.

Three kinds of record go into it: where each outcome was to be sent, the outcomes actually produced, and the names already accounted for. A name counts as accounted for in two ways — the receiver confirmed it, or an earlier startup recorded that Praxis had stopped trying. Those names belong to the reports an outcome becomes, not to the outcome itself, so one report can be confirmed while another from the same outcome is still waiting.

Each produced outcome is then rebuilt from its records and turned into separate reports, the same way it was the first time. One outcome may come out as several reports, or as none. Each report is judged on its own, by a name worked out afresh from the rebuilt copy rather than remembered.

An outcome with no record of where it was to be sent is skipped, with a line in the log. There is nowhere to send it, so it waits for someone to look.

## Sending them again

At startup the records are read, the list built, and each report on it sent as though new.

[What becomes of each one](outcomes-that-never-come-back.md) decides whether a later startup sends it again.

## Related

- [Outcomes that never come back](outcomes-that-never-come-back.md)
- [How an outcome is delivered](how-an-outcome-is-delivered.md)
