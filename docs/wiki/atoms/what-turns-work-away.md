---
row: P2-24
baseline: 49aa659
created: 2026-09-24 21:11 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "Work is turned away while Praxis is shutting down"
    source: "`praxis/trading.py` 1878-1880"
  - claim: "It is turned away before Praxis has been started"
    source: "`praxis/trading.py` 822-825"
  - claim: "It is turned away for an account that has not finished starting, which an unknown name also fails"
    source: "`praxis/trading.py` 836-838, the only entry to that set being 606-608"
  - claim: "An account that failed its start never joins that set"
    source: "`praxis/trading.py` 623 setting the flag at `execution_manager.py` 3643"
  - claim: "An account poisoned later stays in the set, so the manager's own refusal is what catches it"
    source: "poisoned at `execution_manager.py` 4026, refused at 3434-3436"
  - claim: "A supplied request name that is empty is refused"
    source: "`execution_manager.py` 3446-3448"
  - claim: "One too short to build an order name from is refused next"
    source: "`execution_manager.py` 3450 into `generate_client_order_id.py` 105-110"
  - claim: "One already in use anywhere is refused after that"
    source: "`execution_manager.py` 3452-3457"
  - claim: "The command checks itself as it is built, on many grounds"
    source: "`trade_command.py` 79-116, and a mismatched parameter type at 118-124, raised from `execution_manager.py` 3461"
  - claim: "It is then checked for shape on many more"
    source: "`execution_manager.py` 3479 into `validate_trade_command.py`, from an order type the mode disallows at 195-200 to bracket prices on the wrong side at 382-394"
  - claim: "The venue's own filters are not applied here, since no filters are passed"
    source: "`validate_trade_command.py` 143-146, never entered from `execution_manager.py` 3479"
  - claim: "An execution mode switched off on this host is refused"
    source: "`execution_manager.py` 3481-3495, the set defaulting to single-shot alone at `trading_config.py` 105-107"
  - claim: "A full queue is refused last, and fails closed"
    source: "`execution_manager.py` 3497-3511"
  - claim: "All of these raise before the accept is written"
    source: "the accept at `execution_manager.py` 3515-3525"
  - claim: "Work for an account already failed by that point is ended there rather than queued"
    source: "`execution_manager.py` 3531-3547, rather than the queue put at 3550"
---
# What turns work away before it is queued

Work handed to Praxis passes a series of gates before anything is written down. Each raises at the ask, so a caller learns at once.

## At the door

Praxis refuses everything while it is shutting down, and before it has been started at all.

Then the [account](what-an-account-is.md) must have finished starting. A name never registered fails this test too, so an unknown account is turned away here rather than deeper in, as is one whose start failed — it never joins the set this checks.

An account that fails *later* stays in that set, and a second refusal deeper in catches it.

## At the command

A [request name](what-a-trade-is.md) supplied with the work must not be empty, must be long enough to build an order name from, and must not already be in use anywhere, since that register spans accounts.

The command then checks itself as it is built, on many grounds — among them an amount that is not positive or not finite, a time without a zone, an empty symbol. It is then checked for shape on many more, from an order type its execution mode disallows through to bracket prices on the wrong side. The venue's own filters are not applied here; none are passed in.

The execution mode must be switched on for this host. By default only the plain single order is.

Last, the [queue](how-waiting-work-is-drained.md) must have room. A full one refuses rather than waits.

## After them

Only then is the accept written. Even then the work may not be queued: if the account has failed by that point, it is ended there with a rejected report instead. Work turned away at a gate leaves no record behind at all.

## Related

- [Order placement](how-an-order-is-placed.md)
- [What an account is](what-an-account-is.md)
