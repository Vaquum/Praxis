---
row: P4-54
baseline: 49aa659
created: 2026-10-14 10:25 UTC
modified: 2026-10-14 13:10 UTC
evidence:
  - claim: "Recovery works from the written failures rather than from any closing order, so a stop before one was written is still picked up"
    source: "`execution_manager.py` 7919-7926"
  - claim: "Only an account whose policy is to flatten and halt is recovered"
    source: "`execution_manager.py` 7912-7916"
  - claim: "An order the record holds as ended with something filled is passed over"
    source: "`execution_manager.py` 7930-7936"
  - claim: "A query failing for any reason but the venue not having the name skips that command"
    source: "`execution_manager.py` 7961-7962 against 7963-7970"
  - claim: "One the venue shows still working is left in place"
    source: "`execution_manager.py` 7984-7994"
  - claim: "One the venue shows with fills has those taken in, local records written for an order that already exists"
    source: "`execution_manager.py` 7972-7982 into 8035, 8048 and 8058"
  - claim: "That happens only where the record carries no fills for it yet"
    source: "`execution_manager.py` 8019-8026 before 8061"
  - claim: "One the venue has never heard of, and one ended with nothing filled, are sent again"
    source: "`execution_manager.py` 7996-7999"
  - claim: "The queue is drained before the exposure is weighed again, and a poisoned account stops there"
    source: "`execution_manager.py` 8235 and 8237-8245"
  - claim: "Only then is the close attempted again"
    source: "`execution_manager.py` 8255"
---
# How an unfinished close is recovered

A close left unfinished is a position whose [protection was lost](when-protection-is-lost.md) and whose [closing order](when-a-flatten-places-nothing.md) never settled. Starting the account picks these up from the failures written down, not from the orders — so a stop before any closing order existed is recovered too. Only an account whose policy is to flatten and halt is recovered at all.

## What the venue says about the name

The order's name is worked out from the request, and the venue asked about it.

An order the record already holds as ended with something filled on it is passed over before that, since something did close. A query failing for any reason other than the venue not having the name skips that command for this start.

One the venue shows still working is left in place for the feed to finish. One it shows with fills on it has those taken into the record, and local records for it written there and then: the record catching up with an order that already exists at the venue. That only happens where the record carries no fills for it yet — a part-recorded close is left to ordinary squaring instead.

## What is sent again

The close is attempted again for two answers: the venue not having the name, and the venue showing it ended with nothing filled.

What is still open is not taken from the old failure. The account's queue is drained to the end first, so every fill that arrived while it was down is on the books, and only then is the remainder worked out.

An account poisoned on the way through that drain stops there and sends nothing — a close sized from books Praxis cannot trust is worse than no close.

## Related

- [When protection is lost](when-protection-is-lost.md)
- [When a flatten places nothing](when-a-flatten-places-nothing.md)
- [What a restart puts back](what-a-restart-puts-back.md)

---

Created 2026-10-14 10:25 UTC · Last modified 2026-10-14 13:10 UTC
