---
row: P136-01
baseline: 49aa659
created: 2026-11-09 10:41 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Only the ladder starts are walked, from the set the history pass keeps for them alone"
    source: "`execution_manager.py` 1313, reaching 1218 into 1219"
  - claim: "A terminal outcome, a state that is anything but running, or fewer price levels than the minimum each pass a ladder over"
    source: "`execution_manager.py` 1314, or 1317, then 1319 into 1320, or 1322 into 1323"
  - claim: "A command that will not rebuild from its start is reported and passed over"
    source: "`execution_manager.py` 1325-1326, then 1327 into 1331, the rebuilding it attempts at 1557, reaching 1530"
  - claim: "Where no amend was in flight, the generation, the parameters and the grid size come from the completed amend, or from nought, the command's own and the start's count where none completed"
    source: "`execution_manager.py` 1355-1357"
  - claim: "Each rung's name is worked out again from the mode, the command, the rung's place and the generation"
    source: "`execution_manager.py` 1499, then 1500-1502"
  - claim: "A name the account holds no order for counts as a rung never posted, one it holds counts as posted, and one whose status is not terminal counts as still working"
    source: "`execution_manager.py` 1498, then 1503, then 1504 into 1505, or 1507, then 1508 into 1509"
  - claim: "The cursor a ladder comes back with is that count of posted rungs"
    source: "`execution_manager.py` 1359-1360, into 1511, read at 1367"
  - claim: "It comes back with no slice plan and no interval"
    source: "`execution_manager.py` 1364, then 1366, then 1369"
  - claim: "The same tail follows as for a scheme: the terminal answer carried, a draining ladder marked as owing its cancels, and the ladder registered with its command installed, its owner noted and the trade's name recorded"
    source: "`execution_manager.py` 1378, then 1379-1380, then 1383, then 1384, then 1385, then 1386"
---
# How a ladder's rungs are found again

A ladder posts all its resting rungs at once when it starts, so resuming one does not replan or resend anything — it works out what each rung was called and asks the account whether that order is still there.

## Which ladders are tried

Only the ladder starts, taken from [the set the history pass keeps for them alone](what-one-pass-gathers-for-the-schemes.md). A terminal outcome, a state that is anything but running, or fewer price levels than the minimum each pass one over, and a command that will not rebuild from its start is reported and passed over.

## The names worked out again

Each rung's name is worked out from the mode, the command, the rung's place in the grid and the generation — the same working-out that named it when it was posted.

A name the account holds no order for counts as a rung never posted. One it holds counts as posted. One whose status is not terminal counts as still working.

So the cursor a ladder comes back with is a count of how many rungs were found rather than a figure read from the record. A rung the venue accepted but the record never saw is still found; a rung the record saw but the venue lost is not.

## What it comes back without

No slice plan and no interval. A ladder has no schedule to resume — its rungs are already out there — so the fields a fed-out scheme lives by are left empty.

## Related

- [What one pass gathers for the schemes](what-one-pass-gathers-for-the-schemes.md)
- [What a resumed scheme comes back holding](what-a-resumed-scheme-comes-back-holding.md)
- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
