---
row: P100-02
baseline: 49aa659
created: 2026-11-14 03:30 UTC
modified: 2026-11-14 03:30 UTC
evidence:
  - claim: "An idle phase takes the account out of the map rather than being stored"
    source: "`praxis/trading.py` 1400 into 1401"
  - claim: "Any other phase is stored against the account"
    source: "`praxis/trading.py` 1402-1403"
  - claim: "The manager's gate is set from whether the phase is idle, worked out where it is set rather than passed in"
    source: "`praxis/trading.py` 1406-1408"
  - claim: "An account the manager does not hold takes that account out of the map too"
    source: "`praxis/trading.py` 1409 into 1410"
---
# What the phase map and the gate agree on

One routine writes where an account's reconciliation has got to, and the gate that holds its orders back is worked out from the same value in the same breath.

## What the map holds

Any phase but idle, stored against the account. An idle phase takes the account out of the map rather than being stored as idle.

So the map holds only accounts mid-reconciliation, and an account's absence from it means idle. There is one representation of idle rather than two.

## Where the gate comes from

Whether the phase is idle, worked out where it is set rather than passed in. So the gate cannot be set to disagree with the map: both come from the one value, in the one call.

A caller cannot raise the gate without moving the phase, or move the phase without the gate following.

## The account the manager has lost

Setting the gate for an account the manager does not hold takes that account out of the map too. So the map cleans itself at the moment it next tries to write to an account that has gone.

That is a second road to the same clearing: [unregistering an account clears its phase outright](what-registering-an-account-touches.md). This one catches an account the manager lost without the facade being told — the failure is the signal, and the clearing is what it is used for.

## Related

- [How the reconciliation loop is stopped](how-the-reconciliation-loop-is-stopped.md)
- [What registering an account touches](what-registering-an-account-touches.md)
