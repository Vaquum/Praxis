---
row: P181-01
baseline: 49aa659
created: 2026-11-16 11:00 UTC
modified: 2026-11-16 11:00 UTC
evidence:
  - claim: "The record of events, the epoch it writes under, the venue's adapter and the slippage cap are each kept as handed over"
    source: "`execution_manager.py` 677, then 678, then 679, then 680"
  - claim: "The modes the host may drive are kept with the plain single order always added to them, and nothing is kept where none are named"
    source: "`execution_manager.py` 681-685"
  - claim: "The way an outcome is handed on, the clock, the answer to a lost protection, the way a remediation is handed on, and the deadline a restore waits out are all kept as handed over too"
    source: "`execution_manager.py` 686, then 687, then 688, then 689, then 690"
  - claim: "The host hands in all ten"
    source: "`trading.py` 224-235"
  - claim: "Two of the ten can be replaced after the building"
    source: "`execution_manager.py` 724, and 738"
  - claim: "A helper of the module's own answers the current moment in universal time"
    source: "`execution_manager.py` 222"
  - claim: "Nine stores are made empty beside them, and the remembered loop thread starts absent"
    source: "`execution_manager.py` 691, and 692, and 693, and 694, and 695, and 696, and 697, and 698, and 699, then 700"
---
# What the manager is built holding

The manager is built holding ten things handed in and ten of its own made empty, and the host hands in all ten of the first kind.

## Handed in

The record of events and the epoch it writes under. The venue's adapter. The slippage cap. The modes it may drive. The way an outcome is handed on and the way a remediation is handed on. The clock. The answer to a lost protection. And the deadline a restore waits out.

Each is kept as handed over, with one exception: [the modes](ways-of-working-a-host-may-drive.md) are kept with the plain single order always added to them, and nothing is kept at all where none are named.

## Replaceable afterwards

Two of the ten — the way an outcome is handed on, and the way a remediation is handed on — can be replaced after the building. So a host can be built before the thing that listens to it is ready.

## Its own, empty

Nine stores: the remediations owing, the accounts, the commands accepted, the commands ended, the budgets, the snapshot of what may be changed, the commands themselves, the call-offs standing, and the trade each command belongs to. And the remembered [loop thread](which-thread-the-manager-will-take-work-from.md), which starts absent.

A helper of the module's own answers the current moment in universal time; the clock the manager stamps with is whatever was handed in.

## Related

- [Ways of working a host may drive](ways-of-working-a-host-may-drive.md)
- [Which thread the manager will take work from](which-thread-the-manager-will-take-work-from.md)
- [What an account is](what-an-account-is.md)
