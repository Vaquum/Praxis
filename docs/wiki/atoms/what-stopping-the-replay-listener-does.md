---
row: P14-02
baseline: 49aa659
created: 2026-11-08 14:25 UTC
modified: 2026-11-08 15:12 UTC
evidence:
  - claim: "Stopping the listener shuts the worker pool down, waiting for the replay in progress and cancelling whatever is still queued when it runs"
    source: "`replay_api.py` 168-169, attached to the app's cleanup at 174"
  - claim: "Runs go to a pool of one worker, made as the app is"
    source: "`replay_api.py` 105"
  - claim: "A record is set to running where the work is queued, and only the worker's own function writes it again"
    source: "`replay_api.py` 150-151 against 107-116"
---
# What stopping the replay listener does

Bringing the [replay service](asking-for-a-replay-from-outside.md) down shuts the worker [runs](what-a-replay-run-reports-back.md) are given to, and the run in progress and the runs queued behind it are treated differently.

## Waiting, and cancelling

The shutdown is attached to the app's cleanup, so it runs as the server comes down. It waits for the replay already under way to finish, and it cancels whatever is still queued at that moment.

Runs go to one worker, so a run accepted while another is running waits its turn. Whether it is dropped turns on where the worker has got to by the time the server comes down: one the worker has already begun is waited for, one still waiting is cancelled.

## What a dropped run's record says

A record is set to running where the work is queued, before the worker reaches it. The only thing that ever writes that record again is the function the worker runs.

A cancelled run never reaches that function. Its record therefore stays at running — for as long as anything can still ask, which is until the service is gone.

## Related

- [What a replay run reports back](what-a-replay-run-reports-back.md)
- [The moments a replay request names](the-moments-a-replay-request-names.md)
