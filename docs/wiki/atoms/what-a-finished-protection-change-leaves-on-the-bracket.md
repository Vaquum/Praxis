---
row: P167-01
baseline: 49aa659
created: 2026-11-16 04:00 UTC
modified: 2026-11-16 04:00 UTC
evidence:
  - claim: "The fills the venue gave as it took the pair are recorded against the closing command"
    source: "`execution_manager.py` 9769, then 9770-9785, the command named at 9777"
  - claim: "Only a fill the record answered with a place is carried into the figures"
    source: "`execution_manager.py` 9786, then 9787 into 9788"
  - claim: "The pair is then recorded active"
    source: "`execution_manager.py` 9790-9796, then 9797"
  - claim: "The bracket's live pair name and its three current prices are written over, and the standing moved to active"
    source: "`execution_manager.py` 9798, then 9799, then 9800, then 9801, then 9802"
  - claim: "The four figures the change was parked with are cleared earlier, before this ending is reached"
    source: "`execution_manager.py` 9744, then 9745, then 9746, then 9747, before 9798"
  - claim: "A replacement the venue reports as already ended stops short of all this, the pair's name written on the bracket but the standing left unknown"
    source: "`execution_manager.py` 9749, then 9756, then 9757, then 9758, then 9759, then 9767"
---
# What a finished protection change leaves on the bracket

A protection change that reaches its end makes the replacement pair the bracket's live one, by writing over the four figures the old pair was described by.

## The fills that came with it

The fills the venue gave as it took the pair are recorded against the closing command, and only a fill the record answered with a place is carried into the figures. A pair can fill as it is placed, and those fills belong to the closing side of the trade rather than the entry.

## The writing over

The pair is recorded active. Then the bracket's live pair name and its three current prices are written over with the new ones, and the standing moved to active.

The four figures [the change was parked with](what-a-protection-change-writes-on-the-bracket.md) are cleared earlier, before this ending is reached. Between the clearing and the writing over, the bracket still names the old pair as its live one and carries the old pair's prices.

## The ending that stops short

A replacement the venue reports as already ended stops before any of it: the pair's name is written on the bracket, and the standing left unknown with the moment stamped. The prices stay as the old pair's, which is what [the watch](when-protection-is-lost.md) finds when it comes round.

## Related

- [What a protection change writes on the bracket](what-a-protection-change-writes-on-the-bracket.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [When protection is lost](when-protection-is-lost.md)
