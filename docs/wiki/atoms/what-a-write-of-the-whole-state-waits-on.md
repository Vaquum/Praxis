---
row: P6-04
baseline: 49aa659
created: 2026-11-06 15:07 UTC
modified: 2026-11-07 00:00 UTC
evidence:
  - claim: "The lock placed in the pair as its second half is the money's own, made once as the money is built and handed out by a reading that returns it"
    source: "`nexus/core/capital_controller/capital_controller.py` 107 returned at 127, put in the pair at `praxis/launcher.py` 2580"
  - claim: "The guard takes that lock under a test, and takes nothing where there is no pair"
    source: "`nexus/infrastructure/state_store.py` 221 under the test at 219, which otherwise leaves 220-221 unreached"
  - claim: "Ten of the money's own roads take that same lock"
    source: "`nexus/core/capital_controller/capital_controller.py` 181, 326, 511, 546, 610, 663, 768, 875, 992 and 1055"
  - claim: "The road that sets money aside raises five refusals before taking it at all"
    source: "`nexus/core/capital_controller/capital_controller.py` 302-304, or 306-308, or 312-314, or 316-318, or 320-322, each of them before 326"
  - claim: "Once it has the lock it holds it across the clearing out of what has expired and whichever ending is reached"
    source: "`nexus/core/capital_controller/capital_controller.py` 326 holding 327, which reaches the clearing at 480-491, and then a refusal at 362, or one at 370, or one at 379, or one at 388, or one at 399, or the record at 408-415 with the figures set at 417-420 and the answer at 422"
  - claim: "That road asks for no store write of any kind, and outside the tests it is reached from one line"
    source: "`nexus/core/validator/capital_stage.py` 52, its only caller outside `tests/`, reaching `nexus/core/capital_controller/capital_controller.py` 326, with no call to `nexus/infrastructure/state_store.py` 178, 198 or 236 anywhere under `nexus/core/validator/`, nor on the road from `nexus/core/capital_controller/capital_controller.py` 326 to 422"
---
# What a write of the whole state waits on

Once the pair of locks has been handed over, the guard takes the lock the account's money works under, so a write that enters it waits on whichever of the money's own roads is holding that lock. [Which of the store's writes enter that guard](which-of-the-stores-writes-take-which-locks.md) is another article's subject.

## The lock it shares

That lock is the money's own, made once as the money is built and handed out by a reading that returns it, and it stands in the pair as its second half. The guard takes it under a test, and where [no pair has been handed over](when-the-store-writes-without-its-locks.md) it takes nothing at all.

## The roads on the other side

Ten of the money's own roads take that same lock. The road that [sets money aside](how-nexus-sets-money-aside.md) raises five refusals before taking it at all; once it has the lock it holds it across the clearing out of what has expired and whichever ending is reached — a further refusal, or the record written and the figures set.

## A road that writes nothing

That road asks for no store write of any kind. Outside the tests it is reached from one line, [the stage that weighs a request against the money](what-each-check-weighs.md), so a road that writes nothing itself can still hold a write out.

## Related

- [When the store writes without its locks](when-the-store-writes-without-its-locks.md)
- [Which of the store's writes take which locks](which-of-the-stores-writes-take-which-locks.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
