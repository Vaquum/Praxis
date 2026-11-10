---
row: P43-02
baseline: 49aa659
created: 2026-11-08 17:05 UTC
modified: 2026-11-08 17:05 UTC
evidence:
  - claim: "The record is declared unchangeable, so an ordinary write to any of its fields is refused from the moment it is made"
    source: "`trading_config.py` 31, over the fields declared at 83-110"
  - claim: "Its own building writes to it three times through the one call that goes round that refusal"
    source: "`trading_config.py` 163, or 174, or 196"
  - claim: "The credentials mapping is copied and the copy sealed over the field it arrived in"
    source: "`trading_config.py` 146 into 163-167"
  - claim: "The mapping of what to do when protection fails is copied and sealed the same way"
    source: "`trading_config.py` 180 into 196-200"
  - claim: "The ways of working are frozen into a set over the field they arrived in"
    source: "`trading_config.py` 174-178"
---
# What the configuration record holds afterwards

The record is declared unchangeable, and its own building writes to it three times through the one call that goes round that.

## The three writes

Each of its two mappings is copied and the copy sealed over the field it arrived in. The ways of working are frozen into a set over theirs.

The refusal to be written to holds from the moment the record is made, so the building itself has to go round it — which is what the call it uses is for.

## What the sealing is worth

A caller that kept its own mapping and changed it afterwards changes nothing the host reads: the host holds a copy, and that copy refuses an entry.

So the keys that passed are the keys the host works from, and no later addition to the caller's own mapping reaches it.

## What the sealing is not

The road the building took stays open. The same call that sealed a field can replace it, and nothing checks what replaces it — so the record's refusals are made once, at the building, rather than held against every later write.

What the record guarantees is therefore about the caller's mapping rather than about the record itself: the copy it holds refuses an entry, while the field holding that copy can still be replaced.

## Related

- [What the host's configuration record refuses](what-the-hosts-configuration-record-refuses.md)
- [Ways of working a host may drive](ways-of-working-a-host-may-drive.md)
- [Which settings are refused](which-settings-are-refused.md)
