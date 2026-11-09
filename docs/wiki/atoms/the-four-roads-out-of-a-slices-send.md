---
row: P147-01
baseline: 49aa659
created: 2026-11-15 18:00 UTC
modified: 2026-11-15 18:00 UTC
evidence:
  - claim: "A slice's send is wrapped, and the moment is stamped only once the venue has answered"
    source: "`execution_manager.py` 5991, and 6218"
  - claim: "A timeout or a name the venue already knows sends the slice to be rescued by that name"
    source: "`execution_manager.py` 5992 into 5993-5995, and 6219 into 6220-6222"
  - claim: "A rescue that finds nothing records the send as failed and answers with nothing"
    source: "`execution_manager.py` 5996 into 5997-6000, and 6223 into 6224-6227"
  - claim: "A rescue that finds the order uses it as the answer, and stamps the moment then"
    source: "`execution_manager.py` 6001, then 6002, and 6228, then 6229"
  - claim: "A venue failure records the send as failed without any rescue being attempted"
    source: "`execution_manager.py` 6003 into 6004-6007, and 6230 into 6234"
  - claim: "A parameter the adapter will not take records the send as failed too, saying so"
    source: "`execution_manager.py` 6008 into 6009-6013, and 6235 into 6240"
  - claim: "Past all four the submission is recorded under the answer's own moment and applied"
    source: "`execution_manager.py` 6015-6021, then 6022, then 6023, and 6248, then 6249"
  - claim: "Each fill the answer already carries is then written as a fill of its own, under that same moment"
    source: "`execution_manager.py` 6025, then 6026-6037, and 6251, then 6252-6266"
---
# The four roads out of a slice's send

Sending one slice of a fed-out order has four ways of ending, and the two routines that send slices — one placing at market, one resting at a price — are written the same way through all four.

## The one road that asks again

A timeout, or a name the venue says it already knows, sends the slice to be rescued by that name. A rescue that finds the order uses it as the answer; one that finds nothing records the send as failed.

That is the only road that asks the venue anything further. A venue failure and a parameter the adapter will not take are both recorded as failed without the venue being asked whether an order exists.

So the two failures that might have left an order behind are handled differently from the two that could not have.

## The moment that is stamped

Only once the venue has answered. The submission is recorded under that moment, and so is every fill the answer already carried.

So the record's time for a send is when the answer came back rather than when the send went out, and a slow venue makes the gap invisible in the record.

## What the two routines differ on

The kind of order and the price. Everything else — the wrapping, the four roads, the rescue, the stamping, the submission, and the writing of each immediate fill — is the same in both.

## Related

- [When a send's outcome is unknown](when-a-send-is-unclear.md)
- [How a venue failure is sorted](how-a-venue-failure-is-sorted.md)
- [What a fill changes](what-a-fill-changes.md)
