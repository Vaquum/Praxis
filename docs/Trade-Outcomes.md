# Trade Outcomes

This page explains how Praxis represents execution results and routes them back to Nexus.

## What A Trade Outcome Is

`praxis/core/domain/trade_outcome.py` defines the execution result object produced by Praxis.

It captures what actually happened to a trade, not just what the strategy intended.

Typical fields include:

- `account_id`
- `trade_id`
- `command_id`
- terminal status
- target quantity
- filled quantity
- average fill price when fills exist
- reason text
- strategy attribution when relevant

In v0.97.0, the unused `missed_iterations` and `missed_reason` fields are removed without aliases. Remove those constructor arguments and attribute reads from integrations; they never reported skipped-iteration telemetry. `slices_completed` and `slices_total` continue to describe scheme progress, not missed iterations.

In v0.98.0, `filled_qty`, `cumulative_notional`, and `avg_fill_price` describe the same fills. A venue can report more filled than was ordered; each fill is admitted only as far as the command's budget allows, at the price that executed, and the excess is discarded. A command budgets either a base quantity (`qty`) or a quote spend (`quote_qty`), never both, and admission caps whichever one it declared — the other follows at the admitted fills' own prices.

For `filled_qty > 0`, `avg_fill_price` is `cumulative_notional / filled_qty` in Decimal arithmetic. When `filled_qty` is zero, `avg_fill_price` is `None`.

Previously the two totals described different sets of fills, and neither producer was right: one capped the quantity while retaining the whole venue notional, so dividing them gave a price several times the one that executed; the other scaled the notional to match the capped quantity, which reported the right average but could fall below a notional already published for an earlier partial. Consumers that avoided the division to work around the first no longer need to.

The discarded excess is real: Praxis books the full quantity and spend to the account ledger and carries it in the position it holds, and sizes protection and flattens from that raw exposure. Only the outcome is bounded.

A decision layer reconstructing its position from outcomes will not match what the account holds, and the sign of the difference is not fixed: it is short by any discarded excess and long by the commission a spot venue charges in the asset received. The position projection and the ledger's lots both carry what was delivered, net of that commission, so they agree with the wallet; the reported quantity is the one that does not. An outcome is an execution record, not an inventory feed — see TD-156.

## When Outcomes Are Produced

Praxis produces outcomes when commands reach a terminal result:

- fully filled
- rejected
- canceled
- expired
- partially executed and then aborted

Those outcomes are reflected in both:

- the in-process callback/queue delivery path for Nexus
- `TradeOutcomeProduced` events in the Event Spine

## Routing Model

The current queue delivery model is:

1. outcome produced inside execution path
2. callback path routes to `Trading.route_outcome()`
3. outcome delivered to the correct per-account `queue.Queue`
4. Nexus thread reads and reacts

This preserves account isolation even though all accounts share one process.

## Current Boundary

A future state described in the [Event Spine](Event-Spine.md) documentation would make delivery fully spine-driven via cursor subscriptions. That is not yet the shipped behavior. Today the spine records the event, but live delivery still depends on the direct in-process routing path.

## Read Next

- [Trade Lifecycle](Trade-Lifecycle.md)
- [Trading](Trading.md)
- [Event Spine](Event-Spine.md)
- [Metric Snapshots](Metric-Snapshots.md)
