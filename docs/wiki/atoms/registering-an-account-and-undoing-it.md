---
row: P29-01
baseline: 49aa659
created: 2026-11-11 12:00 UTC
modified: 2026-11-11 12:00 UTC
evidence:
  - claim: "An empty account name is refused, the name tested for its truth alone"
    source: "`trading_inbound.py` 119-121"
  - claim: "An account with no credentials configured is refused"
    source: "`trading_inbound.py` 123-126"
  - claim: "The credentials it works from are copied as it is built"
    source: "`trading_inbound.py` 94"
  - claim: "An account the trading side already holds has its venue credentials registered again, and nothing else is done"
    source: "`trading_inbound.py` 128-130"
  - claim: "Otherwise the venue is registered first and the trading side second"
    source: "`trading_inbound.py` 132 into 134"
  - claim: "A trading side raising one of two named kinds of failure has the venue registration undone, and the failure raised on"
    source: "`trading_inbound.py` 135-138"
  - claim: "A failure of any other kind leaves the venue registration standing"
    source: "`trading_inbound.py` 135, which names two kinds"
  - claim: "Unregistering removes the venue credentials whatever the trading side did, including where it raised"
    source: "`trading_inbound.py` 157-161"
---
# Registering an account, and undoing it

Work reaches the trading side through one way in, and that way in is where [an account](what-an-account-is.md) is registered with both the venue and the trading side at once.

## What it refuses

An empty account name. The name is tested for its truth and nothing more, so a name of blank space alone passes — the fourth place on this side with [that escape](the-escape-in-the-shared-check-for-a-name.md).

An account with no [credentials](where-credentials-come-from.md) configured. The configuration is copied as the way in is built, so what is configured is settled before any account registers.

## The order, and the undoing

An account the trading side already holds is registered with the venue again and left otherwise alone.

A new account is registered with the venue first and the trading side second. Where the trading side raises a bad value or a bad state, the venue registration is undone and the failure is raised on.

Two kinds are named, and a failure of any other kind is not caught at all: the venue keeps the account registered while the trading side does not.

## The other end

Unregistering asks the trading side first and removes the venue credentials afterwards, whatever the trading side did. A trading side that raises still loses its venue credentials.

So the undoing is unconditional at that end and conditional at the other.

## Related

- [What an account is](what-an-account-is.md)
- [Where credentials come from](where-credentials-come-from.md)
- [The escape in the shared check for a name](the-escape-in-the-shared-check-for-a-name.md)
