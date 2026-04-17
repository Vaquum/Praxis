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

The post-MMVP note in `~/PaperTradingPipeline/POSTMMVP-1-EventSourcing-Praxis.md` describes a future state where delivery is fully spine-driven via cursor subscriptions. That is not yet the shipped behavior. Today the spine records the event, but live delivery still depends on the direct in-process routing path.

## Read Next

- [Trade Lifecycle](Trade-Lifecycle.md)
- [Trading](Trading.md)
- [Event Spine](Event-Spine.md)
