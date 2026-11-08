---
row: P61-01
baseline: 49aa659
created: 2026-11-12 19:00 UTC
modified: 2026-11-12 19:00 UTC
evidence:
  - claim: "Every one of the forty-two event records is built on one shared record and every one of them calls that record's check before making its own"
    source: "`events.py` 96-117, each of the forty-two calling it as its own check opens, as at 185, 249, 286 and 1709"
  - claim: "That check asks the account's name through the shared test for emptiness, which asks nothing about its kind"
    source: "`events.py` 113 into `_require_str.py` 28-30"
  - claim: "It then asks the moment to carry a zone and to give an offset, as one test whose second half is reached only where a zone is there"
    source: "`events.py` 115-117"
  - claim: "The forty-two call that same shared test ninety times between them, and ninety-four names go through it, one call walking five field names at once"
    source: "`events.py` 188-191, and 1712-1713, and 1959-1961, the one walking five at 1288-1295"
  - claim: "No test asks the moment to be a moment; its zone is read straight off it, so a thing with no zone to read fails on the reading"
    source: "`events.py` 115, which reads the zone off the field before anything is compared"
---
# What every event is held to

Every fact [the trading side](what-an-account-is.md) records is one of forty-two records, and all forty-two rest on one shared record whose check each of them runs before its own.

## The two things the shared check asks

The account's name goes through [the shared test for emptiness](what-a-commands-checks-let-through.md), which turns away whatever counts as nothing and asks nothing about kind.

The moment must carry a zone, and that zone must give an offset. The two stand in one test, the second half reached only where a zone is there, so a moment with no zone and a zone answering nothing are refused on the same line and told apart by nothing.

## That it is reached at all

Each of the forty-two writes its own check and opens it by calling the shared one. None of them leaves that call out, so the two questions above are asked of every event the trading side records, and the forty-two differ only in what they add.

## Names, ninety calls over

The forty-two call that same shared test ninety times between them, and ninety-four names go through it, one call walking five field names at once. It is the most-used check here and the one that asks least, and seven of those calls say [the name may be absent](the-names-a-record-may-leave-out.md).

## What is never asked

No test asks the moment to be a moment. Its zone is read straight off it, so a thing with nothing of that name to read fails on the reading rather than on a refusal, and a thing of another kind that does carry a zone answering an offset passes. Nothing asks the moment to fall in any particular era either.

## Related

- [What a command's checks let through](what-a-commands-checks-let-through.md)
- [The grounds a figure is weighed on](the-grounds-a-figure-is-weighed-on.md)
- [The names a record may leave out](the-names-a-record-may-leave-out.md)
