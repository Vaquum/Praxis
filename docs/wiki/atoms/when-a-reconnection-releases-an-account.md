---
row: P4-60
baseline: 49aa659
created: 2026-10-16 06:03 UTC
modified: 2026-10-16 06:03 UTC
evidence:
  - claim: "The phase an account is in is what the gate on its work is taken from, so the two cannot disagree"
    source: "`trading.py` 1400-1407"
  - claim: "A feed going down gates an idle account at once"
    source: "`trading.py` 1420 and 1426"
  - claim: "One going down mid-pass marks the pass to end gated instead, so no second pass starts"
    source: "`trading.py` 1421-1423"
  - claim: "A reconnection during a running pass asks for exactly one rerun and starts nothing"
    source: "`trading.py` 1449-1453"
  - claim: "Otherwise the reconnection runs the asking itself, backfill then squaring"
    source: "`trading.py` 1455 into 1459-1463"
  - claim: "A venue failure in that asking leaves the account gated"
    source: "`trading.py` 1465-1472"
  - claim: "A backfill coming back incomplete leaves it gated too"
    source: "`trading.py` 1474-1481"
  - claim: "A pass that got through releases the account, and one with a rerun asked for runs again first"
    source: "`trading.py` 1483-1488"
  - claim: "A pass cancelled, or one whose account went away, ends gated"
    source: "`trading.py` 1494 and 1497-1501"
  - claim: "The periodic tick runs its own detectors and never this asking"
    source: "`trading.py` 1372-1377"
---
# When a reconnection releases an account

An account gated by its feed going down stays gated until a reconnection runs the asking again and that asking gets all the way through. The phase it is in is the one place that is recorded, and the gate on its work is read off it, so the two cannot drift apart.

## Going down

A feed going down while nothing is running gates the account there and then.

One going down while an asking is already running marks that pass to end gated instead. The pass carries on to its end, and no second one starts behind it.

## Coming back

A reconnection arriving while an asking is running asks for one rerun and starts nothing itself, so two never overlap.

Arriving at any other time, the reconnection does the asking: the trades missed are fetched, and then the orders are squared against the venue.

## What leaves it gated

A venue failure during that asking leaves the account gated. So does a backfill coming back incomplete, which means the venue had more to give than was fetched.

A pass called off, and one whose account went away under it, both end gated as well.

## What releases it

Only a pass that got all the way through. Where a rerun was asked for meanwhile, that runs first, and the release waits for it.

Nothing else asks. The round of checks that runs on a timer carries its own detectors — the money moved, the balances — and never this asking, so an account gated this way waits on a reconnection rather than on time passing.

## Related

- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
- [The venue feed](the-venue-feed.md)
- [What a reconciliation tells Nexus](what-a-reconciliation-tells-nexus.md)

---

Created 2026-10-16 06:03 UTC · Last modified 2026-10-16 06:03 UTC
