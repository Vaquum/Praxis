---
row: N7-04
baseline: 49aa659
created: 2026-10-27 09:30 UTC
modified: 2026-10-27 11:50 UTC
evidence:
  - claim: "An exit naming a trade the record has no position for is logged and answered with nothing, before any of that position's own figures are read"
    source: "`praxis/launcher.py` 1282-1291 before 1293"
  - claim: "Answering with nothing there has the submission record that request as invalid, and the walk is never asked"
    source: "`nexus/strategy/action_submit.py` 224-238 before 242, on the nothing returned at `praxis/launcher.py` 1291"
  - claim: "The size asked for is read off the request, and what the position has left is its size less what is already pending on it"
    source: "`praxis/launcher.py` 1305 and 1307"
  - claim: "Whether this is a full close is settled there by comparing the size asked with that figure"
    source: "`praxis/launcher.py` 1308"
  - claim: "A command identifier comes off the request, or is minted on the spot where the request carries none"
    source: "`praxis/launcher.py` 1306"
  - claim: "The venue is then asked to fit the size, at the position's entry price, as a market order where the request names no kind of order"
    source: "`praxis/launcher.py` 1310-1321"
  - claim: "Any refusal from that fitting ends the working out and nothing is built for the checks to read"
    source: "`praxis/launcher.py` 1323 into 1369"
  - claim: "On the way out of that refusal the dust road is taken, where the close was whole, nothing is pending on the position, and a processor is to hand"
    source: "`praxis/launcher.py` 1339-1342 into 1363-1367"
  - claim: "The protective exit Praxis puts up for a bracketed entry is marked a full close outright, with no such comparison made"
    source: "`praxis/launcher.py` 1587, built for an entry at 2194-2200"
---
# What Praxis works out for an exit

Praxis works a strategy's exit over from the record it keeps before [the checks](the-checks-a-decision-passes.md) see any of it: that the position is there, what that position has left, whether this is a full close, a name for the command, and a size the venue will take.

## The position must be there

An exit naming a trade the record has no position for is logged and answered with nothing, before any of that position's own figures are read. The submission then records that request as invalid, and [the walk](what-each-check-weighs.md) is never asked.

## What the position has left

The position's size, less [what is already pending on it](what-a-pending-sale-is.md) — so a second exit is measured against what the first has not yet taken. Whether this is a full close is settled there, by comparing the size asked with that figure. [The protective exit Praxis puts up](protection.md) for a bracketed entry is marked a full close outright instead, with no such comparison made.

## A name for it

The command identifier comes off the request, or is minted on the spot where the request carries none, so the command has a name before the checks weigh it.

## Fitting the size

The venue is then asked to fit the size, at the position's entry price, as a market order where the request names no kind. Any refusal from that fitting ends the working out and nothing is built for the checks to read. On the way out of that refusal [the dust road](where-a-positions-last-scraps-go.md) is taken, where the close was whole, nothing is pending on the position, and a processor is to hand.

## Related

- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)
- [What a pending sale refuses](what-a-pending-sale-refuses.md)

---

Created 2026-10-27 09:30 UTC · Last modified 2026-10-27 11:50 UTC
