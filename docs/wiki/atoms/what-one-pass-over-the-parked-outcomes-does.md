---
row: N77-01
baseline: 49aa659
created: 2026-11-13 10:00 UTC
modified: 2026-11-13 10:00 UTC
evidence:
  - claim: "A pass with no command parked answers at once"
    source: "`nexus/core/outcome_loop.py` 273-274"
  - claim: "One moment is read off the clock for the whole pass"
    source: "`nexus/core/outcome_loop.py` 276, weighed at 281, then set again at 304, or handed on at 291"
  - claim: "The pass walks a copy of the names, so a command taken out of the map as the pass runs leaves the walk undisturbed"
    source: "`nexus/core/outcome_loop.py` 278, against the removals at 287, or 296"
  - claim: "A command put back into the map by a drain is therefore not reached again in the same pass"
    source: "`nexus/core/outcome_loop.py` 331 against the copy taken at 278"
  - claim: "The copy holds the names alone, each turned back into its queue from the map as the pass reaches it"
    source: "`nexus/core/outcome_loop.py` 279"
  - claim: "Once a resolved head's queue has been drained the pass moves to the next command"
    source: "`nexus/core/outcome_loop.py` 293"
  - claim: "A head that neither resolved nor ran out has its count raised by one, the count standing in the queue beside the outcome"
    source: "`nexus/core/outcome_loop.py` 303"
  - claim: "A sibling that dispatched lets the drain move to the one behind it"
    source: "`nexus/core/outcome_loop.py` 329"
  - claim: "A sibling that did not ends the drain where it stands, the ones behind it going back into the queue rather than being tried"
    source: "`nexus/core/outcome_loop.py` 343, after 331-333"
  - claim: "Every outcome of a dropped queue is reported, the head and each sibling alike"
    source: "`nexus/core/outcome_loop.py` 358"
---
# What one pass over the parked outcomes does

A pass walks the commands whose outcomes [are waiting on a strategy](an-outcome-waiting-on-a-strategy.md), and takes at most one step for each.

## The moment

One moment is read off the clock for the whole pass. Every command's waiting is weighed against it, every new waiting set from it, and the drain is handed the same moment.

So a command whose waiting elapses while the pass is still running is judged against the moment the pass began, and waits for the next pass.

## The copy

The pass walks a copy of the names rather than the map itself. A command taken out of the map as the pass runs therefore leaves the walk undisturbed.

The same copy means a command a drain puts back into the map is not reached again in the same pass. It waits like any other.

What the copy holds is the names alone. Each is turned back into its queue from the map as the pass reaches it.

## One step each

A resolved head has its queue drained, and the pass moves on to the next command. A head that neither resolved nor ran out has its count raised by one, the count standing in the queue beside the outcome itself.

## The drain

A sibling that dispatched lets the drain move to the one behind it. A sibling that did not ends the drain where it stands — the ones behind it go back into the queue in order, rather than each being tried in turn.

## The drop

When a head runs out, every outcome of the queue is reported, the head and each sibling alike. The report is one entry per outcome, so a long queue is dropped loudly.

## Related

- [An outcome waiting on a strategy](an-outcome-waiting-on-a-strategy.md)
- [What a tick answers](what-a-tick-of-the-outcome-loop-answers.md)
