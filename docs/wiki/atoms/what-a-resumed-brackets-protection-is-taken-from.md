---
row: P137-02
baseline: 49aa659
created: 2026-11-15 13:00 UTC
modified: 2026-11-15 13:00 UTC
evidence:
  - claim: "The protection's name and version come from the latest active record where there is one"
    source: "`execution_manager.py` 1654, then 1655 into 1656-1657"
  - claim: "Where there is none, the name is worked out from the mode, the command and the protection's place, at version nought"
    source: "`execution_manager.py` 1659-1663, the place at 181"
  - claim: "That name is then asked of the account, and the bracket's road turns on whether the order is resting"
    source: "`execution_manager.py` 1665, then 1667"
  - claim: "The average entry price is the entry's money over the amount it filled, and nothing where it filled nothing"
    source: "`execution_manager.py` 1668-1672"
  - claim: "The amend whose legs are restored is found by matching the name of the list actually resting, rather than by version"
    source: "`execution_manager.py` 1673, then 1674 into 1683-1691"
  - claim: "Where such an amend is found the three protective prices are its own, and otherwise they are worked out from the command and the average entry price"
    source: "`execution_manager.py` 1702 into 1703-1705, or 1706 into 1707-1708"
  - claim: "The bracket then comes back with its protection placed, reported active, at that version and under that name, carrying the average entry price and those three prices"
    source: "`execution_manager.py` 1711-1722"
  - claim: "A bracket whose protection is absent or still submitting comes back carrying only its command and its entry name"
    source: "`execution_manager.py` 1743-1746"
---
# What a resumed bracket's protection is taken from

A resumed bracket's protection is rebuilt from whichever list the venue is actually resting, and that is not always the list the latest version names.

## Which name is asked after

The latest record of an active protection gives both the name and the version. Where there is no such record, the name is worked out from the mode, the command and the protection's place, at version nought.

That name is then asked of the account, and everything after turns on whether the order is resting.

## The amend matched by name

The amend whose legs are restored is found by matching the name of the list actually resting — rather than by taking the newest version.

An amend whose cancel never landed leaves the list from before it resting while the version has already moved on. Matching by name restores the legs that belong to the list that is really there, where matching by version would restore legs for a list the venue never kept.

Where no recorded amend matches, the protection is the initial placement, and its three prices are worked out from the command and the average entry price instead of read.

## The price the legs rest on

The average entry price is the entry's money over the amount it filled. An entry that filled nothing gives none, and [that stops the resume](what-stops-a-bracket-being-resumed.md) rather than producing legs from nothing.

## The two shapes it comes back in

With its protection placed, reported active, at that version and under that name, carrying the average entry price and the three prices.

Or, where the protection is absent or still submitting, carrying only its command and its entry name — a bracket awaiting protection, which the account's own work will place.

## Related

- [What stops a bracket being resumed](what-stops-a-bracket-being-resumed.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [What a restart puts back of a bracket](what-a-restart-puts-back-of-a-bracket.md)
