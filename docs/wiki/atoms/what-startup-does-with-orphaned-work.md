---
row: P4-50
baseline: 49aa659
created: 2026-10-14 07:55 UTC
modified: 2026-10-14 07:55 UTC
evidence:
  - claim: "Work accepted with nothing afterwards to account for it is refused on the account's behalf, and so is a send with neither result nor ending"
    source: "`execution_manager.py` 2254-2258 and 2260-2263 into 2271-2275 and 2277-2281"
  - claim: "A scheme the replay could not resume is retired separately"
    source: "`execution_manager.py` 2260-2266 into 2279-2281"
  - claim: "The venue is asked per symbol the account trades, and an order the record knows, open or closed, is left alone"
    source: "`trading.py` 932 and 942, passed over at 954-955"
  - claim: "One the record does not know is cancelled only where its name carries a command Praxis owns"
    source: "`trading.py` 933 and 958-965 before 967-978"
  - claim: "A pair is cancelled as a pair rather than a single order"
    source: "`trading.py` 977-978 against 984"
  - claim: "A query or a cancel that fails leaves the account unready"
    source: "`trading.py` 942-951 and 990-999 into 606-608"
  - claim: "An account left unready has its startup failed and its stream closed"
    source: "`trading.py` 617-624"
---
# What startup does with orphaned work

An orphan is work one side knows about and the other does not. Starting an [account](what-an-account-is.md) looks for both kinds: a request the record accepted but nothing afterwards accounts for, and an order resting at the venue the record has never heard of.

## Work the record cannot account for

A request accepted with no send, no scheme and no ending recorded after it is refused on the account's behalf, so [a caller waiting on it](how-an-outcome-crosses-back.md) hears an answer rather than nothing. A send written down with neither a result nor an ending after it is refused the same way.

A scheme the replay could not put back is retired on its own path, for the same reason.

## Orders the record has never heard of

The venue is asked, for each symbol the account trades, which orders it still shows resting. One the record knows — open or already closed — is left where it is.

One the record does not know is only cancelled where its name carries a command this account owns. Anything else is somebody else's order on the same venue account, and is left untouched and logged. A pair is cancelled as a pair, not as the one order the name happens to point at.

## Failing closed

Asking the venue can fail, and so can the cancel. Either leaves the account unready, and an unready account has its startup failed and its feed closed rather than being allowed to trade.

So an account that cannot finish this sweep does not trade at all, which is the point: an order nobody can account for is one nobody is managing.

## Related

- [Starting a host](starting-a-host.md)
- [What a restart puts back](what-a-restart-puts-back.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)

---

Created 2026-10-14 07:55 UTC · Last modified 2026-10-14 07:55 UTC
