---
row: P161-01
baseline: 49aa659
created: 2026-11-16 01:00 UTC
modified: 2026-11-16 11:30 UTC
evidence:
  - claim: "The account is looked up, and a name the manager does not hold is refused outright"
    source: "`execution_manager.py` 2148, then 2150, then 2151, then 2152"
  - claim: "Nothing is written where the account's money record already names a cost-basis method"
    source: "`execution_manager.py` 2154 into 2155"
  - claim: "Otherwise the registration is written to the record of events"
    source: "`execution_manager.py` 2157, then 2162"
  - claim: "It reaches the money record only where that write answered with a place"
    source: "`execution_manager.py` 2164 into 2165"
  - claim: "The write is attempted on every startup, straight after the replay"
    source: "`trading.py` 548, then 549"
  - claim: "The money record refuses a second registration and holds the method unchangeable"
    source: "`account_ledger.py` 235, then 237, the method set at 239"
  - claim: "A refusal there is swallowed where an event is applied to the money record"
    source: "`execution_manager.py` 2091, then 2093"
  - claim: "A restart from a saved picture carries the method back"
    source: "`account_ledger.py` 213, then 214 into 215"
---
# When an account's registration is written

An account's registration is the event that fixes how its costs are counted, and it is written once in the account's life — though the write is attempted on every startup.

## The one test

Every startup tries it, straight after the replay. What decides whether anything is written is one reading: whether the account's money record already names a cost-basis method.

A name the manager does not hold is refused outright. A method already named means the account was registered before, by a registration in the replayed history, by [the registration a pre-account history is given](the-registration-a-pre-account-history-is-given.md), or by a saved picture that carried the method back — and nothing is written.

Otherwise the registration goes down in the record of events, and reaches the money record only where that write answered with a place.

## Why the test is the whole of it

The money record refuses a second registration: the method is fixed by the first and cannot be changed. That refusal would never be seen, because a refusal raised while an event is applied to the money record is swallowed there.

So the reading is what keeps the record of events from carrying two registrations for one account. Without it the second would go down, the money record would refuse it, and the only sign would be a line in the log.

## Related

- [The registration a pre-account history is given](the-registration-a-pre-account-history-is-given.md)
- [What an account is](what-an-account-is.md)
- [How a restart reads its record back](how-a-restart-reads-its-record-back.md)
