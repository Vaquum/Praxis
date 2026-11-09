---
row: P140-01
baseline: 49aa659
created: 2026-11-15 14:30 UTC
modified: 2026-11-15 14:30 UTC
evidence:
  - claim: "Admitting refuses where it is called from a thread other than the loop's, and only where a loop thread was recorded at all"
    source: "`execution_manager.py` 3168-3171 into 3176"
  - claim: "It refuses where the account is not registered"
    source: "`execution_manager.py` 3178, then 3179 into 3180-3181"
  - claim: "It refuses where the account has fail-stopped, and again where it failed its startup and stays parked"
    source: "`execution_manager.py` 3183 into 3184-3185, or 3187 into 3192"
  - claim: "A recovery admission refuses where the account is not parked, which is the one refusal that asks for a state rather than against one"
    source: "`execution_manager.py` 3194, then 3195 into 3200"
  - claim: "A recovery admission then appends and projects at once, and puts the event on the dispatch queue only where a sequence came back"
    source: "`execution_manager.py` 3202, then 3204 into 3205, then 3207"
  - claim: "Any other admission makes a promise, puts the event and that promise on the admission queue, wakes the worker, and waits on the promise"
    source: "`execution_manager.py` 3209-3211, then 3212, then 3214"
---
# What admitting an event refuses

Admitting an event is how anything reaches an account's record, and it turns away four things before deciding which of two roads to take.

## The four

A call from a thread other than the loop's — tested only where a loop thread was recorded at all, so a manager that never recorded one accepts any thread.

An account that is not registered. An account that has fail-stopped. An account that failed its startup and stays parked.

## The one refusal that asks for a state

A recovery admission refuses where the account is **not** parked. Every other refusal turns an account away for being in some state; this one turns it away for not being in one.

So the parked state that stops an ordinary admission is exactly what a recovery admission requires.

## The two roads

A recovery admission appends and projects there and then, puts the event on the dispatch queue only where a sequence came back, and answers with that sequence.

Any other admission makes a promise, puts the event and that promise on the admission queue, wakes [the account's worker](how-waiting-work-is-drained.md), and waits. So an ordinary admission answers only once the worker has done the work, and a recovery admission answers having done it itself.

## Related

- [How waiting work is drained](how-waiting-work-is-drained.md)
- [The two checks around an append](the-two-checks-around-an-append.md)
- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
