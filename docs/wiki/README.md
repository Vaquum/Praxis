# How Praxis and Nexus work

Praxis sends orders to a venue and keeps the record of what happened. Nexus
decides what to send. One process runs both, and these short articles explain
one piece each, in plain words.

New here? Read [Trades, requests and orders](atoms/what-a-trade-is.md), then
[What an account is](atoms/what-an-account-is.md),
[Order placement](atoms/how-an-order-is-placed.md),
[The account worker](atoms/how-waiting-work-is-drained.md) and
[Outcomes](atoms/what-an-outcome-is.md). After that, open the group holding your
question. Every term is explained in the article that owns it, and linked from
the others where it appears.

## Orders, accounts and the venue

- [Trades, requests and orders](atoms/what-a-trade-is.md) — a trade, a request and an order: work from outside, one piece of it, and one send to the venue.
- [What an account is](atoms/what-an-account-is.md) — a name that groups the requests, orders, holdings and queues kept about it.
- [What a venue is](atoms/what-a-venue-is.md) — whatever Praxis sends orders to: one per host, called by name, so a live exchange and a simulator run the same code.
- [What a fill is](atoms/what-a-fill-is.md) — a report from a venue that some of an order has traded: an amount, at a price, at a time.
- [Outcomes](atoms/what-an-outcome-is.md) — what Praxis reports back about a request: where it has got to, how much filled, and at what average.
- [Order types](atoms/order-types.md) — the kinds of order Praxis can send — at the market, at a named price, waiting on a trigger, and a linked pair where one filling cancels the other.
- [The prices an order must name](atoms/the-prices-an-order-must-name.md) — which kinds of order need a price, a trigger, or both.
- [Where the order type decides](atoms/where-the-order-type-decides.md) — the few places where the kind of order alone changes what Praxis does.
- [The order book](atoms/the-order-book.md) — what a venue publishes about a pair: buyers on one side, sellers on the other, each a price and an amount wanted.
- [Holdings](atoms/holdings.md) — what one trade holds: which way it went, how much, and the average price paid to build it.

## A decision becomes an order

