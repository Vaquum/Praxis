---
row: P123-01
baseline: 49aa659
created: 2026-11-09 09:42 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "Each sweep weighs the operator's credentials first and answers with whatever refusal that gives"
    source: "`launcher.py` 3570, then 3572 into 3573, and 3598, then 3600 into 3601"
  - claim: "Each then resolves the account's runtime and answers with whatever refusal that gives"
    source: "`launcher.py` 3575, then 3577 into 3578, and 3603, then 3605 into 3606"
  - claim: "Past those refusals each insists the runtime is there, and reads the account's name off it rather than off the request"
    source: "`launcher.py` 3580, then 3582, and 3608, then 3610"
  - claim: "Cancelling everything sweeps under a wrapping of its own and answers the account's name beside the names it cancelled"
    source: "`launcher.py` 3584, then 3585, then 3595"
  - claim: "Closing everything cancels first and closes after, inside one wrapping"
    source: "`launcher.py` 3612, then 3613, then 3614"
  - claim: "A failure anywhere in either sweep is reported and answered as a named error at five hundred"
    source: "`launcher.py` 3586 into 3587-3588, and 3615 into 3616-3617"
  - claim: "A sweep that answers tells the alert sink at warning, with its counts"
    source: "`launcher.py` 3590-3593, and 3619-3622"
  - claim: "So a failure in the closing loses the cancelling's own answer, the aborts having already gone out"
    source: "`launcher.py` 3613 before 3614, into 3615 into 3617, past 3624-3626"
---
# What the operator's two sweeps answer with

An operator can ask an account to cancel everything it has working, or to cancel everything and close what it holds, and the two asks are answered the same way.

## What both do first

Weigh the operator's credentials, and answer with whatever refusal that gives. Then resolve the account's runtime, and answer with whatever refusal that gives.

Past those refusals each insists the runtime is there, and reads the account's name off it rather than off the request — so the name in the answer is the one the host resolved.

## What each answers

Cancelling everything answers the account's name beside the names it cancelled.

Closing everything cancels first and closes after, and answers the account's name beside both lists.

## What a failure costs

A failure anywhere in either sweep is reported and answered as a named error at five hundred. [The alert sink](alerts.md) is told only where the sweep answered, at warning, carrying its counts.

Closing everything runs both sweeps inside one wrapping. So a failure in the closing half loses the cancelling half's answer too — and the aborts it describes have already gone out. An operator who sees that error knows that cancelling may have happened and cannot tell from the answer what it reached.

## Related

- [Alerts](alerts.md)
- [What a sweep does to each item](what-a-sweep-does-to-each-item.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
