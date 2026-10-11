---
row: P3-21
baseline: 49aa659
created: 2026-09-30 18:44 UTC
modified: 2026-10-11 19:43 UTC
evidence:
  - claim: "Three answers are possible: the venue, Praxis, or unknown"
    source: "`praxis/core/domain/enums.py` 28-30"
  - claim: "A refusal raised before any send is put down to Praxis"
    source: "`classify_submit_failure.py` 60-61, that kind raised at `binance_adapter.py` 1194-1234 from 1520, before the send built past it"
  - claim: "A refusal the venue sent is put down to the venue, with its code kept"
    source: "`classify_submit_failure.py` 63-64"
  - claim: "A duplicate-name refusal is the venue's"
    source: "`classify_submit_failure.py` 66-72"
  - claim: "Its code is recovered only where what raised it was itself a venue refusal"
    source: "`classify_submit_failure.py` 68-70"
  - claim: "The adapter raises that kind from one rejection code, whatever the reason behind it"
    source: "`binance_adapter.py` 1644-1651"
  - claim: "A send timeout and a general transport failure are unknown"
    source: "`classify_submit_failure.py` 74-75"
  - claim: "Any other venue failure is the venue's, with no code"
    source: "`classify_submit_failure.py` 77-78"
  - claim: "That branch catches a missing credential, raised before anything is sent"
    source: "`binance_adapter.py` 483 and 721"
  - claim: "A bad-value failure is Praxis's, including one raised while reading a reply"
    source: "`classify_submit_failure.py` 80-84, such a failure raised at `binance_adapter.py` 897"
  - claim: "A failure of an unrecognised kind is unknown, and so is none at all"
    source: "`classify_submit_failure.py` 80-84, which nothing supplied also reaches"
  - claim: "A caller may supply the answer itself, overriding what would be worked out"
    source: "`execution_manager.py` 5455-5462, used at 4962"
---
# Who refused a send

When a send fails, Praxis records **which side refused it**, so that what reads the record afterwards need not judge from the wording. There are three answers: the venue, Praxis, or unknown.

The answer is usually worked out from the kind of failure. A caller may also supply it outright, and what it supplies stands.

## How it is worked out

A refusal raised before the send is built is Praxis's. One the venue sent is the venue's, with the code the venue gave kept alongside.

A duplicate-name refusal is the venue's. Its code survives only where what raised it was itself a venue refusal; otherwise none is kept. The adapter raises that kind from one rejection code whatever lay behind it, so the label is surer than the reason.

Any other failure from the venue's family is the venue's, with no code — including a missing credential, which is raised before anything is sent at all. So this answer does not prove the venue was reached.

A bad-value failure is Praxis's. That covers a setting refused before sending, and also a reply Praxis could not make sense of after the venue answered — both come out as Praxis's.

## When nothing can be said

A send timeout and a general transport failure are marked unknown. So is a failure of a kind that says nothing about a side, and so is a call made with no failure at all.

Those are left unknown rather than guessed at.

## Related

- [When a send's outcome is unknown](when-a-send-is-unclear.md)
- [What a refusal says](what-a-refusal-says.md)
