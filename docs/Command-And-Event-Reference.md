# Command And Event Reference

This page lists the commands accepted by `Trading` and the durable events used to track execution and recover account state.

## Commands

| Operation | Entry point | Result |
|---|---|---|
| Submit | `await Trading.submit_command(...)` | Persists `CommandAccepted`, queues the command, and returns its `command_id`. |
| Abort | `Trading.submit_abort(TradeAbort(...))` | Queues cancellation for the target command. Fills already received remain part of the outcome. |
| Modify | `Trading.submit_modify(TradeModify(...))` | Queues an amend for a resting order, running scheme, or active bracket protection. |

All three operations require a ready account. Abort and modify take the original `account_id` and `command_id`, a `reason`, and a timezone-aware `created_at`. Modify also takes `modify_params` for the original execution mode. The account writer processes aborts and modifies on its priority queue. Check the resulting events to see what happened at the venue.

## Submit Fields

| Field | Use |
|---|---|
| `account_id`, `trade_id`, `symbol` | Target account, caller's trade identifier, and venue pair. |
| `side`, `order_type` | `OrderSide` and `OrderType` for the requested order. |
| `qty`, `quote_qty` | Supply exactly one positive, finite `Decimal`. Base quantity uses `qty`. A quote-sized `SINGLE_SHOT` market buy uses `qty=None` and sets `quote_qty`. |
| `execution_mode`, `execution_params` | Execution mode and its parameter type from the table below. |
| `timeout`, `created_at` | Positive deadline in seconds and a timezone-aware creation time. |
| `reference_price` | Positive caller reference price when available. Pass `None` to leave it unset. |
| `maker_preference`, `stp_mode` | Maker preference and self-trade-prevention mode. |
| `strategy_id` | Optional strategy identifier for position attribution. |
| `command_id` | Optional caller-supplied identifier. It needs at least 16 characters after removing hyphens and must be unused. Praxis assigns a UUID when omitted. |

## Execution Modes

`TradingConfig.enabled_execution_modes` defaults to `SINGLE_SHOT`. Enable other modes for the deployment and check the venue's order support. Binsim accepts BTCUSDT market orders.

| Mode | Order type at admission | Submit parameters | Modify parameters |
|---|---|---|---|
| `SINGLE_SHOT` | `MARKET`, `LIMIT`, `LIMIT_IOC`, `STOP`, `STOP_LIMIT`, `TAKE_PROFIT`, `TP_LIMIT`, `OCO` | `SingleShotParams` | `SingleShotModify` |
| `BRACKET` | `MARKET` | `BracketParams` | `BracketModify` |
| `TWAP`, `TIME_DCA` | `MARKET` | `IntervalSliceParams` | `IntervalSliceModify` |
| `SCHEDULED_VWAP` | `MARKET` | `ScheduledVwapParams` | `ScheduledVwapModify` |
| `ICEBERG` | `LIMIT` | `IcebergParams` | `IcebergModify` |
| `LADDER_DCA` | `LIMIT` | `LadderDcaParams` | `LadderDcaModify` |

`TIME_DCA` requires `BUY`. An iceberg's display quantity is at most the command quantity. For required limit and trigger prices by order type, see [the admission checks](../praxis/core/validate_trade_command.py).

The modify type describes the fields that can be requested. The writer checks the live state before applying them. For example, a single-shot amend requires a resting order, and a bracket amend targets active protective OCO orders. See [Execution Manager](Execution-Manager.md).

## Execution Events

Read the Event Spine by `epoch_id` and ascending `event_seq`. Each event carries `account_id` and a timezone-aware `timestamp`. Follow `command_id` for one instruction, `trade_id` across instructions for the same trade, and `client_order_id` from a submission intent to the corresponding venue reports.

| Event | What it records |
|---|---|
| `CommandAccepted` | Accepted command, trade, and optional strategy identifier. |
| `OrderSubmitIntent` | Order identity and sizing recorded before sending it to the venue. |
| `OrderSubmitted`, `OrderAcked` | Venue order identity from the submission response or acknowledgement. |
| `OrderSubmitFailed` | Failed submission, with failure class and the venue's error code when supplied. |
| `FillReceived` | Venue trade ID, filled quantity, execution price, fee, fee asset, and maker flag. |
| `OrderQuoteNativeFilled` | Venue confirmation that a quote-sized order is fully filled. |
| `OrderRejected`, `OrderCanceled`, `OrderExpired` | Terminal order state. Any recorded fills still count. |
| `TradeClosed` | Closure of the trade after a terminal command closes the position. |
| `TradeOutcomeProduced` | Command status, cumulative filled quantity and notional, and target quantity when known. |

## Plan And Protection Events

| Event | What it records |
|---|---|
| `SchemeInitialized`, `SchemeStateChanged` | Starting plan and subsequent scheme lifecycle state. |
| `SliceFailed`, `SchemeFrozen`, `SchemeDraining`, `SchemeReplanned` | Failed slice, freeze, drain, or replacement plan for the remaining work. |
| `OrderAmendInitiated` | A resting single order and its intended replacement before cancellation. |
| `LadderAmendInitiated`, `LadderAmendPlanned` | Rungs being retired and the plan for their replacements. |
| `LadderAmendCompleted`, `LadderAmendAborted`, `LadderAmendStateUnknown` | Completion, abandonment, or uncertain venue state for a ladder amend. |
| `BracketInitialized` | Entry and protective-leg configuration for a bracket. |
| `ProtectionAmendRequested`, `ProtectionCancelConfirmed`, `ProtectionStateUnknown` | Requested protection change and what is known about the old legs. |
| `ProtectionReplaceSubmitted`, `ProtectionActive`, `ProtectionFailed` | Submission, confirmation, or failure of protection. |
| `FlattenInitiated`, `ProtectionRemediationDelivered` | Start of flattening or delivery of remediation to Nexus. |

## Account And Delivery Events

| Event | What it records |
|---|---|
| `RegisterAccount` | Account registration and the cost basis method used in replay. |
| `FundTransaction`, `MarkSampled` | A booked deposit or withdrawal, or a sampled valuation mark. |
| `ReconciliationMismatch` | A balance shortfall observed during reconciliation. |
| `OperatorHaltRequested`, `OperatorResumeRequested` | Operator requests recorded on the spine. |
| `OutcomeDeliveryContextRecorded` | Launcher routing context used to rebuild Nexus delivery after restart. |
| `OutcomeAcked`, `OutcomeReplayAbandoned` | Successful application of a Nexus outcome or durable abandonment of its replay. |

The domain types define the complete fields. [TradeCommand](../praxis/core/domain/trade_command.py), [TradeAbort](../praxis/core/domain/trade_abort.py), [TradeModify](../praxis/core/domain/trade_modify.py), [Event](../praxis/core/domain/events.py)

## Read Next

- [Binsim Walkthrough](Binsim-Walkthrough.md)
- [Event Spine](Event-Spine.md)
- [Trade Outcomes](Trade-Outcomes.md)
