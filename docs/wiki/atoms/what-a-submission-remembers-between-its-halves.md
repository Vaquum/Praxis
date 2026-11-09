---
row: P129-01
baseline: 49aa659
created: 2026-11-15 09:00 UTC
modified: 2026-11-15 09:00 UTC
evidence:
  - claim: "A fresh remembering is made for every call to the submitter, holding each built request under its command's name"
    source: "`launcher.py` 4220-4222, then 4228, then 4230 into 4231-4235"
  - claim: "A request with no command name is handed to the checks and remembered nowhere"
    source: "`launcher.py` 4230, then 4237"
  - claim: "The registering reads that remembering by the command's name, by a lookup that demands the entry"
    source: "`launcher.py` 2078"
  - claim: "Three of the account's loops are each given that same submitter to call"
    source: "`launcher.py` 4555, and 4568, and 4579"
  - claim: "The registry of commands is made once for the account and shared across every call"
    source: "`launcher.py` 4209, against 4220-4222"
  - claim: "The request builder drops an action whose strategy the settings do not name"
    source: "`launcher.py` 4180, then 4182 into 4191"
  - claim: "It passes the venue's adapter through only where the trading stack stands"
    source: "`launcher.py` 4201-4205"
  - claim: "Where no registering runs, the request is built again after the send and the record set on the registration"
    source: "`launcher.py` 4325-4331, then 4333 into 4334"
---
# What a submission remembers between its halves

A submission is built in one place and registered in another, and what carries a request between the two is a mapping made fresh for each batch of actions.

## The fresh remembering

Every call to the submitter makes one. As each request is built, it is put there under its command's name, and the request is handed to the checks as well.

The registering then reads it back by that name, by a lookup that demands the entry — so a command reaching the registering with nothing remembered for it stops there.

## Why it is per call

Three of the account's loops are each given the same submitter to call. A mapping made once for the account would be shared between those calls, and one call could clear it between another's writing and the registering's reading.

The registry of commands is made once for the account and shared across every call. That one is guarded by a lock; this one needs none, because no two calls share it.

## What is not remembered

A request with no command name. It is handed to the checks like any other and put nowhere, so nothing can look it up afterwards.

## The road with no registering

Where no registering runs, the request is built again after the send and the record set on the registration — which is [the one road that rebuilds](what-rebuilding-an-orders-record-is-given.md) rather than being handed what the checks read.

## What the builder refuses

An action whose strategy the settings do not name is dropped. The venue's adapter is passed through only where the trading stack stands, so a host without one builds requests that are never snapped to the venue's steps.

## Related

- [What rebuilding an order's record is given](what-rebuilding-an-orders-record-is-given.md)
- [How an action is routed into a request](how-an-action-is-routed-into-a-request.md)
- [What a pending sale is](what-a-pending-sale-is.md)
