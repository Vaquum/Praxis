# Launcher

This page explains how Praxis is started as a whole process and how it is wired together with Nexus and shared market data.

## What The Launcher Is

`praxis/launcher.py` is the orchestration entry point for the combined Praxis + Nexus + Limen runtime. It is responsible for:

- creating the shared asyncio event loop thread used by Praxis
- starting the `Trading` runtime on that loop
- starting the shared `MarketDataPoller`
- starting one Nexus manager thread per configured account
- routing `TradeOutcome` objects back to the correct Nexus thread
- handling shutdown on `SIGINT` and `SIGTERM`

In the current implementation, Praxis is the process. The launcher keeps the execution layer and decision layer in one runtime rather than splitting them into networked services.

## Main Runtime Shape

The current process layout is:

1. main thread for process lifetime and signal handling
2. one asyncio loop thread for Praxis runtime work
3. one Nexus thread per configured account
4. one or more daemon poller threads for shared market data buckets

That means venue REST calls, user-stream processing, reconciliation, and execution events all stay on the Praxis loop, while each Nexus instance runs synchronously in its own thread.

## Startup Order

At a high level, `Launcher.launch()` does this:

1. install signal handlers
2. start the asyncio event loop thread
3. start `Trading`
4. start `MarketDataPoller`
5. start one Nexus thread per `InstanceConfig`
6. block until shutdown signal
7. stop Nexus threads, poller, trading runtime, and event loop

Within each Nexus instance, the launcher wires:

- `PraxisOutbound` so Nexus can submit commands and pull positions
- a per-account `queue.Queue[TradeOutcome]` for outcome delivery back from Praxis
- a startup sequencer that loads manifest and strategy runtime state

## InstanceConfig

`InstanceConfig` defines one Nexus manager instance:

- `account_id`
- `manifest_path`
- `strategies_base_path`
- `allocated_capital`
- `state_dir`
- optional `strategy_state_path`

The launcher creates one per-account outcome queue and one per-account Nexus thread from these configs.

## Why This Matters

This design keeps command submission and outcome routing cheap:

- Nexus to Praxis crosses a thread boundary, not a network boundary
- Praxis to Nexus returns outcomes through a thread-safe queue
- all accounts stay isolated at the runtime level even though they share one process

## Current Boundary

The launcher already wires the paper-trading path end to end. It does not implement a microservice deployment model, and it does not introduce independent remote process boundaries between Praxis and Nexus.

## Read Next

- [Trade Lifecycle](Trade-Lifecycle.md)
- [Execution Manager](Execution-Manager.md)
- [Event Spine](Event-Spine.md)
