# Praxis Docs

This page is the routing hub for the Praxis docs. Use it to choose the right path based on what you are trying to do.

## Praxis In One Page

Praxis is Vaquum's execution system. It turns trading decisions into venue actions, durable execution state, and auditable outcomes through an event-sourced runtime centered on the Event Spine.

The current repository is a partial implementation of RFC-4001. Where the RFC and the code diverge, the code is authoritative. Today the implemented center of gravity is the Trading sub-system: Binance Spot testnet execution, per-account isolation, event-backed state replay, and integration wiring with the rest of the Vaquum stack.

## Start Here

### If You Are New To Praxis

1. Read the [product home page](../README.md)
2. Read the architecture and intended scope in [RFC-4001](https://github.com/Vaquum/Praxis/issues/1)
3. Run [Setup And Verification](Setup-And-Verification.md)
4. Read [Trading](Trading.md) and [Trade Lifecycle](Trade-Lifecycle.md)
5. Review [Binance Spot Testnet](Binance-Spot-Testnet.md)
6. Review the current known implementation gaps in [TechnicalDebt.md](TechnicalDebt.md)

### If You Want To Understand The Current Runtime

1. Start with the [product home page](../README.md)
2. Read [RFC-4001](https://github.com/Vaquum/Praxis/issues/1) for the target model
3. Read [Launcher](Launcher.md), [Trading](Trading.md), and [Trade Lifecycle](Trade-Lifecycle.md)
4. Continue to [Execution Manager](Execution-Manager.md), [Event Spine](Event-Spine.md), [Trading State](Trading-State.md), and [Venue Adapter](Venue-Adapter.md)
5. Continue to [Recovery And Reconciliation](Recovery-And-Reconciliation.md), [Trade Outcomes](Trade-Outcomes.md), and [Slippage And Order Book](Slippage-And-Order-Book.md)
6. Review [TechnicalDebt.md](TechnicalDebt.md) for known constraints and shortcuts in the shipped implementation

### If You Want To Contribute Or Maintain

1. Start with [Developer/README.md](Developer/README.md)
2. Read [RFC-4001](https://github.com/Vaquum/Praxis/issues/1)
3. Read [Documentation System](Developer/Documentation-System.md)
4. Review [TechnicalDebt.md](TechnicalDebt.md)
5. Use the repository code as the final source of truth for behavior

## How Praxis Flows

1. A manager or integration layer submits trade decisions into Praxis.
2. Praxis validates and routes those decisions through per-account runtimes.
3. State-changing facts are persisted to the Event Spine before or alongside execution lifecycle changes.
4. Venue adapters submit, cancel, query, and reconcile against Binance Spot testnet.
5. Trading state is rebuilt through replay, and outcomes are routed back downstream to callers.

## Docs Map

- `Overview`: [Product Home](../README.md), [this docs hub](README.md)
- `Guides`: [Setup And Verification](Setup-And-Verification.md), [Launcher](Launcher.md), [Trading](Trading.md), [Trade Lifecycle](Trade-Lifecycle.md), [Binance Spot Testnet](Binance-Spot-Testnet.md)
- `Reference`: [Execution Manager](Execution-Manager.md), [Event Spine](Event-Spine.md), [Trading State](Trading-State.md), [Venue Adapter](Venue-Adapter.md), [Recovery And Reconciliation](Recovery-And-Reconciliation.md), [Trade Outcomes](Trade-Outcomes.md), [Slippage And Order Book](Slippage-And-Order-Book.md)
- `Developer`: [Developer Home](Developer/README.md), [Documentation System](Developer/Documentation-System.md)
- `Operations`: [Technical Debt](TechnicalDebt.md)
- `Architecture`: [RFC-4001](https://github.com/Vaquum/Praxis/issues/1)

## Product Boundary

### Praxis Owns

- execution intake and routing
- venue communication
- order lifecycle tracking
- durable execution state through the Event Spine
- replay and recovery of trading state
- outcome routing back to manager integrations

### Praxis Does Not Yet Fully Own

- the completed Account sub-system described in the RFC
- the full RFC execution-mode surface beyond current shipped behavior
- strategy generation or trade decisioning
- a fully generalized multi-venue execution layer

## Read Next

- For a first real local path, continue to [Setup And Verification](Setup-And-Verification.md)
- For runtime flow, continue to [Launcher](Launcher.md), [Trading](Trading.md), and [Trade Lifecycle](Trade-Lifecycle.md)
- For core state and execution surfaces, continue to [Execution Manager](Execution-Manager.md), [Event Spine](Event-Spine.md), [Trading State](Trading-State.md), [Venue Adapter](Venue-Adapter.md), [Recovery And Reconciliation](Recovery-And-Reconciliation.md), [Trade Outcomes](Trade-Outcomes.md), and [Slippage And Order Book](Slippage-And-Order-Book.md)
- For contributor-facing docs rules, continue to [Developer/README.md](Developer/README.md)
