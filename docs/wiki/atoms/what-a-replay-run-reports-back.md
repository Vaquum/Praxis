---
row: P4-40
baseline: 49aa659
created: 2026-10-03 20:55 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "Work is queued and the name returned without waiting for the run"
    source: "`replay_api.py` 150-155"
  - claim: "Runs go to one worker, so a second run waits for the first"
    source: "`replay_api.py` 105 and 153"
  - claim: "A queued run already reports as running"
    source: "`replay_api.py` 150-151, the three words at 39-41"
  - claim: "The name is answered once, and the run's state only when asked for again"
    source: "`replay_api.py` 155 against 157-166"
  - claim: "A run that raises is kept as failed, and the words of what went wrong are given back"
    source: "`replay_api.py` 108-112 and 284-285"
  - claim: "A name never given out is reported unknown, and no record is ever removed"
    source: "`replay_api.py` 160-164 against 112 and 116"
  - claim: "A finished run's counts come back as numbers and its amounts as text"
    source: "`replay_api.py` 272-281 into `metrics_serialization.py` 27-50 and 57-68"
  - claim: "A figure that is missing comes back as nothing rather than as text"
    source: "`metrics_serialization.py` 18-20"
  - claim: "The distribution figures pass through as numbers, rounded where they were made"
    source: "`metrics_serialization.py` 44-45, rounded at `percentiles.py` 62-64 and `snapshot_result.py` 93-103 and 116-123"
---
# What a replay run reports back

A run [asked for over HTTP](asking-for-a-replay-from-outside.md) is answered once, with a name. What the run has come to is told only when that name is asked after, as often as the asker cares to.

## The name

Work is queued and the name returned without waiting for the run. Runs go to one worker, so a second run waits for the first — but its request still gets its own name straight away, and that run already reports as running.

## The answer afterwards

A run that raises is kept as failed, and the words of what went wrong are given back with the name.

A name never given out is reported unknown. No record is ever removed, so a name stays answerable for as long as the service runs.

## How the figures come across

A finished run's counts come back as numbers and its amounts as text, so nothing is rounded on the way out. A figure that is missing comes back as nothing at all, rather than as a nought or as the word.

The distribution figures are the exception. They pass through as numbers, already rounded where they were worked out.

## Related

- [Asking for a replay from outside](asking-for-a-replay-from-outside.md)
- [What a replay reports](what-a-replay-reports.md)
