---
row: P1-01
baseline: 49aa659
created: 2026-09-20 15:52 UTC
modified: 2026-09-24 08:02 UTC
evidence:
  - claim: "A request carries a name of its own alongside the trade name"
    source: "a supplied name is refused when empty at `execution_manager.py` 3446-3448, when too short by `generate_client_order_id.py` 105-110 called from `execution_manager.py` 3450, or when already in use at 3452-3457; where none was supplied one is generated instead at 3459; both carried at 3461-3463"
  - claim: "Holdings are keyed by trade name and account"
    source: "`trading_state.py` 482-491"
  - claim: "Protection is placed only once the opening order is finished, something filled, and something is still held"
    source: "finished at `execution_manager.py` 4672-4673; nothing filled ends it at 4704-4712, otherwise placement is called at 4714-4725; nothing held leaves it unplaced and the bracket registered for later at 4887-4904, counted at 4848-4852"
  - claim: "Protection is a request Praxis builds itself, not one submitted to it"
    source: "built at `execution_manager.py` 5159-5161, installed only on success 5017-5018; a submitted request is built instead at 3459-3463"
  - claim: "A result is built per request and carries both names"
    source: "`execution_manager.py` 10784-10788"
  - claim: "Results carry the request name; delivery queues are keyed by account"
    source: "`execution_manager.py` 10818-10822, `trading.py` 335-336"
  - claim: "A request can report more than once, and a later report need not be the last"
    source: "first at `execution_manager.py` 4551-4558, again for the same request at 10733-10741, which can itself be a partial report from 10710"
  - claim: "A recorded order can be abandoned instead of sent"
    source: "recorded at `execution_manager.py` 4944-4945, then either abandoned at 4965 or sent at 4968"
  - claim: "The first slice goes at once, later ones when their interval falls due and the run is open"
    source: "first fired at `execution_manager.py` 5800; a later one fires only where the due test at 5831-5835 passes, needing the run open and no ending pending, reaching 5838-5839; the next time is set an interval ahead at 5923-5926"
  - claim: "A run past its deadline is ended instead of being advanced, unless it is draining or mid-change"
    source: "`execution_manager.py` 5817-5824, whose test requires the hold not draining and no change in progress"
  - claim: "A send is filed under its own name before any venue name exists"
    source: "`trading_state.py` 309-311, the venue's own name arriving later at 337-341"
  - claim: "Each slice is its own order, named from the request and carrying its name"
    source: "`execution_manager.py` 5904-5908, 5953-5966, the name formed from a fragment of the request name at `generate_client_order_id.py` 149-154"
---
# Trades, requests and orders

A **trade**, a **request** and an **order** are three names Praxis keeps, at three different scales. A trade names work that arrived from outside. A request names one piece of work carried out under it. An order names one [send to the venue](how-an-order-is-placed.md).

## Trade

A name from outside, carried along so related work can be recognised. Holdings are counted under it.

## Request

One piece of work, tracked under a name of its own and carrying the trade name too. Requests arrive from outside, and Praxis raises some itself: once an opening order has finished with something filled and holdings still open, it builds a second request for the protective order.

## Order

One send to the venue. Praxis names and records it before making the call, and some recorded orders are abandoned before that call, so a record can stand where no send followed. The venue's own name arrives later.

## How they fan out

One trade can cover more than one request, and one request can send more than one order.

Opening a protected position is submitted once: Praxis sends the opening order, then raises that second request under the same trade. A request fed out over time sends an order per slice, all under that one request. The first goes at once; [the account worker](how-waiting-work-is-drained.md) releases each later one when its interval has come and nothing has halted the run.

## Matching a result to a name

Results come back per request. A single request can report more than once, and a report may be followed by another.

To ask what became of everything, gather the results sharing a trade name. To ask about one piece of work, match on its request name; every result carries it.
