---
row: P3-19
baseline: 49aa659
created: 2026-09-30 19:01 UTC
modified: 2026-10-11 21:12 UTC
evidence:
  - claim: "Credentials must be text and neither part may be empty"
    source: "`secret_store.py` 67-73"
  - claim: "They are held as one value that cannot be altered"
    source: "`secret_store.py` 49"
  - claim: "Printing the whole value gives a stand-in for both parts"
    source: "`secret_store.py` 79 and 85 with the stand-in at 36"
  - claim: "Reading the fields themselves gives the real thing"
    source: "`secret_store.py` 60-61, which no reader guards"
  - claim: "They are fetched at startup and handed on to be kept"
    source: "`launcher.py` 4954-4967 into `trading_inbound.py` 123-132"
  - claim: "The venue call keeps a reference to the same value and reads it back when sending"
    source: "`binance_adapter.py` 444, read back at 480 and 721"
  - claim: "On live a file is used where one is named, otherwise the system's own store"
    source: "past `launcher.py` 4945, either 4946-4948 or 4950"
  - claim: "A mapping in memory serves every other way of working"
    source: "`secret_store.py` 229 and 247, chosen at `launcher.py` 4952"
  - claim: "The system store separates nothing recorded from a store that would not answer"
    source: "either `secret_store.py` 211 or 205-207"
  - claim: "A file it cannot open, or whose text is not the JSON it expects, is the store failing, while one whose characters will not decode escapes as it is"
    source: "either `secret_store.py` 293-295 or 299-301, read at 292 past both"
  - claim: "A file whose characters will not decode is neither, and escapes as it is"
    source: "`secret_store.py` 291-301, which catches neither case"
---
# Where credentials come from

The key and secret Praxis needs to act for an [account](what-an-account-is.md) are fetched once at startup and handed on to be kept. Each must be text, and neither may be empty.

They are held as one value that cannot be altered. The venue call keeps a reference to that same value and reads it back each time it sends.

## What the hiding covers

Printing the whole value gives a stand-in in place of both parts, so writing one to a log by accident shows nothing.

That covers printing the value. Reading its two fields gives the real thing — so a log line built from the fields, or anything that takes an object apart field by field, exposes them just as readily. The protection is narrow, and it is not a reason to relax about where a credential travels.

## Where they are kept

Three places. On live, a file is used where one is named; otherwise the system's own store. Every other way of working takes a mapping held in memory.

## Telling absence from failure

The system store separates two cases: nothing recorded there for that account, and a store that would not answer at all.

A file it cannot open, or cannot read as it expects, is reported as the store failing. A file whose characters will not decode is neither of those, and comes out as it is.

Absence says only that this store holds nothing for this account — never that the account was not set up, since it may have been removed, or set up somewhere else.

## Related

- [What an account is](what-an-account-is.md)
- [What a venue is](what-a-venue-is.md)
