---
row: P1-04
baseline: 49aa659
created: 2026-09-20 16:35 UTC
modified: 2026-09-24 08:02 UTC
evidence:
  - claim: "An unknown account is refused"
    source: "`execution_manager.py` 2995-2998"
  - claim: "A failed start, or a worker whose task has exited, is refused"
    source: "`execution_manager.py` 3000-3012"
  - claim: "An unknown request, or one belonging to another account, is refused"
    source: "either `validate_trade_abort.py` 42-44 or 46-51"
  - claim: "Already-finished work makes the ask do nothing"
    source: "`validate_trade_abort.py` 53, acted on at `execution_manager.py` 3020-3025"
  - claim: "Otherwise it joins the priority line"
    source: "`execution_manager.py` 3027"
  - claim: "A still-starting account reaches no queue that pass"
    source: "`execution_manager.py` 3903-3905"
  - claim: "Work with no order yet is marked, then later dropped unsent"
    source: "marked at `execution_manager.py` 8500-8506, returning at 8512 before any fill is read; the mark is taken at 4154, 4482, 5275, 5713 or 6074"
  - claim: "Those paths report nothing filled"
    source: "`execution_manager.py` 4161-4168, 4490-4497, 5283-5290, 5720-5726"
  - claim: "A marked ladder reaching its start builds no report then"
    source: "a zero slice total passed at `execution_manager.py` 6077-6081 into 8411-8423, refused by `trade_outcome.py` 146-148, the error logged and swallowed at `execution_manager.py` 4012-4019"
  - claim: "The next start reports it rejected as an orphan"
    source: "`execution_manager.py` 2254-2259 classing it, 2270-2275 into the rejection built at 2309-2321 and dispatched at 2330, run at boot from `praxis/trading.py` 550-552"
  - claim: "A request already finished when the worker reaches the ask is left alone"
    source: "`execution_manager.py` 8482-8487"
  - claim: "A ladder past its deadline reports instead, never reaching that start"
    source: "`execution_manager.py` 4004-4005 into the expired report at 4123-4129, rather than the start at 4007"
  - claim: "Only such work already begun leaves for its own path"
    source: "`execution_manager.py` 8489-8491"
  - claim: "An existing order is cancelled at the venue"
    source: "either `execution_manager.py` 8521-8525 for a linked pair or 8527-8531 otherwise"
  - claim: "A not-found failure is swallowed and the cancellation still recorded"
    source: "`execution_manager.py` 8532-8533, unchanged at 8538"
  - claim: "A venue failure leaves the order record untouched"
    source: "`execution_manager.py` 8534-8536, skipping 8539-8547"
  - claim: "The request is reported cancelled either way"
    source: "`execution_manager.py` 8568-8570, built at 10567-10580"
  - claim: "A cancel reply missing its id, or carrying a status Praxis cannot read, builds no report and writes no reason"
    source: "a missing id raised at `binance_adapter.py` 1690, an unreadable status at 1691 via 895-897, or for a linked pair a missing list id at 1735, escaping either `execution_manager.py` 8532-8533 or 8534-8536, logged at 3944-3951"
  - claim: "A linked-pair cancel never reads a status, so an unknown one changes nothing"
    source: "`binance_adapter.py` 1734-1736"
  - claim: "A body that will not parse is a venue error instead, so a reason is written and the report still built"
    source: "a success body wrapped at `binance_adapter.py` 660-680, or an error body raised at 1143-1152, caught at `execution_manager.py` 8534-8536, built at 8568-8570"
  - claim: "The reported fill total is the one already recorded for the work"
    source: "`execution_manager.py` 8549-8551, read at 2588-2591"
---
# Cancellation

Cancelling asks Praxis to stop a request already submitted. A refusal, or a request already finished, is settled at the ask. Otherwise it joins the [priority line](how-waiting-work-is-drained.md), and whether it stopped anything is known later.

## Asking

The ask is refused if the account or the [request](what-a-trade-is.md) named is unknown, if it belongs elsewhere, or if the account failed to start or its worker has exited.

Work already finished makes it a no-op. Otherwise it joins the line, which the worker empties on every pass once the account has finished starting up.

## Carrying it out

A request that finished while the ask waited is left alone. Work fed out or laddered, already begun, takes its own path. For the rest, one of two things is true.

If [no order](how-an-order-is-placed.md) exists yet, the work still waits its turn. It is marked, and when that comes it is dropped unsent and reported with nothing filled. A ladder cancelled before its first rung is dropped too. Past its deadline it is reported expired on that pass; otherwise its report fails to build, and a rejection reaches the caller only after the next start.

If an order does exist, the venue is told to cancel it. A failure the adapter calls not-found counts as success and is recorded as a cancellation. Any other leaves the order's record untouched, with the reason carrying the failure.

The request is reported cancelled either way, including when the venue refused the cancel and the order still rests there — unless the reply is missing an id, or carries a status it cannot read, when no report is built and no reason written.

## What was already filled

On the existing-order path, whatever had already been counted as filled is reported with the cancellation, and no fresh count is fetched.
