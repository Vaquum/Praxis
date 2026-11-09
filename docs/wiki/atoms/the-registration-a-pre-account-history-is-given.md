---
row: P161-02
baseline: 49aa659
created: 2026-11-16 01:00 UTC
modified: 2026-11-16 01:00 UTC
evidence:
  - claim: "The replayed events are sifted for the four kinds that book into the money record"
    source: "`execution_manager.py` 2114-2117, the four named at 2116"
  - claim: "Where any of those were found and none of them is a registration, a registration naming the default method is applied to the money record"
    source: "`execution_manager.py` 2119 into 2120-2126"
  - claim: "It is applied to the money record alone, with nothing written to the record of events"
    source: "`execution_manager.py` 2120, against 2162"
  - claim: "The sifting runs as part of the replay"
    source: "`execution_manager.py` 1113"
  - claim: "The startup write that follows the replay then finds the method named and writes nothing"
    source: "`trading.py` 549, reaching `execution_manager.py` 2154 into 2155"
---
# The registration a pre-account history is given

A history written before accounts had registrations carries none, and a registration is made up in memory so the money record can take that history's fills.

## What is looked for

The replayed events are sifted for the four kinds that book into the money record: a registration, a fill, a closed trade, and a movement of funds.

Where any of those were found and none of them is a registration, the history predates registrations and books to the money record all the same. A registration naming the default method is applied there so the rest can be projected.

## Where it goes and where it does not

It is applied to the money record alone. Nothing is written to the record of events, so the made-up registration lives only in memory and is made again on the next replay.

## What it costs the startup

The sifting runs as part of the replay, and [the startup write](when-an-accounts-registration-is-written.md) comes straight after it. By then the method is named, so that write finds the account registered and writes nothing — which is how a pre-account history ends up with a registered money record and no registration in its record of events.

## Related

- [When an account's registration is written](when-an-accounts-registration-is-written.md)
- [How a restart reads its record back](how-a-restart-reads-its-record-back.md)
- [What an account is](what-an-account-is.md)
