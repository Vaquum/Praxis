# Binsim Walkthrough

This guide follows a paper buy through Praxis, from command acceptance and fill to position recovery after restart.

## Prerequisites

- a Praxis checkout with the development dependencies installed in an active Python environment
- the recorded BTCUSDT Spot book included with the checkout

Install the dependencies using [Setup And Verification](Setup-And-Verification.md).

## Run The Walkthrough

From the repository root, run the test in a fresh temporary directory so you can inspect its artifacts after it exits.

```bash
run_dir=$(mktemp -d)
python -m pytest -q --basetemp "$run_dir" \
    tests/test_binsim_feed.py::test_recorded_binsim_buy_replays_after_restart
```

The test starts a local Binsim venue and registers a paper account with 10,000 USDT and zero BTC. The depth poller reads the first captured observation through a local HTTP endpoint. The clock is held 100 ms after its receipt time, keeping the original observation within the freshness limit. The book update ID is `101867030636`. [Capture provenance](../tests/fixtures/render-top20/provenance.json)

## Submit The Buy And Read The Fill

`Trading.submit_command()` submits a `SINGLE_SHOT` market buy for 0.001 BTC on `BTCUSDT`. Praxis persists `CommandAccepted` and queues the command, then writes `OrderSubmitIntent` before sending the order through `BinanceAdapter`. Binsim fills the order at the first ask and returns the fill inline in the REST response.

| Reading | Result |
|---|---|
| Filled quantity | 0.001 BTC |
| Fill price | 80,514.49 USDT per BTC |
| Quote spent | 80.51449 USDT |
| Fee | 0.000001 BTC |
| Open position after the fee | 0.000999 BTC |
| Remaining Binsim balance | 9,919.48551 USDT and 0.000999 BTC |

Praxis records `OrderSubmitted` and `FillReceived` using the client order ID from the intent. `TradeOutcomeProduced` reports `FILLED` for the command. The entry leaves an open position.

## Verify Restart Recovery

The test stops `Trading` and closes its SQLite connection. A new instance opens the same `events.sqlite` in epoch 1, verifies the Event Spine, and rebuilds the account position. It checks that the recovered position and ordered events match the first run and that the venue balances still match the filled buy. The test also reopens `binsim_ledger.json` from disk and checks both balances.

After the test passes, read the events from the reopened database.

```bash
spine=$(find "$run_dir" -name events.sqlite -print)
python -m sqlite3 "$spine" \
    'SELECT event_seq, event_type FROM events WHERE epoch_id = 1 ORDER BY event_seq;'
```

```text
(1, 'RegisterAccount')
(2, 'CommandAccepted')
(3, 'OrderSubmitIntent')
(4, 'OrderSubmitted')
(5, 'FillReceived')
(6, 'TradeOutcomeProduced')
```

The single `FillReceived` row and the recovered 0.000999 BTC position are the checks that matter here. For venue reconciliation during interrupted execution, see [Recovery And Reconciliation](Recovery-And-Reconciliation.md).

## Read Next

- [Binsim](Binsim.md)
- [Command And Event Reference](Command-And-Event-Reference.md)
- [Trading State](Trading-State.md)
