---
row: P176-02
baseline: 49aa659
created: 2026-11-09 13:01 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "The version used is the standing one or the first, whichever is greater"
    source: "`execution_manager.py` 6837-6839"
  - claim: "A state-unknown is recorded, naming the pair's current name as both the old one and the new"
    source: "`execution_manager.py` 6845-6857, the two names set at 6855, and 6856, the record built at 10000-10008, then 10009"
  - claim: "Only after that record goes down is the standing moved to unknown and the moment stamped"
    source: "`execution_manager.py` 6845, then 6861, then 6862"
  - claim: "A scan over protection is then asked for"
    source: "`execution_manager.py` 6863"
  - claim: "That record is what a restart reads to rebuild the bracket in doubt"
    source: "`execution_manager.py` 6845, against 1779, then 1780, then 1787, the names read at 1837, and 1838"
  - claim: "The watchdog gathers both names and asks about a name appearing twice once"
    source: "`execution_manager.py` 7366-7373"
---
# What hearing a protection has ended does

A protective pair the venue reports as ended leaves the position's cover in doubt, and what Praxis does about it is write the doubt down before believing it.

## The record first

A state-unknown is recorded, under the standing version or the first, whichever is greater. Only after that record goes down is the bracket's standing moved to unknown and the moment stamped.

That record is what a restart reads to rebuild a bracket in doubt, taking the version, both names and the moment from it. A restart falling between the record and the marks finds the doubt recorded all the same, the marks being memory and the record not.

## Both names, one name

The record names the pair's current name as both the old one and the new. The watchdog gathers both and asks about a name appearing twice once, so naming it twice costs nothing and leaves the record's shape the same as an amend's.

## Then the scan

A scan over protection is asked for, which is what brings the watchdog round to ask the venue what became of the pair.

## Related

- [Which order the watchdog asks about first](which-order-the-watchdog-asks-about-first.md)
- [What a protection of unknown fate is rebuilt as](what-a-protection-of-unknown-fate-is-rebuilt-as.md)
- [When protection is lost](when-protection-is-lost.md)
