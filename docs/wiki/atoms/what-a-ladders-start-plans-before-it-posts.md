---
row: P155-02
baseline: 49aa659
created: 2026-11-15 22:00 UTC
modified: 2026-11-16 13:30 UTC
evidence:
  - claim: "The parameters are insisted upon as a ladder's and the amount as present"
    source: "`execution_manager.py` 6085, then 6086"
  - claim: "The venue's remembered rules give the lot step, and nothing where none are held"
    source: "`execution_manager.py` 6088, then 6089, then 6090"
  - claim: "The levels are planned from the parameters, the whole amount and that step"
    source: "`execution_manager.py` 6092-6093, the report made and the start abandoned at 6096-6102, then 6103"
  - claim: "A planning that refuses is reported and the command ended as rejected, its slice total named as the count of prices the parameters held"
    source: "`execution_manager.py` 6094 into 6096-6101, the total at 6100"
  - claim: "Otherwise a start is recorded naming the planned count as its slice total and nought as its interval"
    source: "`execution_manager.py` 6105-6119, the count at 6114, the interval at 6115"
  - claim: "It carries the weights the parameters held, or an empty set where they held none, and the prices as given"
    source: "`execution_manager.py` 6117, then 6118"
  - claim: "The start is written to the record and applied, and only then is the live ladder built from the planned levels"
    source: "`execution_manager.py` 6120, then 6121, then 6123-6125"
---
# What a ladder's start plans before it posts

A ladder works out every rung's amount and price before it records anything, so a grid that cannot be planned is refused without a start being written at all.

## What the planning needs

The venue's remembered rules, for the lot step — and nothing at all where no rules are held, in which case the levels are planned against no step.

The parameters' prices and weights, and the command's whole amount.

## What a refusal reports

A planning that refuses ends the command as rejected, and names as its slice total the count of prices the parameters held rather than the count actually planned — there being no planned count to name.

## What a start records

The planned count as its slice total, and nought as its interval: a ladder posts all its rungs at once and has no schedule.

The weights the parameters held, or an empty set where they held none, and the prices as given. So the start carries what was asked for alongside the count that was achievable.

## The order

The start is written to the record and applied, and only then is the live ladder built from the planned levels. So the record holds the ladder's shape before anything in memory describes it.

## Related

- [How a ladder's rungs are found again](how-a-ladders-rungs-are-found-again.md)
- [What stops a scheme being resumed](what-stops-a-scheme-being-resumed.md)
- [What a ladder's change is refused for](what-a-ladders-change-is-refused-for.md)
