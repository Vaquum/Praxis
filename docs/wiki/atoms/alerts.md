---
row: P3-20
baseline: 49aa659
created: 2026-09-30 19:11 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A level outside the three is replaced with the middle one rather than refused"
    source: "`alert_sink.py` 48-49 with the three at 20"
  - claim: "Every alert is logged as a warning, whatever level it carries"
    source: "`alert_sink.py` 51"
  - claim: "What is logged is subject to the level the host was started with"
    source: "`launcher.py` 4847-4855"
  - claim: "With no web address given, nothing is sent"
    source: "`alert_sink.py` 60-61"
  - claim: "With one, the same thing is sent there"
    source: "`alert_sink.py` 68"
  - claim: "A failure while sending is logged and goes no further"
    source: "`alert_sink.py` 69-70"
  - claim: "The writing of that log line sits outside the catch"
    source: "`alert_sink.py` 51, against the catch at 67-70"
  - claim: "So does the working-out of the details"
    source: "`alert_sink.py` 63-65"
  - claim: "Some paths log without sending at all, even where an address is set"
    source: "`launcher.py` 3385-3404"
  - claim: "Entering a halted state queues one at the highest level, whatever caused it"
    source: "`launcher.py` 4132 into Nexus `mode_controller.py` 510-511 and 379-380"
  - claim: "It is dropped if the account is no longer halted when the queue drains"
    source: "Nexus `mode_controller.py` 371-377"
  - claim: "An operator halting or resuming raises one a level below, after its saving succeeds"
    source: "`launcher.py` 3562-3565, past the early return at 3548-3552"
  - claim: "Cancelling every order, and closing every position, each raise one too"
    source: "either `launcher.py` 3590-3593 or 3619-3622"
---
# Alerts

An **alert** is how Praxis says something needs a person. Each one writes a log line, marked so whatever watches the logs can pick it out, and where a web address is configured the same thing is sent there.

## Levels, and what they do

Three levels exist. A level outside them is quietly replaced with the middle one rather than refused.

The level travels in the line's contents, but every alert is **logged at the middle level regardless** — so an alert marked highest is written no more loudly than any other, and a host started at a stricter logging level shows none of them while still sending.

## What is guarded

A failure while sending is logged and goes no further. Whatever raised the alert carries on.

That guard covers the sending only. Writing the log line, and working the details into a sendable shape, happen outside it — so an alert carrying a detail that cannot be worked out fails outwards, into whatever raised it.

Some paths log without sending at all, even where an address is set.

## What raises one

Entering a halted state queues one at the highest level, whatever put it there — [poor health](health.md) or a person. It is dropped if the account is no longer halted by the time the queue drains.

An operator halting or resuming an [account](what-an-account-is.md) raises one a level below, but only once the change has been saved. Cancelling every order, and closing every position, each raise one too.

So an operator halt can produce two: the transition, and the action.

## Related

- [Health](health.md)
- [What an account is](what-an-account-is.md)