- [How a decision becomes a command](atoms/how-a-decision-becomes-a-command.md) — a decision from Nexus is turned into an instruction Praxis will act on, field by field.
- [What a command must carry](atoms/what-a-command-must-carry.md) — one instruction must name the account, the trade and itself, and give either an amount of coin or an amount of money, never both.
- [The payload a mode's settings arrive in](atoms/the-payload-a-modes-settings-arrive-in.md) — the settings that ride along with a decision, and how they are turned into the ones the chosen way of working needs.
- [What a command's checks let through](atoms/what-a-commands-checks-let-through.md) — the checks on an instruction only ask whether something is there, or whether a number is above zero, so other mistakes pass and surface later.
- [What turns work away](atoms/what-turns-work-away.md) — the checks work must pass before Praxis records it at all, before it is ever queued.
- [What the host refuses first](atoms/what-the-host-refuses-first.md) — one guard every way in shares, answered by a raise before anything is written down.

## Getting an order to the venue

- [Order placement](atoms/how-an-order-is-placed.md) — placing happens in two stages: recording the work and returning, then reaching the venue on a later pass.
- [How an order is named](atoms/how-an-order-is-named.md) — Praxis works an order's name out rather than drawing it at random, so the same inputs always give the same name.
- [The likely-price check](atoms/how-the-likely-price-is-checked.md) — refusing an order that would trade too far from the market price.
- [Estimating the likely price](atoms/how-the-likely-price-is-worked-out.md) — the average price Praxis expects an order to get, worked out by walking the offers standing at the venue.
- [The sizes a venue trades in](atoms/the-sizes-a-venue-trades-in.md) — a venue accepts only certain amounts and prices, and Praxis weighs an order against the figures it holds for that symbol — or sends it unweighed when it holds none.
- [What a venue must be able to do](atoms/what-a-venue-must-be-able-to-do.md) — the jobs every venue has to offer — register an account, place, cancel, report balances — written down as one list.
- [Holding back sends](atoms/holding-back-sends.md) — a limit on how fast Praxis may call the venue: most calls wait for a slot, and asking the time does not.
- [When Praxis retries a venue call](atoms/when-praxis-retries-a-venue-call.md) — a repeatable call gets three attempts and a send gets one, and each attempt spends a slot of the allowance.
- [When a send's outcome is unknown](atoms/when-a-send-is-unclear.md) — a call to the venue can fail without settling whether the order arrived, so Praxis asks the venue before deciding.
- [A reply that cannot be read](atoms/a-reply-that-cannot-be-read.md) — what happens when the venue answers in a shape Praxis cannot understand.
- [Who refused a send](atoms/who-refused-a-send.md) — a failed send is put down to the venue, to Praxis, or to neither, so a later reader need not judge the wording.
- [What a refusal says](atoms/what-a-refusal-says.md) — a refusal arrives as a named kind, and the kind decides whether the outcome is settled or must be asked after.

## The pass that takes work off the queues

- [The account worker](atoms/how-waiting-work-is-drained.md) — each account has one worker going round the same circuit until it is stopped, taking work off a queue.
- [The priority line](atoms/the-priority-line.md) — cancellations and changes wait in a line of their own, emptied on each circuit once the account has started, before anything waiting to be placed.
- [Work already under way](atoms/work-already-under-way.md) — what a pass moves along between taking one request and the next — a cancel tried again, a slice now due, protection waiting to go up.
- [When an account is reconciling or poisoned](atoms/when-an-account-is-reconciling-or-poisoned.md) — what a pass does for an account being brought back into step with the venue, or carrying a fault that needs a restart, and when there is no pass left to do it.
- [When a reconnection releases an account](atoms/when-a-reconnection-releases-an-account.md) — a gated account waits on its feed coming back, not on time passing.
- [A change waiting out a hold](atoms/a-change-waiting-out-a-hold.md) — a change to an order already sent is put aside while the account is catching up with the venue, and is never taken up at all once the worker has stopped.
- [How a worker stops taking work](atoms/how-a-worker-stops.md) — the loop an account takes its work from can die, be cancelled, or go on turning without ever reaching that work, and each leaves the account differently placed.

## Ways an order can be worked

- [Ways of working a host may drive](atoms/ways-of-working-a-host-may-drive.md) — a host is given the list of ways it may work an order, and work naming one outside that list is turned away.
- [The settings each way of working takes](atoms/the-settings-each-way-of-working-takes.md) — what each way of working an order asks to be told, and the mistakes in it that get the order refused.
- [Work fed out over time](atoms/work-fed-out-over-time.md) — an amount broken into slices that go out one at a time with a gap between them.
- [Orders at several prices](atoms/orders-at-several-prices.md) — spreading an amount across named prices, an order each, sent one after another in one pass.
- [Part-shown orders](atoms/part-shown-orders.md) — one resting order the venue displays only part of at a time.
- [When a weight curve plans nothing](atoms/when-a-weight-curve-plans-nothing.md) — a curve that passes every settings check can still split an amount into a part of nothing, caught on the way out rather than at the start.
- [Protection](atoms/protection.md) — the pair of orders put up after an opening one, to close the position at a good price or at a bad one.
- [When protection is put up again](atoms/when-protection-is-put-up-again.md) — the protective pair goes up once and a second attempt is turned back — except where the prices are being changed, which sends a fresh pair past that guard.
- [How protection's prices are changed](atoms/how-protections-prices-are-changed.md) — the resting pair taken down and a fresh one put up for what is left, or nothing put up where nothing is worth protecting.
- [When protection is lost](atoms/when-protection-is-lost.md) — once the pair guarding a position counts as gone, the account stops adding to it, a closing order is attempted where the policy says so, and Nexus is told.
- [How an unfinished close is recovered](atoms/how-an-unfinished-close-is-recovered.md) — a start picks up a close that never settled from the failures written down, and weighs what is open again before sending.
- [When a flatten places nothing](atoms/when-a-flatten-places-nothing.md) — the order that closes an unprotected position is only an attempt: an unknown venue, a pair that may still be resting, or too little left to close stop it before anything goes out.
- [How big a flatten goes out](atoms/how-big-a-flatten-goes-out.md) — the remainder cut down to what the account can pay with and rounded to the venue's step, against a price worked out for that purpose alone.

## Changing, cancelling and giving up

- [Changing work already sent](atoms/changing-work-already-sent.md) — asking Praxis to alter work it has accepted, what may be altered depending on how that work is carried out.
- [The change each way of working accepts](atoms/the-change-each-way-of-working-accepts.md) — every request to alter work must name the command, the account and a reason, and a change to how work is spread over time is refused outright.
- [What each change insists on](atoms/what-each-change-insists-on.md) — which fields each way of working lets a change touch, and what it checks before touching them.
- [How a schedule change is carried out](atoms/how-a-schedule-change-is-carried-out.md) — the parts already sent kept, the rest planned again, and the next part set a full gap from now.
- [How a price change is carried out](atoms/how-a-price-change-is-carried-out.md) — a price change replaces the order rather than editing it: the resting one is cancelled, what it really filled is settled, and a fresh one goes out for the rest.
- [How a ladder's prices are changed](atoms/how-a-ladders-prices-are-changed.md) — the whole grid replaced: every old rung cancelled and seen to be over before one new rung goes out.
- [What stops a ladder's new rungs](atoms/what-stops-a-ladders-new-rungs.md) — a grid can be left short: nothing worth placing, a freeze, or a rung that halts the run each time it is tried.
- [When a price change leaves no new order](atoms/when-a-price-change-places-nothing.md) — a price change can end with nothing resting in place of the order it replaced: the cancel never settles, the order is still working, too little is left to trade, or the send goes out and comes back unconfirmed.
- [Cancellation](atoms/how-a-trade-is-cancelled.md) — asking Praxis to stop a request already submitted, answered at once or taken up in the line of its own.
- [Abandoning work outright](atoms/abandoning-work-outright.md) — asking Praxis to give up on one command rather than alter it, cancelling at the venue where an order is out.
- [Where an abandonment lands](atoms/where-an-abandonment-lands.md) — what giving up on a command does, by how far that command had got.

## When work runs out of time

- [Deadlines](atoms/deadlines.md) — the time by which work is expected to be done, and the moments Praxis measures against it.
- [The expiry cancel](atoms/the-expiry-cancel.md) — an order found past its deadline has its report settled as expired before the venue is asked, and the expiry written against the order unless the cancel failed outright.

## What a fill does when it arrives

- [What a fill changes](atoms/what-a-fill-changes.md) — a fill updates the order's record and then the money's, so a failure on the first leaves the second alone.
- [Fills and the order](atoms/fills-and-the-order.md) — how a fill moves an order's totals and status, including one arriving too late.
- [When an update fails](atoms/when-an-update-fails.md) — failing to update the order's own totals stops the account; failing to update the money record is logged and passed over.
- [How an outside event enters the record](atoms/how-an-outside-event-enters-the-record.md) — news from outside is written by the account's own writer, and the caller waits to be told how it went.
- [Where duplicates stop](atoms/where-duplicates-stop.md) — the same fill can arrive from the send, from the live feed and from a later query — it is written down once, and only that copy is acted on.
- [The part of a fill a command counts](atoms/the-part-of-a-fill-a-command-counts.md) — the whole fill goes into the books, and only what fits the order's budget reaches the figures Nexus hears.

## The records Praxis keeps

- [The order record Praxis keeps](atoms/the-order-record-praxis-keeps.md) — what Praxis holds about one attempt to place an order at the venue.
- [What changes on an order](atoms/what-changes-on-an-order.md) — the fields that move as the venue reports, and the rules that stop applying once the record exists.
- [The position Praxis keeps](atoms/the-position-praxis-keeps.md) — what Praxis records of the coin it holds per trade, and when a purchase charge is taken off the amount that purchase adds.
- [The commission and the amount](atoms/the-commission-and-the-amount.md) — why holdings are sometimes credited less than the fill reported.
- [When the commission swallows the fill](atoms/when-the-commission-swallows-the-fill.md) — what happens when the fee equals or exceeds the amount traded.
- [The money ledger](atoms/the-money-ledger.md) — Praxis's own account of what a trade cost and what it made, kept beside the holdings.
- [Lots, and what a sell costs](atoms/lots-and-what-a-sell-costs.md) — a buy is remembered as an amount at the price it was bought at, and a sell is costed against those.

## The written history, and what it proves

- [The event spine](atoms/the-event-spine.md) — the file Praxis writes its events to, in the order it wrote them.
- [The chain](atoms/the-chain.md) — records carry codes drawn from the record before, so editing a coded one shows up.
- [When an older record can be opened](atoms/when-an-older-record-can-be-opened.md) — a record from an earlier build is brought forward to the shape this one expects, unless its identity or its duplicate marks say otherwise.
- [What the chain proves](atoms/what-the-chain-proves.md) — checking the chain end to end says whether every row that has codes still matches its contents and the row before it.
- [What the chain misses](atoms/what-the-chain-misses.md) — ways of altering the records that the check does not notice.

## What the venue tells Praxis

- [The venue feed](atoms/the-venue-feed.md) — a connection kept open per account, over which the venue says what happened to that account's orders unasked.
- [The kept book](atoms/the-kept-book.md) — Praxis's own copy of the latest offers for a pair, held with the time it arrived so a check need not wait on the venue.
- [Backfilling missed trades](atoms/backfilling-missed-trades.md) — asking the venue for trades Praxis did not hear about, after the feed was away or at a start.
- [How an order is brought back into step](atoms/how-an-order-is-brought-back-into-step.md) — the venue asked what became of each working order, fills taken in before any ending is concluded.

## The prices a strategy is priced against

- [Where the bars are kept](atoms/where-the-bars-are-kept.md) — the price history a strategy is measured against: one file per series on disk, read for the last bar that closed.
- [When no price comes back](atoms/when-no-price-comes-back.md) — the ways reading that history gives nothing back — the file, the table inside it, or the price itself being unusable.

## What Praxis reports back to Nexus

- [How an outcome crosses back](atoms/how-an-outcome-crosses-back.md) — Praxis reports running totals for a command and Nexus wants one event's figures, so one report becomes several or none.
- [The figures an outcome carries](atoms/the-figures-an-outcome-carries.md) — a report is refused unless its numbers hold together: a target above zero, a filled amount within it, and an average price that fits them.
- [The figures carried back on a fill](atoms/the-figures-carried-back-on-a-fill.md) — what Nexus is told on a fill is the change since the last report rather than the running total, and one change can cover several fills.
- [The figures an outcome reports](atoms/the-figures-an-outcome-reports.md) — the slice count is slices sent rather than slices finished, and how far along is the filled amount against the target.
- [What an outcome does not check](atoms/what-an-outcome-does-not-check.md) — a report is never checked for whether its value matches amount times price, nor for whether its state and its counts agree.
- [How an outcome is delivered](atoms/how-an-outcome-is-delivered.md) — an outcome is written down before it is handed over, and the handing over can fail.
- [What stops an outcome crossing twice](atoms/what-stops-an-outcome-crossing-twice.md) — once a request has ended, a later report of it is dropped — for as long as that ending is still remembered.
- [How an undelivered outcome is replayed](atoms/how-an-undelivered-outcome-is-replayed.md) — how the next startup works out which reports are not yet accounted for.
- [Who a restart tells again](atoms/who-a-restart-tells-again.md) — a report can have two receivers, and a restart resends to the first one only.
- [Outcomes that never come back](atoms/outcomes-that-never-come-back.md) — when a report being resent is given up on, and what is left behind when it is.

## When the books do not match the venue

- [What a reconciliation tells Nexus](atoms/what-a-reconciliation-tells-nexus.md) — the findings that cross when Praxis squares its books, and the answer it sends back when Nexus asks what it is holding.
- [When a balance shortfall is reported](atoms/when-a-balance-shortfall-is-reported.md) — the venue holding less of an asset than the books say, compared asset by asset and told to Nexus.
- [Reports that do not get through](atoms/reports-that-do-not-get-through.md) — what happens to a shortfall Nexus never took, and the stale one that keeps waiting.
- [The window a movement is found in](atoms/the-window-a-movement-is-found-in.md) — money moving in or out is looked for from the last one seen, and never from before the account was taken on.
- [The holds a report places](atoms/the-holds-a-report-places.md) — what a reported finding does to the account: halt it, block new entries, or log it, and only a hand from outside lifts the hold.

## What Nexus does with the money

- [The checks a decision passes](atoms/the-checks-a-decision-passes.md) — a given list walked in order until one refuses, and most of it skipped for an action that closes rather than commits.
- [What a check must answer with](atoms/what-a-check-must-answer-with.md) — two shapes an answer may take, and the answers the walk declines to interpret at all.
- [What becomes of money set aside](atoms/what-becomes-of-money-set-aside.md) — money held back for a trade that never happens stays held back until something else comes along and asks.
- [How far down the account is](atoms/how-far-down-the-account-is.md) — losses are measured both from the best the account has ever been worth and from the best its closed trades have ever added up to, and those are different numbers.
- [What the price check weighs](atoms/what-the-price-check-weighs.md) — the check that looks at the market stops a trade for a number being absent as readily as for one being out of bounds.
- [What the platform ceilings weigh](atoms/what-the-platform-ceilings-weigh.md) — the last check before an order goes out asks for five numbers and is handed one, and the limits it offers on the rest cannot be used.
- [What each check weighs](atoms/what-each-check-weighs.md) — six checks stand between a strategy's decision and the venue, and they look at quite different things: the order itself, what the account has lost, and whether the venue is answering.
- [The roads around the checks](atoms/the-roads-around-the-checks.md) — some orders go out to the venue without passing a single one of the checks the rest pass.
- [What an entry outcome changes](atoms/what-an-entry-outcome-changes.md) — a report of one kind moves the money set aside for a command on to the next place it sits, and two kinds of report move nothing at all.
- [What a settling fee does to the figure](atoms/what-a-settling-fee-does-to-the-figure.md) — the gap between a guessed trading cost and what the report says it came to moves two balances in opposite directions, and can raise the money held against a strategy without anyone committing more.
- [When a reservation times out](atoms/when-a-reservation-times-out.md) — money held for a trade that never went out is given back by a sweep at the start of a fresh request, and an order finding its own hold already expired hands the money back itself rather than waiting for that sweep.
- [Releasing an order whose record was lost](atoms/releasing-an-order-whose-record-was-lost.md) — where the system knows an order by name but has lost everything else about it, the money behind it is given back from the name alone, and asking about an order that was never there is treated as success.
- [Whether a fill closes a position](atoms/whether-a-fill-closes-a-position.md) — a completed trade is checked against the holding it was meant to close, and a leftover below the increment the venue prices sizes in counts as closed.
- [What weighs a shutdown sale](atoms/what-weighs-a-shutdown-sale.md) — an order the system approves itself still meets the guard comparing its price to the open market, and the check against the venue's own minimum size, though an order fed out in pieces misses the first of those entirely.
- [The sale a host sends as it stops](atoms/the-sale-a-host-sends-as-it-stops.md) — shutting down, the system asks each strategy what to sell and approves those orders itself, so the checks that normally stand in front of an order never see them.
- [Where an imported position's names come from](atoms/where-an-imported-positions-names-come-from.md) — a holding rebuilt at startup needs three labels off the side that placed the orders, and a holding missing any one of them is left out of the records altogether.
- [What a stopping host halts first](atoms/what-a-stopping-host-halts-first.md) — on the way down, anything a strategy asks for through the usual checks is turned away, and the background jobs are switched off one after another in a set order.
- [What a stopping host saves of its strategies](atoms/what-a-stopping-host-saves-of-its-strategies.md) — each strategy is asked to describe itself in bytes, which are written to a side file and then moved over the old one, so what is on disk is always one whole version.
- [What a failed save costs the stopping](atoms/what-a-failed-save-costs-the-stopping.md) — a write that fails on the disk loses one strategy's update while leaving what it saved before, a directory that cannot be made loses every update, and a strategy handing back something the writer cannot take costs the shutdown its final saved picture, though the account is still handed back.
- [What a start does with a strategy's saved state](atoms/what-a-start-does-with-a-strategys-saved-state.md) — the saved bytes are handed back to the strategy, with empty bytes standing in where the file is missing or unreadable, and a setting that is left blank means the start never looks.
- [The last record a stopping host writes](atoms/the-last-record-a-stopping-host-writes.md) — on the way out a picture of the state is saved and then the account is handed back, each wrapped so a failure is written down and passed over, and the handing back can fail with the account still registered.
- [What a checkpoint holds](atoms/what-a-checkpoint-holds.md) — the saved picture covers money, risk, holdings and trading state while what each strategy kept for itself goes to separate files; a stopping host, a timer and sometimes a start each ask for one.
- [What the thirty-day cut leaves](atoms/what-the-thirty-day-cut-leaves.md) — trimming the log goes by when each line was written, while the recent-loss figures rebuilt from what is left go by when the thing described happened, and the running total adds up what survived once repeats of one outcome are dropped.
- [What the first stage weighs before the mode](atoms/what-the-first-stage-weighs-before-the-mode.md) — a name with space around it, a request worth nothing, and a strategy whose whole allowance is nothing are each turned away before trading state is looked at, while a request to close or to alter an order is named as exempt from the amount test and the allowance test rather than having to clear them.
- [What settles a request before the first stage](atoms/what-settles-a-request-before-the-first-stage.md) — the name is fixed when the settings are read, while the money allowance is written as the order is put together — from two figures the settings already hold above zero, except on a request to alter an order, which is given no allowance at all.
- [What an entry's sum is worked out from](atoms/what-an-entrys-sum-is-worked-out-from.md) — an order to buy carries either an amount of money or a quantity, and a quantity is trimmed to what the venue trades in before it is priced, which can make the order smaller than was asked for.
- [What Praxis works out for an exit](atoms/what-praxis-works-out-for-an-exit.md) — before the checks see a request to close a holding, that holding is looked up, what is left of it after anything already in progress is computed, and a label is minted where none came.
- [The watch over handovers that timed out](atoms/the-watch-over-handovers-that-timed-out.md) — an order whose handover ran out of time is flagged as unsettled, and a job reports the flags that have stood too long; a final reply the books cannot take in drops the order off the list with its flag still raised, while one that blows up on the way in leaves both standing.
- [What the prediction loop's stop leaves running](atoms/what-the-prediction-loops-stop-leaves-running.md) — the job that reads predictions and hands them to the strategies gathers its work first and then carries it out, so work gathered before the switch-off is still carried out, and can still reach a strategy and put its answer up for the usual checks.
- [What a loop's stop leaves running](atoms/what-a-loops-stop-leaves-running.md) — switching off a repeating background job cancels its next run but lets the run already going finish, so a write can still land after the switch-off has returned.
- [What the halted mode turns away](atoms/what-the-halted-mode-turns-away.md) — while the system is coming down, a strategy's request to open, close or alter is refused by the usual checks, yet two kinds of order still go out, one of them closing positions by a route that skips those checks.
- [Stopping the loop that reads outcomes](atoms/stopping-the-loop-that-reads-outcomes.md) — the reader being switched off is asked to finish and given a while, and one still going when the while is up is left to complete the turn it is in, which can take one more message away from whoever reads next.
- [What a strategy is handed when it is asked to stop](atoms/what-a-strategy-is-handed-when-it-is-asked-to-stop.md) — the holdings it owns, the money it still has room for, and the state trading is in, with its own settings arriving empty.
- [The abort a host sends as it stops](atoms/the-abort-a-host-sends-as-it-stops.md) — a request to drop an order already handed over, naming it by a label the strategy itself supplies.
- [What a stopping host waits for](atoms/what-a-stopping-host-waits-for.md) — it keeps a list as it sends and reads replies until that list is clear; should a set time pass with entries left, it tries to drop them and reads once more for half as long before going down regardless.
- [Where an outcome outside the wait is sent](atoms/where-an-outcome-outside-the-wait-is-sent.md) — a reply arrives for an order the shutdown is not watching, and a second route hands it to the code that keeps the books, which records it against the order where it has a file on one, and otherwise asks for the money back if the reply is a final one.
- [The name an order comes back with](atoms/the-name-an-order-comes-back-with.md) — the label the other side answers with when an order is handed over, and when a label that differs from what was asked for is treated as a failure.
- [Which name a command is kept under](atoms/which-name-a-command-is-kept-under.md) — an order is filed under either the label the sender chose or the label the other side answered with, and which of those applies was fixed long before the order went.
- [Claiming the money after the send](atoms/when-money-set-aside-moves-onto-an-order.md) — on one route the money held in reserve is re-booked against an order only once that order has gone, so a refusal arrives too late to stop it and can leave the reply with no strategy to attach it to.
- [What a strategy’s committed figure moves on](atoms/what-moves-a-strategys-committed-figure.md) — the money held against one strategy is raised on purpose only where it is set aside for a trade; the rest of what touches it is giving money back, except a settling fee that came in over its guess, which pushes it up in the ordinary way of things; a startup replaces it outright.
- [What a pending sale refuses](atoms/what-a-pending-sale-refuses.md) — the cap on selling the same holding twice is applied by the first check a request meets, and the sales a host fires off as it shuts down never meet it.
- [What a pending sale does to the dust](atoms/what-a-pending-sale-does-to-the-dust.md) — an unsettled sale bars one route to writing a holding off and leaves the other wide open, so the same leftover is treated two ways depending on how it got there.
- [What a pending sale is](atoms/what-a-pending-sale-is.md) — a holding records how much of it already has a sale out, which caps what a further sale asking through the checks may request.
- [What a written-back position carries](atoms/what-a-written-back-position-carries.md) — a holding rebuilt at startup from the venue side takes one price as both the price it opened at and the price its money is booked at, where a holding built in the ordinary way keeps those apart.
- [What the host counts when a fill empties a position](atoms/what-the-host-counts-when-a-fill-empties-a-position.md) — a holding is gone before the message announcing its close arrives, so a tally stands in for it and tells a sold-out trade from one that never held anything.
- [Where a position's last scraps go](atoms/where-a-positions-last-scraps-go.md) — the part of a holding too small to sell is written off to a running total per coin, and no decision ever looks at that total again.
- [What a taking-out takes](atoms/what-a-taking-out-takes.md) — releasing the money behind a sale removes what was asked for or as much as is there, and a strategy left with a sliver is dropped from the books entirely.
- [What a start weighs a position at](atoms/what-a-start-weighs-a-position-at.md) — startup values each holding at a different price depending on where it came from, and writes the price it settled on back onto the holding.
- [What a start does with a dusted position](atoms/what-a-start-does-with-a-dusted-position.md) — startup asks the venue side what it is holding and writes back anything missing, so a holding written off can reappear with its money attached.
- [What a dusted scrap leaves behind](atoms/what-a-dusted-scrap-leaves-behind.md) — writing off a holding too small to sell leaves the money it was bought with counted against nothing until the next startup.
- [What money arriving in the account changes](atoms/what-money-arriving-in-the-account-changes.md) — paying money in is written to the log and buys nothing: the sum every allowance is a slice of is fixed when the host starts and never moves.
- [What a fee figure is worked out from](atoms/what-a-fee-figure-is-worked-out-from.md) — the trading cost in a report is a flat thousandth of the fill, while the ledger alongside it books what the venue actually charged, so each trade is recorded as costing one amount in one place and another in the other.
- [Which fills come back with a result](atoms/which-fills-come-back-with-a-result.md) — a purchase reports no gain or loss at all, and the gain on a sale is measured from the price the holding was opened at rather than the price its money is booked at.
- [Where a realized result is written down](atoms/where-a-realized-result-is-written-down.md) — what a sale made or lost is saved to the record before it is counted, so a save that fails leaves nothing counted that was never saved.
- [What the deployed figures out of step refuse](atoms/what-the-deployed-figures-out-of-step-refuse.md) — two records of committed money are kept, and while they disagree no new holding can be opened, though sales and cancellations go through untouched.
- [What a boot rebuilds from the positions](atoms/what-a-boot-rebuilds-from-the-positions.md) — startup works out each strategy’s committed money again from the holdings it can see, and without that pass the first order of the new run is turned down and so is every one after it.
- [What a boot finds stranded](atoms/what-a-boot-finds-stranded.md) — money the last run had committed with nothing left to give it back is written off at startup, at the risk of committing it twice.
- [What the fee reserve absorbs](atoms/what-the-fee-reserve-absorbs.md) — trading costs are guessed before a trade and billed after it, and the account holds money back for the gap.
- [What an exit outcome changes](atoms/what-an-exit-outcome-changes.md) — closing a holding gives money back and reports what the trade made, and those are two different sums.
- [When an entry's position grows](atoms/when-an-entrys-position-grows.md) — buying in pieces leaves one holding at an averaged price, and what that average is later measured against.
- [An outcome waiting on a strategy](atoms/an-outcome-waiting-on-a-strategy.md) — a report matching no strategy yet is set aside, everything after it for that command waits behind, and a wait that never ends costs them all.
- [How Nexus sets money aside](atoms/how-nexus-sets-money-aside.md) — a trade is weighed against its share of the pool, its strategy's budget, the free capital and a ceiling on everything deployed, and the fees are held with it.
- [What Nexus does when a command does not get across](atoms/what-nexus-does-when-a-command-does-not-get-across.md) — the money comes back on every road but one, and that one keeps it on purpose.

## The settings a host runs on

- [The settings a host is given](atoms/the-settings-a-host-is-given.md) — what a host reads from its environment and its manifests before it starts anything.
- [Which settings are refused](atoms/which-settings-are-refused.md) — the checks a host's settings are read through, any one of which failing ends the start.
- [The deployment caps](atoms/the-deployment-caps.md) — the ceilings a host's settings can put on what it may do, from an order's worth to a book's age.
- [Which accounts are refused](atoms/which-accounts-are-refused.md) — the checks each account faces as its manifest is read.
- [Where credentials come from](atoms/where-credentials-come-from.md) — the key and secret for an account, fetched once at startup and handed on to be kept.

## Starting and stopping a host

- [Starting a host](atoms/starting-a-host.md) — what one process does to bring Praxis and Nexus up, in the order it does it.
- [What a starting host reports](atoms/what-a-starting-host-reports.md) — what the figures a starting host publishes actually confirm, and why reading healthy does not mean every account is ready.
- [What a failure at startup does](atoms/what-a-failure-at-startup-does.md) — which steps stop the host when they go wrong, and which are written off.
- [What startup does with orphaned work](atoms/what-startup-does-with-orphaned-work.md) — work the record cannot account for, and orders at the venue it has never heard of.
- [Stopping a host](atoms/stopping-a-host.md) — a host comes down when its stop flag is set, which a signal or an escaping exception does.
- [What becomes of work still open](atoms/what-becomes-of-work-still-open.md) — what a stopping host does with commands part-way through and orders resting at the venue.
- [What a restart puts back](atoms/what-a-restart-puts-back.md) — the live work rebuilt from the record, each kind at the point it had reached, with nothing already at the venue sent again.
- [What a restart puts back of a bracket](atoms/what-a-restart-puts-back-of-a-bracket.md) — a resting pair left alone, one that never got out sent, one mid-change left for the watch, and a stale one passed over.
- [What stopping leaves undone](atoms/what-stopping-leaves-undone.md) — stopping carries on past a refused cancel, a drain out of time and a failed close, logging each, while being called off stops it where it stands.

## Watching a host run

- [Health](atoms/health.md) — what Praxis records about the venue answering, and who can halt an account on it.
- [Alerts](atoms/alerts.md) — how Praxis says something needs a person: a marked log line, and a web call where one is configured.
- [What a host writes about itself](atoms/what-a-host-writes-about-itself.md) — a host writes JSON, one piece per line, each line carrying its level and the moment in UTC.
- [What the logging arrangement misses](atoms/what-the-logging-arrangement-misses.md) — log lines a library writes keep their own shape, and asking the host for plain text does not change them.

## Replaying recorded bars

- [Replay](atoms/replay.md) — running the ordinary path over bars that already happened.
- [What a replay is given](atoms/what-a-replay-is-given.md) — the bars, the money and the strategy text a replay run is handed before it starts.
- [Where a replay's bars come from](atoms/where-a-replays-bars-come-from.md) — a run over real history takes its bars from a prediction frame and a price frame, filtered before use.
- [The frames a replay writes](atoms/the-frames-a-replay-writes.md) — every run writes a price frame and a prediction frame of its own before each bar goes out.
- [The replay clock](atoms/the-replay-clock.md) — the clock moved by hand, one bar at a time.
- [The replay venue](atoms/the-replay-venue.md) — what stands in for an exchange during a replay, holding one price at a time inside the same program.
- [Asking for a replay from outside](atoms/asking-for-a-replay-from-outside.md) — the request that starts a run, and everything it is held to before one begins.
- [What a replay reports](atoms/what-a-replay-reports.md) — the single result a finished walk hands back: bars walked, fills, amounts, fees and what was made.
- [What a replay run reports back](atoms/what-a-replay-run-reports-back.md) — a run asked for over HTTP answers at once with a name, and holds the result until that name is asked after.

## A simulated exchange on the real paths

- [Binsim](atoms/binsim.md) — a simulated exchange Praxis can be pointed at, answering over the web on the real venue's paths.
- [Binsim's book](atoms/binsims-book.md) — a list of prices handed to it, replaced whole, and filled against by walking.
- [Binsim's ledger](atoms/binsims-ledger.md) — what the simulated venue keeps per account: the balances it holds and the fills it has been given.
- [When binsim turns an order away](atoms/when-binsim-turns-an-order-away.md) — the refusals that turn on the venue's own state: a book too old, a name booked before, a balance that cannot cover it, and a size the venue will not take.
- [What a binsim snapshot is turned away for](atoms/what-a-binsim-snapshot-is-turned-away-for.md) — depth, progress and shape are each checked before a snapshot replaces the book, and orders go on filling against whatever was accepted last.

## Summing up a replay or a paper run

- [What a paper run's figures add](atoms/what-a-paper-runs-figures-add.md) — a paper run is summed up like a replay, except its prices are sampled from the market rather than read from bars, and it works out their spacing itself.
- [The paper report](atoms/the-paper-report.md) — how recorded fills and sampled prices become closed-trade results and account figures, asked for during a run or after it.
- [The mark sampler](atoms/the-mark-sampler.md) — the market price noted on a timer between trades, so a paper run has something to value an open position against — and the samples that arrive late or not at all.
- [The two bases the figures come from](atoms/the-two-bases-the-figures-come-from.md) — the same summary figures worked out twice, once from the run's own steps and once from tables of bars.
- [What the parity figures refuse](atoms/what-the-parity-figures-refuse.md) — the bar-based figures turn away empty input, mismatched columns and a prediction that is neither yes nor no, and assume a fee unless told otherwise.
- [The metrics](atoms/the-metrics.md) — the figures a run is summed up by, and the units they come in.

## Routes end to end

A route sequences the articles below into the order things actually happen, and
names every fork. Start here if you want to follow one thing through rather than
look one thing up.

- [Cancelling a trade](spines/cancelling-a-trade.md) — from the asking to the report, including the forks that report nothing at all.
- [Draining an account's queues](spines/draining-an-accounts-queues.md) — one pass of the worker, which every other route is carried by.
- [Changing work already sent](spines/changing-work-already-sent.md) — the checks a change meets, then one arm for each way of working.
- [Stopping a host with work in flight](spines/stopping-a-host-with-work-in-flight.md) — abandon what is in flight, cancel what is resting, and what it carries on through.
- [Starting a host back up](spines/starting-a-host-back-up.md) — replay, ask the venue, and the points that leave an account gated instead of ready.

## How this wiki works

- [The register](register.md) — every topic, whether it is written yet, and everything found while reading the code.
- [The file ledger](ledger.md) — which source files the wiki accounts for, and which it has not touched.
- [Which commits it describes](BASELINE.md) — every article is written against one version of the code, and names it.
- [The article template](TEMPLATE.md) — what every page must carry, including the word limit.

Each article has a word limit. One that outgrows it is split in two rather than
made longer, which is why some titles are narrow.

Both sides are the subject, and Praxis is the side that has been written. 201
articles exist. Of Praxis's own source files 46 are accounted for in full, 38 in
part and 4 not at all; of the 70 in Nexus, 46 are named and 24
untouched — 33 carry a row of their own, and 13 are reached by an
article that needed them. How Nexus decides what to send is the work that
remains. [The file ledger](ledger.md) names every file on both sides, so a
subject with no article can be found there rather than guessed at.

---

Created 2026-09-16 15:31 UTC · Last modified 2026-10-27 13:00 UTC
