---
row: N55-01
baseline: 49aa659
created: 2026-11-08 17:57 UTC
modified: 2026-11-08 17:57 UTC
evidence:
  - claim: "Four figures a fill carries are checked for being there by assertion, which ends the work rather than answering"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 217-220, asserted again at 445-446 and 458-461"
  - claim: "The record a fill arrives as refuses one lacking any of the four, so none can be missing by the time the assertions run"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 183-185, or 195-197, or 207-209, or 222-224"
  - claim: "The capital side is called before the position is touched, an entry's fill going one way and an exit's another"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 224-230, or 242-247, both ahead of 256-258"
  - claim: "A capital call that does not succeed is answered as a failure carrying the capital side's own reason, on either road"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 232-237, or 248-253"
  - claim: "Only past that does an entry fill naming no trade raise"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 463-465, reached from 256-258"
  - claim: "And one naming a trade the state holds no position for raises there too"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 467-471"
---
# The figures a fill is assumed to carry

Processing a fill reads four figures — the size filled, the price, what that came to, and the fees paid — and checks for them by assertion rather than by a test it could answer with.

## Where the assumption is kept

On the other side of the handoff. [The record a fill arrives as](what-a-fill-must-carry.md) refuses one lacking any of the four, and refuses each for being the wrong kind, not finite, or outside its bounds.

So nothing missing can reach the assertions. They stand as a statement of what the record has already made true, and a fill that somehow lacked one would end the work rather than be answered.

## What happens before the position is touched

The capital side is called first: an entry's fill one way, an exit's another. A call that does not succeed is answered as a failure carrying the capital side's own reason — and that happens on either road, before any position is read.

## The two failures past it

Only past that is the position touched. An entry fill naming no trade raises there, and so does one naming a trade the state holds no position for.

So a fill that cannot be applied is answered where the money is concerned and raises where the position is: the same fill meets a returned failure first and an ended turn second, and which it meets depends on which call fails.

## Related

- [What a fill must carry](what-a-fill-must-carry.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What a tracked order must be](what-a-tracked-order-must-be.md)
