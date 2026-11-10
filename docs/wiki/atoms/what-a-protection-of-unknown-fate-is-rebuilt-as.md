---
row: P138-01
baseline: 49aa659
created: 2026-11-09 10:49 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "One pass gathers the bracket starts, the latest unresolved phase, and the latest amend request kept apart from it"
    source: "`execution_manager.py` 1772-1774, then 1775, then 1776 into 1777, or 1779 into 1780, then 1781 into 1782"
  - claim: "A protection reported active or failed clears the unresolved phase, so only a command whose latest protection record is neither reaches this road"
    source: "`execution_manager.py` 1784 into 1785"
  - claim: "A command the bracket resume already rebuilt is passed over, and so is one with no start recorded"
    source: "`execution_manager.py` 1787, then 1788 into 1789, or 1791, then 1792 into 1793, or the bracket rebuilt whole at 1710-1722 before 1731"
  - claim: "A command that will not rebuild from its start is reported and passed over"
    source: "`execution_manager.py` 1795-1796, then 1797 into 1805, the rebuilding it attempts at 1862, reaching 1530"
  - claim: "The average entry price is taken where the entry's order is there and filled something, and is simply nothing otherwise"
    source: "`execution_manager.py` 1807-1808, then 1811, then 1812-1816"
  - claim: "The three protective prices are the latest amend request's where there is one, and the start's own where there is none"
    source: "`execution_manager.py` 1818, then 1822 into 1823-1825, or 1826 into 1827-1829"
  - claim: "It comes back with its protection placed, its state unknown, at the phase's version, the old list as its protection and the new as a replacement still owing, and the phase's moment as when it became unknown"
    source: "`execution_manager.py` 1831-1839"
  - claim: "Where the bracket resume would have stopped for an entry that filled nothing, and would have worked the prices out from the command, this road does neither"
    source: "`execution_manager.py` 1812-1816, against 1693 into 1697, and 1827-1829, against 1706 into 1707-1708"
---
# What a protection of unknown fate is rebuilt as

A protection whose fate the record never settles is rebuilt as exactly that — placed, with its state unknown — so the watchdog can ask the venue which of two lists it is really holding.

## Which commands reach this road

Those whose latest protection record is neither an active nor a failed one. An active or failed record clears the unresolved phase, so what is left is a command that recorded a request or a halt and nothing after it.

A command the bracket resume already rebuilt is passed over, as is one with no start recorded, and one that will not rebuild from its start.

## The two lists it carries

Its protection name is the old list, and the new list is carried as a replacement still owing — both taken from the phase, along with its version and the moment it became unknown.

The three protective prices are the latest amend request's where there is one, and the start's own where there is none. The average entry price is taken where the entry's order is there and filled something.

## Where it parts from the ordinary bracket resume

Two places. An entry that filled nothing stops [the ordinary resume](what-stops-a-bracket-being-resumed.md) and does not stop this one — it simply leaves the average price empty. And the three prices are read from the record here, where the ordinary resume works them out from the command when no amend matches.

So a bracket whose protection is in doubt comes back with prices someone recorded, and one whose protection is resting may come back with prices worked out afresh.

## Related

- [What stops a bracket being resumed](what-stops-a-bracket-being-resumed.md)
- [What a resumed bracket's protection is taken from](what-a-resumed-brackets-protection-is-taken-from.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
