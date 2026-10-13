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

## Getting an order to the venue

- [Order placement](atoms/how-an-order-is-placed.md) — placing happens in two stages: recording the work and returning, then reaching the venue on a later pass.
- [How an order is named](atoms/how-an-order-is-named.md) — Praxis works an order's name out rather than drawing it at random, so the same inputs always give the same name.
- [The likely-price check](atoms/how-the-likely-price-is-checked.md) — refusing an order that would trade too far from the market price.
- [Estimating the likely price](atoms/how-the-likely-price-is-worked-out.md) — the average price Praxis expects an order to get, worked out by walking the offers standing at the venue.
- [The sizes a venue trades in](atoms/the-sizes-a-venue-trades-in.md) — a venue accepts only certain amounts and prices, and Praxis weighs an order against the figures it holds for that symbol — or sends it unweighed when it holds none.
- [What a venue must be able to do](atoms/what-a-venue-must-be-able-to-do.md) — the jobs every venue has to offer — register an account, place, cancel, report balances — written down as one list.
- [Holding back sends](atoms/holding-back-sends.md) — a limit on how fast Praxis may call the venue: most calls wait for a slot, and asking the time does not.
- [When a send's outcome is unknown](atoms/when-a-send-is-unclear.md) — a call to the venue can fail without settling whether the order arrived, so Praxis asks the venue before deciding.
- [A reply that cannot be read](atoms/a-reply-that-cannot-be-read.md) — what happens when the venue answers in a shape Praxis cannot understand.
- [Who refused a send](atoms/who-refused-a-send.md) — a failed send is put down to the venue, to Praxis, or to neither, so a later reader need not judge the wording.
- [What a refusal says](atoms/what-a-refusal-says.md) — a refusal arrives as a named kind, and the kind decides whether the outcome is settled or must be asked after.

## The pass that takes work off the queues

- [The account worker](atoms/how-waiting-work-is-drained.md) — each account has one worker going round the same circuit until it is stopped, taking work off a queue.
- [The priority line](atoms/the-priority-line.md) — cancellations and changes wait in a line of their own, emptied on each circuit once the account has started, before anything waiting to be placed.
- [Work already under way](atoms/work-already-under-way.md) — what a pass moves along between taking one request and the next — a cancel tried again, a slice now due, protection waiting to go up.
- [When an account is reconciling or poisoned](atoms/when-an-account-is-reconciling-or-poisoned.md) — what a pass does for an account being brought back into step with the venue, or carrying a fault that needs a restart, and when there is no pass left to do it.
- [A change waiting out a hold](atoms/a-change-waiting-out-a-hold.md) — a change to an order already sent is put aside while the account is catching up with the venue, and is never taken up at all once the worker has stopped.
- [How a worker stops taking work](atoms/how-a-worker-stops.md) — the loop an account takes its work from can die, be cancelled, or go on turning without ever reaching that work, and each leaves the account differently placed.

## Ways an order can be worked

- [Ways of working a host may drive](atoms/ways-of-working-a-host-may-drive.md) — a host is given the list of ways it may work an order, and work naming one outside that list is turned away.
- [The settings each way of working takes](atoms/the-settings-each-way-of-working-takes.md) — what each way of working an order asks to be told, and the mistakes in it that get the order refused.
- [Work fed out over time](atoms/work-fed-out-over-time.md) — an amount broken into slices that go out one at a time with a gap between them.
- [Orders at several prices](atoms/orders-at-several-prices.md) — spreading an amount across named prices, an order each, sent one after another in one pass.
- [Part-shown orders](atoms/part-shown-orders.md) — one resting order the venue displays only part of at a time.
- [Protection](atoms/protection.md) — the pair of orders put up after an opening one, to close the position at a good price or at a bad one.
- [When protection is put up again](atoms/when-protection-is-put-up-again.md) — the protective pair goes up once and a second attempt is turned back — except where the prices are being changed, which sends a fresh pair past that guard.

## Changing, cancelling and giving up

- [Changing work already sent](atoms/changing-work-already-sent.md) — asking Praxis to alter work it has accepted, what may be altered depending on how that work is carried out.
- [The change each way of working accepts](atoms/the-change-each-way-of-working-accepts.md) — every request to alter work must name the command, the account and a reason, and a change to how work is spread over time is refused outright.
- [What each change insists on](atoms/what-each-change-insists-on.md) — which fields each way of working lets a change touch, and what it checks before touching them.
- [How a price change is carried out](atoms/how-a-price-change-is-carried-out.md) — a price change replaces the order rather than editing it: the resting one is cancelled, what it really filled is settled, and a fresh one goes out for the rest.
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
- [Where duplicates stop](atoms/where-duplicates-stop.md) — the same fill can arrive from the send, from the live feed and from a later query — it is written down once, and only that copy is acted on.

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
- [What the chain proves](atoms/what-the-chain-proves.md) — checking the chain end to end says whether every row that has codes still matches its contents and the row before it.
- [What the chain misses](atoms/what-the-chain-misses.md) — ways of altering the records that the check does not notice.

## What the venue tells Praxis

- [The venue feed](atoms/the-venue-feed.md) — a connection kept open per account, over which the venue says what happened to that account's orders unasked.
- [The kept book](atoms/the-kept-book.md) — Praxis's own copy of the latest offers for a pair, held with the time it arrived so a check need not wait on the venue.
- [Backfilling missed trades](atoms/backfilling-missed-trades.md) — asking the venue for trades Praxis did not hear about, after the feed was away or at a start.

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
- [Stopping a host](atoms/stopping-a-host.md) — a host comes down when its stop flag is set, which a signal or an escaping exception does.
- [What becomes of work still open](atoms/what-becomes-of-work-still-open.md) — what a stopping host does with commands part-way through and orders resting at the venue.
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

## Summing up a replay or a paper run

- [What a paper run's figures add](atoms/what-a-paper-runs-figures-add.md) — a paper run is summed up like a replay, except its prices are sampled from the market rather than read from bars, and it works out their spacing itself.
- [The paper report](atoms/the-paper-report.md) — how recorded fills and sampled prices become closed-trade results and account figures, asked for during a run or after it.
- [The mark sampler](atoms/the-mark-sampler.md) — the market price noted on a timer between trades, so a paper run has something to value an open position against — and the samples that arrive late or not at all.
- [The two bases the figures come from](atoms/the-two-bases-the-figures-come-from.md) — the same summary figures worked out twice, once from the run's own steps and once from tables of bars.
- [What the parity figures refuse](atoms/what-the-parity-figures-refuse.md) — the bar-based figures turn away empty input, mismatched columns and a prediction that is neither yes nor no, and assume a fee unless told otherwise.
- [The metrics](atoms/the-metrics.md) — the figures a run is summed up by, and the units they come in.

## How this wiki works

- [The register](register.md) — every topic, whether it is written yet, and everything found while reading the code.
- [The file ledger](ledger.md) — which source files the wiki accounts for, and which it has not touched.
- [Which commits it describes](BASELINE.md) — every article is written against one version of the code, and names it.
- [The article template](TEMPLATE.md) — what every page must carry, including the word limit.

Each article has a word limit. One that outgrows it is split in two rather than
made longer, which is why some titles are narrow.

The wiki is about Praxis. How Nexus decides is barely written up here: it
appears where decisions cross into Praxis and where results cross back. 115
articles exist. Of Praxis's own source files 46 are accounted for in full, 37 in
part and 5 not at all; of the 70 in Nexus, 17 are cited in passing and 53
untouched. [The file ledger](ledger.md) names every one of them, so a subject
with no article can be found there rather than guessed at.

---

Created 2026-09-16 15:31 UTC · Last modified 2026-10-12 19:08 UTC
