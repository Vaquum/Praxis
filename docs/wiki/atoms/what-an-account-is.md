---
row: P2-12
baseline: 49aa659
created: 2026-09-24 20:13 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "Registering a name creates its queues, its state and its ledger together"
    source: "`execution_manager.py` 823-830, with two further queues made alongside at 581-584"
  - claim: "Venue news arrives on one of those rather than the queue named in the constructor"
    source: "`execution_manager.py` 3211 from `praxis/trading.py` 1757, the named one written only at `execution_manager.py` 3116"
  - claim: "It also starts the one worker that will serve it"
    source: "`execution_manager.py` 832-836"
  - claim: "Registering a known name again re-registers it at the venue and returns, creating none of the account's own state again"
    source: "`trading_inbound.py` 128-130, the manager never entered, though a replaying venue does reset its balance book at `replay_venue_adapter.py` 116"
  - claim: "The refusal that raises is reserved for a direct call on the manager"
    source: "`execution_manager.py` 816-818"
  - claim: "An account can be registered parked, its worker sleeping each pass"
    source: "`execution_manager.py` 831, read by the worker at 3903-3905, cleared at 3672"
  - claim: "Recovery acts on the venue while it is parked, cancelling a stray by one call or the other"
    source: "either `praxis/trading.py` 978-982 for a linked pair or 984-988 otherwise"
  - claim: "A flatten is re-sent only where the policy calls for it and several checks have all fallen through"
    source: "`praxis/trading.py` 600 into the policy test at `execution_manager.py` 7912-7916, reaching 8255 only where every later check falls through, and the send itself at 7707 only past the further checks inside it"
  - claim: "A flatten the venue still has working is left in place, not re-sent"
    source: "`execution_manager.py` 7984-7994"
  - claim: "The repair sweep re-sends by its own route, never through that one"
    source: "`execution_manager.py` 7118-7122, reaching 7139 unless that test returns instead"
  - claim: "Holdings are keyed by trade and account together"
    source: "`trading_state.py` 482-491"
  - claim: "On the exchange adapter, credentials are stored against the name and used to sign its calls"
    source: "`binance_adapter.py` 444, loaded at 721 and signed with at 725"
  - claim: "A replaying venue takes the same argument and never reads it"
    source: "`replay_venue_adapter.py` 113-116"
  - claim: "Some registries are shared across accounts, so a request name in use anywhere is refused"
    source: "`execution_manager.py` 693-697 with the refusal at 3452-3457"
---
# What an account is

An **account** is a name that owns work and everything kept about it. Most of what Praxis holds is per-account: every order, every holding, every queue and the worker that serves them all belong to exactly one account, and the name travels on the work alongside its [trade name](what-a-trade-is.md) from submission onward.

## What registering one creates

Registering a name creates, together: the queue [submitted work](how-an-order-is-placed.md) waits in, the [priority line](the-priority-line.md) [cancellations](how-a-trade-is-cancelled.md) and changes wait in, a queue that only tests write to, a record of its orders both open and closed, and a ledger of what has been spent and held. News from the [venue](what-a-venue-is.md) arrives on queues made alongside those.

It also starts [the one worker](how-waiting-work-is-drained.md) that will serve all of it. Registering a name that already exists creates none of this again: it re-registers at the venue and returns.

An account can be registered parked. Its worker exists but sleeps through every pass, which leaves recovery free to rebuild the picture first — though recovery itself does reach the venue in that window, cancelling strays and, in one narrow case, re-sending a flatten. One the venue still has working is left alone.

## What is shared anyway

Not everything is per-account. Some registries span the whole process, which is why a [request name](what-a-trade-is.md) already in use under one account is refused under another.

Holdings are counted under a trade **and** an account together, so the same trade name under two accounts is two separate holdings. On a real exchange, credentials are stored against the account name and used to sign that account's calls; a replaying venue takes them and never looks.

## Related

- [What a venue is](what-a-venue-is.md)
- [The account worker](how-waiting-work-is-drained.md)
- [Trades, requests and orders](what-a-trade-is.md)
