---
row: P174-01
baseline: 49aa659
created: 2026-11-16 07:30 UTC
modified: 2026-11-16 13:00 UTC
evidence:
  - claim: "A copy of the live children is walked, so the set can be changed as it goes"
    source: "`execution_manager.py` 6445, then 6447"
  - claim: "A name the record holds no order for is dropped from the live set"
    source: "`execution_manager.py` 6448, then 6449, then 6450, then 6451"
  - claim: "A name the venue does not know is left in the live set"
    source: "`execution_manager.py` 6459, then 6460"
  - claim: "Any other venue failure leaves it there too"
    source: "`execution_manager.py` 6461, then 6468"
  - claim: "Only a cancel the venue confirmed writes the call-off down and drops the name"
    source: "`execution_manager.py` 6470-6476, then 6477, then 6478, then 6479"
  - claim: "The live set standing non-empty is what keeps the work from being settled"
    source: "`execution_manager.py` 6355, then 6356, reached from 7068, then 7069"
  - claim: "A drain passes over work whose live set is empty, so the calling off is attempted only while names remain"
    source: "`execution_manager.py` 7052-7056, then 7057, the moment taken at 7059 and the retry stamped at 7064, then 7065-7067"
---
# What calling off a scheme's children leaves behind

Calling off the still-working children of [work fed out over time](work-fed-out-over-time.md) is attempted for each of them, and a child that cannot be called off stays on the live list.

## What is walked

A copy of the live children, so the set itself can be changed as the walk goes.

## The two names that come off

A name the record holds no order for comes off at once — there is nothing to call off, and nothing to wait for either.

A name whose cancel the venue confirmed comes off once the call-off is written down.

## The two that stay

A name the venue does not know, and a name whose cancel failed any other way. Both stay on the live list, and a child left there settles through its own fill or expiry instead.

The live list standing non-empty is what keeps the work from being settled: the settling is attempted straight after the calling off, and it does nothing while a name remains. A drain in turn passes over work whose list is already empty, so the calling off is attempted only while there is something on it.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What is cleared before a scheme's ending is written](what-is-cleared-before-a-schemes-ending-is-written.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
