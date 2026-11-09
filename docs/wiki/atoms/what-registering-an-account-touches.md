---
row: P99-03
baseline: 49aa659
created: 2026-11-09 07:50 UTC
modified: 2026-11-09 07:50 UTC
evidence:
  - claim: "Registering demands a started facade, registers the account inbound, and adds it to the managed set"
    source: "`praxis/trading.py` 1835, then 1836, then 1837"
  - claim: "Unregistering demands a started facade too"
    source: "`praxis/trading.py` 1842"
  - claim: "It takes the account's stream out of the map and closes it, with a failure of that closing caught and reported"
    source: "`praxis/trading.py` 1844, then 1845 into 1846-1847, against 1848-1849"
  - claim: "It then unregisters inbound and clears the account from three collections"
    source: "`praxis/trading.py` 1851, then 1852, and 1853, and 1854"
  - claim: "Pulling positions demands a started facade and hands the asking straight on"
    source: "`praxis/trading.py` 1988, then 1989"
  - claim: "Settling a queue hands the asking straight on and demands nothing"
    source: "`praxis/trading.py` 1930"
---
# What registering an account touches

Registering an account touches one collection. Unregistering it touches three and closes a connection.

## Registering

A started facade is demanded first. The account is registered inbound, and added to the managed set. Nothing else is created for it — whatever else the facade will hold about that account arrives later.

## Unregistering

A started facade is demanded too. Then the account's stream is taken out of the map and closed, with a failure of that closing caught and reported rather than stopping the rest.

Then the account is unregistered inbound and cleared from three collections: the managed set, the ready set, and the record of how far its reconciliation got.

So the undoing reaches further than the doing, because the doing is not what put most of it there.

## The two that pass the asking on

Pulling positions demands a started facade and hands the asking straight on. Settling a queue hands the asking straight on and demands nothing.

So one delegation checks and one does not. A caller can settle a queue on a facade that was never started, and the demand is absent rather than passed down — whatever happens then is the manager's to decide.

## Related

- [What the facade hands out](what-the-facade-hands-out.md)
- [What the facade is built with](what-the-facade-is-built-with.md)
