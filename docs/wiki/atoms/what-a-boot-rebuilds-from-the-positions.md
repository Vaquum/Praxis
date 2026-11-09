---
row: N3-05
baseline: 49aa659
created: 2026-10-22 15:40 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "Where the live positions are handed in, each strategy's deployed figure is worked out again from them and replaces what was carried over"
    source: "`nexus/core/capital_controller/capital_controller.py` 214-272"
  - claim: "Money set aside adds to the asking strategy's figure as it is set aside, unless the sum lands within a millionth of a millionth of nought, which drops it"
    source: "`nexus/core/capital_controller/capital_controller.py` 419-420 into 1097-1098 and 1115, dropped instead at 1100-1101, the amount at `nexus/core/domain/capital_state.py` 16"
  - claim: "Clearing the three stranded totals touches no strategy's figure, which stands as it was"
    source: "`nexus/core/capital_controller/capital_controller.py` 193-212"
  - claim: "Money set aside is refused while those figures do not add up to the account's total deployed"
    source: "`nexus/core/capital_controller/capital_controller.py` 340-365"
  - claim: "A position's contribution is its size at its cost basis"
    source: "`nexus/core/capital_controller/capital_controller.py` 258-261"
  - claim: "A position still carrying a pending sale has it set to nought"
    source: "`nexus/core/capital_controller/capital_controller.py` 216-233"
  - claim: "A sale larger than the position less what is pending on it is refused at the intake stage, which stands first in the order the walk is handed"
    source: "`nexus/core/validator/intake_stage.py` 278-284, intake standing first in the order at `nexus/core/validator/pipeline_models.py` 50-56, which the walk the host builds is handed at `praxis/launcher.py` 1010"
  - claim: "A position with no cost basis is weighed at the price it was entered at"
    source: "`nexus/core/capital_controller/capital_controller.py` 235-248"
  - claim: "Where that is nought too the cost basis is left at nought, so the position adds nothing to the figure"
    source: "`nexus/core/capital_controller/capital_controller.py` 235-238 into 258-261"
  - claim: "A position in that state is logged as one the figure will come out short of"
    source: "`nexus/core/capital_controller/capital_controller.py` 250-257"
  - claim: "A rebuilt figure that differs from the one carried over is logged with both"
    source: "`nexus/core/capital_controller/capital_controller.py` 263-269"
  - claim: "Handing the positions in is optional in the code"
    source: "`nexus/core/capital_controller/capital_controller.py` 214"
  - claim: "The one caller outside the tests hands them in"
    source: "`praxis/launcher.py` 4101"
---
# What a boot rebuilds from the positions

A rebuild works each strategy's committed money out again from the positions that are actually there, in the same pass that [writes off what is stranded](what-a-boot-finds-stranded.md).

## Why it has to happen

Money set aside adds to the asking strategy's figure as it is set aside — unless the sum lands within a millionth of a millionth of nought, which drops it — so writing off the stranded totals leaves that figure standing, still counting what was just cleared. Money set aside is then refused while the strategies' figures and the account's total [disagree](what-the-deployed-figures-out-of-step-refuse.md). This rebuild is what brings the per-strategy side of that sum back to the positions.

## What the pass does to each position

A position still carrying a pending sale has it set to nought. That figure is subtracted from the position's size at the intake stage, which stands first in the order the walk is handed, and a sale larger than what is left is refused there.

A position contributes its size at its cost basis. One whose cost basis is missing is weighed at the price it was entered at instead. Where that is missing too the basis stays at nought, so the position contributes nothing, and a line is logged saying the figure will come out short.

The figures are then replaced wholesale. One that differs from what was carried over is logged with both, so the correction is visible.

## The half that never runs

Handing the positions in is optional in the code, and every caller outside the tests hands them in. The shorter pass — the three totals cleared and nothing rebuilt — is not one the running system takes.

## Related

- [What a boot finds stranded](what-a-boot-finds-stranded.md)
- [What each check weighs](what-each-check-weighs.md)

---

Created 2026-10-22 15:40 UTC · Last modified 2026-10-23 07:08 UTC
