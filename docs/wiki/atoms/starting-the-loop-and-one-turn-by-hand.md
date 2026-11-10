---
row: N71-07
baseline: 49aa659
created: 2026-11-08 21:14 UTC
modified: 2026-11-08 21:14 UTC
evidence:
  - claim: "Starting answers at once where the loop is already up, under the lock"
    source: "`nexus/strategy/predict_loop.py` 233-235"
  - claim: "It then raises the flag, clears the event a stop uses, and gives every pairing a first due moment its own interval ahead of now"
    source: "`nexus/strategy/predict_loop.py` 237, then 238, then 240-244"
  - claim: "So no pairing is served at the moment of starting, each waiting out its own interval first"
    source: "`nexus/strategy/predict_loop.py` 241-244, every moment set ahead of now"
  - claim: "Each pairing's interval is its own, so the pairings come due independently of each other"
    source: "`nexus/strategy/predict_loop.py` 242, reading each binding's own interval"
  - claim: "One thread is then made and started, marked so it cannot keep the program alive"
    source: "`nexus/strategy/predict_loop.py` 246-251"
  - claim: "A turn asked for by hand refuses while the loop is up, the reading of the flag taken under the lock"
    source: "`nexus/strategy/predict_loop.py` 277-280"
  - claim: "The lock is let go before that turn runs, so the refusal is a guard against being called wrongly rather than a barrier against the loop starting meanwhile"
    source: "`nexus/strategy/predict_loop.py` 282, standing outside 277"
  - claim: "That turn schedules nothing after itself and hands a failure to its caller, where the loop's own turn has its failure logged and goes on"
    source: "`nexus/strategy/predict_loop.py` 282, against 307-322"
---
# Starting the loop, and one turn by hand

The loop that reads predictions has two ways in: it can be set running, or asked for a single turn.

## Setting it running

Starting answers at once where the loop is already up, so asking twice is harmless.

Otherwise it raises the flag, clears the event a stop uses, and gives every pairing of a strategy and a series a first due moment its own interval ahead of now.

So no pairing is served at the moment of starting. Each waits out its own interval, and the intervals are each the pairing's own — so the pairings come due independently and a loop running briefly may serve some and not others.

One thread is then made and started, marked so it cannot keep the program alive on its own.

## One turn by hand

A single turn can be asked for directly. It refuses while the loop is up, the reading of the flag taken under the lock.

The lock is let go before the turn runs. So the refusal guards against being called wrongly, and not against the loop being started while the turn is in flight.

That turn schedules nothing after itself.

## The difference that matters

A turn asked for by hand hands a failure to its caller. The loop's own turn has its failure logged, sets its next due moment, and goes on to the next pairing.

So the same turn, reached two ways, treats a failure two ways.

## Related

- [What the prediction loop's stop leaves running](what-the-prediction-loops-stop-leaves-running.md)
- [Which prediction row is used](which-prediction-row-is-used.md)
