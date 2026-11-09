---
row: P122-01
baseline: 49aa659
created: 2026-11-15 05:30 UTC
modified: 2026-11-15 05:30 UTC
evidence:
  - claim: "The record is opened only where a path was given, its folder made where absent, one connection kept on the host, and its shape made sure of before it is handed back"
    source: "`launcher.py` 3123 into 3124-3125, or 3127, then 3128, then 3129, then 3130, then 3133"
  - claim: "Each of the host's three appends stops where the loop or the trading stack is missing, the acknowledgement and the abandonment reporting and returning"
    source: "`launcher.py` 3148 into 3153, and 3190 into 3195"
  - claim: "The delivery record raises there instead"
    source: "`launcher.py` 3231 into 3236"
  - claim: "The acknowledgement builds its event with the host's clock, reads the epoch and the record off the trading stack, hands the append to the Praxis loop and waits ten seconds"
    source: "`launcher.py` 3155-3161, then 3164-3167"
  - claim: "The abandonment does the same"
    source: "`launcher.py` 3197-3203, then 3207-3210"
  - claim: "The delivery record does the same, with nothing wrapped around the handover or the wait"
    source: "`launcher.py` 3238-3252, then 3254-3257"
  - claim: "The other two wrap both and report whatever comes out"
    source: "`launcher.py` 3163 into 3168-3172, and 3206 into 3211-3215"
  - claim: "So a failure writing a delivery record reaches the caller, which undoes the registration and re-raises"
    source: "`launcher.py` 2188 inside 2135, into 2201 into 2206-2207"
---
# Which of the host's appends can stop the work

The host writes three kinds of event to its own record from whatever thread it happens to be on, and one of the three can stop the work that called it.

## Opening the record

Only where a path was given — without one the opening refuses. The folder is made where absent, one connection is kept on the host, and the record's shape is made sure of before the record is handed back.

## What the three share

Each stops at once where the loop or the trading stack is missing. Each builds its event with the host's clock, reads the epoch and the record off the trading stack, hands the append to the Praxis loop from the thread it is on, and waits ten seconds for it.

## Where they part

The acknowledgement and the abandonment report and return when they find nothing to write through, and wrap both the handover and the wait so that whatever comes out is reported and no more.

The delivery record raises instead, and wraps nothing at all.

## What that costs each way

A failure writing an acknowledgement or an abandonment is a line in the log. The outcome is left to be delivered again, or the leg left to be attempted again, at the next start.

A failure writing a delivery record reaches the caller, which undoes the registration and re-raises. The order is not sent.

So the one append that must succeed is the one whose record a restart would need to make sense of an outcome that arrives with nothing in memory to match it.

## Related

- [The event spine](the-event-spine.md)
- [What a delivery record carries](what-a-delivery-record-carries.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
