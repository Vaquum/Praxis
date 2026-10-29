---
row: N8-07
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-29 08:56 UTC
evidence:
  - claim: "The window keeps what it has seen per strategy and identifier, drops what has aged out, and refuses one seen inside it"
    source: "`nexus/core/validator/intake_stage.py` 170-174, 179-182, 184-194 and 196-197"
  - claim: "Its two guards, against an entry naming no side and one naming no identifier, are never reached from a live request, the builder supplying both before either branch that makes one"
    source: "`nexus/core/validator/intake_stage.py` 153-159 and 162-168 against `praxis/launcher.py` 1171-1172 before 1178-1191 or 1254-1267"
  - claim: "A repeat is refused on a path that returns, so the moment is stored only where the entry is let by"
    source: "`nexus/core/validator/intake_stage.py` 184-194 returning instead of reaching 196-197"
  - claim: "Praxis sets the window span to one second from a figure written into its own code, where the rate cap figure is read from the environment"
    source: "`praxis/launcher.py` 354 over the figure at 190, turned into seconds at `nexus/core/validator/intake_stage.py` 144, against `praxis/launcher.py` 359 over 763"
---
# The window that turns a repeated entry away

A window remembers which strategy sent which identifier, and refuses an entry whose strategy and identifier it has lately seen.

## What counts as the same entry

The strategy that sent it and the identifier it carries, taken together. Two entries from one strategy under different identifiers are separate, and the same identifier from two strategies is separate too.

The window keeps those pairs against the moment each was let by, drops every pair that has reached the span it covers, and refuses an entry whose pair is still inside it. A refusal returns before the moment is recorded, so a repeat that is turned away does not extend the window.

## Where its span comes from

One second, set from a figure written into Praxis's own code. That is where this differs from [the cap on how fast entries may go in](the-cap-on-how-fast-entries-may-go-in.md), which reads its figure from the host's surroundings and so can be changed without changing Praxis.

## The two guards nothing reaches

The check carries two refusals ahead of the comparison — one for an entry naming no side, one for an entry naming no identifier.

Neither is reachable from a live request. Praxis fills both in before it takes either of the two branches that build an entry at all, so by the time the window sees one, both are always there.

## Related

- [The cap on how fast entries may go in](the-cap-on-how-fast-entries-may-go-in.md)
- [The checks a decision passes](the-checks-a-decision-passes.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-29 08:56 UTC
