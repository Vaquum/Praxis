# How Praxis and Nexus work

Short articles about the system's own workings, in plain words. Each explains one thing and links to the rest from inside the text.

Read them in order if you are new. Every term is explained where it first appears.

## The vocabulary

- [What a venue must be able to do](atoms/what-a-venue-must-be-able-to-do.md) — the operations a venue must declare, named in one place; naming them makes none of them work.
- [What a venue is](atoms/what-a-venue-is.md) — whatever Praxis sends orders to: one per host, called by name, so a live exchange and a simulator run the same code.
- [Backfilling missed trades](atoms/backfilling-missed-trades.md) — asking the venue for trades Praxis did not hear about, after the feed was away or at a start.
- [Holding back sends](atoms/holding-back-sends.md) — a store of permits that refills steadily, which most calls to the exchange take one of; asking the time takes none.
- [Health](atoms/health.md) — what Praxis records about the venue answering, and who can halt an account on it.
- [Asking for a replay from outside](atoms/asking-for-a-replay-from-outside.md) — the request that starts a run, and everything it is held to before one begins.
- [What a replay run reports back](atoms/what-a-replay-run-reports-back.md) — a run asked for over HTTP is answered with a name, and what it came to is told when that name is asked after.
- [Where a replay's bars come from](atoms/where-a-replays-bars-come-from.md) — a run over real history takes its bars from a prediction frame and a price frame, filtered before use.
- [The frames a replay writes](atoms/the-frames-a-replay-writes.md) — every run writes a price frame and a prediction frame of its own before each bar goes out.
- [Where the bars are kept](atoms/where-the-bars-are-kept.md) — the files a strategy is priced against, one per series on disk, read for the last bar that closed.
- [When no price comes back](atoms/when-no-price-comes-back.md) — reading a bar can give nothing back, the file, the frame or the price in it being unusable.
- [The venue feed](atoms/the-venue-feed.md) — a connection kept open per account, over which the venue says what happened to that account's orders unasked.
- [Who refused a send](atoms/who-refused-a-send.md) — a failed send is put down to the venue, to Praxis, or to neither, so a later reader need not judge the wording.
- [What a refusal says](atoms/what-a-refusal-says.md) — a refusal arrives as a named kind, and the kind decides whether the outcome is settled or must be asked after.
- [Alerts](atoms/alerts.md) — how Praxis says something needs a person: a marked log line, and a web call where one is configured.
- [Where credentials come from](atoms/where-credentials-come-from.md) — the key and secret for an account, fetched once at startup and handed on to be kept.
- [What a host writes about itself](atoms/what-a-host-writes-about-itself.md) — a host writes JSON to standard output, one piece per line, each carrying its level and the moment in UTC.
- [What the logging arrangement misses](atoms/what-the-logging-arrangement-misses.md) — the arrangement a host sets up is narrower than it looks: it touches the root alone, and asking for plain text does nothing where a handler is already attached there.
- [Starting a host](atoms/starting-a-host.md) — what one process does to bring Praxis and Nexus up, in the order it does it.
- [What a failure at startup does](atoms/what-a-failure-at-startup-does.md) — which steps stop the host when they go wrong, and which are written off.
- [The settings each way of working takes](atoms/the-settings-each-way-of-working-takes.md) — each way of working carries settings of the kind it registers, and each kind has demands of its own.
- [The change each way of working accepts](atoms/the-change-each-way-of-working-accepts.md) — what a request to alter work must carry, and the one change refused twice over.
- [What each change insists on](atoms/what-each-change-insists-on.md) — the fields each kind of change offers, and the rules each holds them to.
- [The position Praxis keeps](atoms/the-position-praxis-keeps.md) — what Praxis records of the coin it holds per trade, and the one fee it nets off.
- [The order record Praxis keeps](atoms/the-order-record-praxis-keeps.md) — what Praxis holds about one attempt to place an order at the venue.
- [What changes on an order](atoms/what-changes-on-an-order.md) — the fields that move as the venue reports, and the rules that stop applying once the record exists.
- [What a command must carry](atoms/what-a-command-must-carry.md) — one instruction to Praxis, built from what a caller gave and checked as it is built.
- [What a command's checks let through](atoms/what-a-commands-checks-let-through.md) — a command's checks are comparisons, so a value wrong on some other ground passes and breaks later.
- [How a decision becomes a command](atoms/how-a-decision-becomes-a-command.md) — work crossing from Nexus into Praxis is re-keyed field by field, and its settings converted.
- [The payload a mode's settings arrive in](atoms/the-payload-a-modes-settings-arrive-in.md) — a decision carries a mode's settings as a payload, turned into the settings object that mode wants.
- [What a reconciliation tells Nexus](atoms/what-a-reconciliation-tells-nexus.md) — the findings that cross when Praxis squares its books, and the one request that comes the other way.
- [When a balance shortfall is reported](atoms/when-a-balance-shortfall-is-reported.md) — the venue holding less of an asset than the books say, compared asset by asset and told to Nexus.
- [Reports that do not get through](atoms/reports-that-do-not-get-through.md) — what happens to a shortfall Nexus never took, and the stale one that keeps waiting.
- [How an outcome crosses back](atoms/how-an-outcome-crosses-back.md) — Praxis reports running totals for a command and Nexus wants one event's figures, so one report becomes several or none.
- [The figures carried back on a fill](atoms/the-figures-carried-back-on-a-fill.md) — an outcome crossing back on a fill carries differences rather than totals, some covering more than that fill.
- [What stops an outcome crossing twice](atoms/what-stops-an-outcome-crossing-twice.md) — how a repeat is caught, how long it is remembered, and the repeat that gets through.
- [The settings a host is given](atoms/the-settings-a-host-is-given.md) — what a host reads from its environment and its manifests before it starts anything.
- [Which settings are refused](atoms/which-settings-are-refused.md) — the checks a host's settings are read through, any one of which failing ends the start.
- [The deployment caps](atoms/the-deployment-caps.md) — the ceilings a host's settings can put on what it may do, from an order's worth to a book's age.
- [Which accounts are refused](atoms/which-accounts-are-refused.md) — the checks each account faces as its manifest is read.
- [Stopping a host](atoms/stopping-a-host.md) — a host comes down when its stop flag is set, which a signal or an escaping exception does.
- [What becomes of work still open](atoms/what-becomes-of-work-still-open.md) — what a stopping host does with commands part-way through and orders resting at the venue.
- [Abandoning work outright](atoms/abandoning-work-outright.md) — asking Praxis to give up on one command rather than alter it, cancelling at the venue where an order is out.
- [Where an abandonment lands](atoms/where-an-abandonment-lands.md) — what giving up on a command does, by how far that command had got.
- [What stopping leaves undone](atoms/what-stopping-leaves-undone.md) — stopping carries on past a refused cancel, a drain out of time and a failed close, logging each.
- [What a starting host reports](atoms/what-a-starting-host-reports.md) — a starting host says two things about itself, a count of threads in its log and an answer at its endpoint that weighs the stop flag and trading first.
- [What an account is](atoms/what-an-account-is.md) — a name that groups the requests, orders, holdings and queues kept about it.
- [Trades, requests and orders](atoms/what-a-trade-is.md) — a trade, a request and an order: work from outside, one piece of it, and one send to the venue.
- [How an order is named](atoms/how-an-order-is-named.md) — Praxis works an order's name out rather than drawing it at random, so the same inputs always give the same name.
- [Order types](atoms/order-types.md) — the kinds of order Praxis can send, and how a command is built into each.
- [The prices an order must name](atoms/the-prices-an-order-must-name.md) — which kinds of order need a price, a trigger, or both.
- [What a fill is](atoms/what-a-fill-is.md) — a report from a venue that some of an order has traded: an amount, at a price, at a time.
- [The event spine](atoms/the-event-spine.md) — the file Praxis writes its events to, in the order it wrote them.
- [The chain](atoms/the-chain.md) — records carry codes drawn from the record before, so editing a coded one shows up.
- [What the chain proves](atoms/what-the-chain-proves.md) — checking the chain end to end says whether every row that has codes still matches its contents and the row before it.
- [What the chain misses](atoms/what-the-chain-misses.md) — ways of altering the records that the check does not notice.
- [Where duplicates stop](atoms/where-duplicates-stop.md) — the same trade can be reported more than once, and this is where the repeat is caught.
- [What a fill changes](atoms/what-a-fill-changes.md) — a fill updates the order's record and then the money's, so a failure on the first leaves the second alone.
- [When an update fails](atoms/when-an-update-fails.md) — updating those pictures can fail, and sometimes that stops the account.
- [Fills and the order](atoms/fills-and-the-order.md) — how a fill moves an order's totals and status, including one arriving too late.
- [Holdings](atoms/holdings.md) — what one trade holds: which way it went, how much, and the average price paid to build it.
- [The commission and the amount](atoms/the-commission-and-the-amount.md) — why holdings are sometimes credited less than the fill reported.
- [When the commission swallows the fill](atoms/when-the-commission-swallows-the-fill.md) — what happens when the fee equals or exceeds the amount traded.
- [Where the order type decides](atoms/where-the-order-type-decides.md) — the few places where the kind of order alone changes what Praxis does.
- [The order book](atoms/the-order-book.md) — what a venue publishes about a pair: buyers on one side, sellers on the other, each a price and an amount wanted.
- [The kept book](atoms/the-kept-book.md) — Praxis's own copy of the latest offers for a pair, held with the time it arrived so a check need not wait on the venue.

## Getting an order to the venue

- [What turns work away](atoms/what-turns-work-away.md) — the checks an order must pass before Praxis records it at all.
- [Order placement](atoms/how-an-order-is-placed.md) — placing happens in two stages: recording the work and returning, then reaching the venue on a later pass.
- [When a send's outcome is unknown](atoms/when-a-send-is-unclear.md) — a call to the venue can fail without settling whether the order arrived, so Praxis asks the venue before deciding.
- [A reply that cannot be read](atoms/a-reply-that-cannot-be-read.md) — what happens when the venue answers in a shape Praxis cannot understand.
- [The likely-price check](atoms/how-the-likely-price-is-checked.md) — refusing an order that would trade too far from the market price.
- [Estimating the likely price](atoms/how-the-likely-price-is-worked-out.md) — how that price is worked out from the offers standing at the venue.
- [Work fed out over time](atoms/work-fed-out-over-time.md) — an amount broken into slices that go out one at a time with a gap between them.
- [Part-shown orders](atoms/part-shown-orders.md) — one resting order the venue displays only part of at a time.
- [Protection](atoms/protection.md) — a pair of orders put up after an opening order, to close the position at either a good price or a bad one.
- [When protection is put up again](atoms/when-protection-is-put-up-again.md) — protection is put up once, guarded by a flag that turns a second attempt back.
- [Orders at several prices](atoms/orders-at-several-prices.md) — spreading an amount across named prices, an order each, sent one after another in one pass.
- [The account worker](atoms/how-waiting-work-is-drained.md) — each account has one worker going round the same circuit until it is stopped, taking work off a queue.
- [The priority line](atoms/the-priority-line.md) — cancellations and changes wait in a line of their own, emptied on each circuit once the account has started, before anything waiting to be placed.
- [Work already under way](atoms/work-already-under-way.md) — the work the loop moves along between taking one request and the next.

## Changing and stopping

- [Changing work already sent](atoms/changing-work-already-sent.md) — asking Praxis to alter work it has accepted, what may be altered depending on how that work is carried out.

## When time runs out

- [Deadlines](atoms/deadlines.md) — the time by which work is expected to be done, and the moments Praxis measures against it.
- [The expiry cancel](atoms/the-expiry-cancel.md) — an order found past its deadline is settled as expired before the venue is asked, and the expiry is written against the order only where the cancel came back.

## Reporting back

- [Outcomes](atoms/what-an-outcome-is.md) — what Praxis reports back about a request: where it has got to, how much filled, and at what average.
- [The figures an outcome carries](atoms/the-figures-an-outcome-carries.md) — the rules its numbers must satisfy, or it is refused.
- [What an outcome does not check](atoms/what-an-outcome-does-not-check.md) — the figures an outcome's rules never weigh, which is how an impossible report gets through.
- [The figures an outcome reports](atoms/the-figures-an-outcome-reports.md) — two of an outcome's figures mean different things depending on which part of Praxis made the report.
- [How an outcome is delivered](atoms/how-an-outcome-is-delivered.md) — an outcome is written down before it is handed over, and the handing over can fail.
- [How an undelivered outcome is replayed](atoms/how-an-undelivered-outcome-is-replayed.md) — how the next startup works out which reports are not yet accounted for.
- [Who a restart tells again](atoms/who-a-restart-tells-again.md) — a startup resends some reports and not others, and this is which.
- [Outcomes that never come back](atoms/outcomes-that-never-come-back.md) — a resent report stops once a record says the receiver took it, or that Praxis stopped trying.

## Cancelling

- [Cancellation](atoms/how-a-trade-is-cancelled.md) — asking Praxis to stop a request already submitted, answered at once or taken up in the line of its own.

## Replaying instead of trading

- [Replay](atoms/replay.md) — running the ordinary path over bars that already happened.
- [The replay clock](atoms/the-replay-clock.md) — the clock moved by hand, one bar at a time.
- [The replay venue](atoms/the-replay-venue.md) — what stands in for an exchange during a replay, holding one price at a time inside the same program.

## A venue that is not real

- [Ways of working a host may drive](atoms/ways-of-working-a-host-may-drive.md) — a host is told which ways of working it may drive, and work naming one outside that list is turned away.
- [Binsim](atoms/binsim.md) — a simulated exchange Praxis can be pointed at, answering over the web on the real venue's paths.
- [Binsim's book](atoms/binsims-book.md) — a list of prices handed to it, replaced whole, and filled against by walking.
- [Binsim's ledger](atoms/binsims-ledger.md) — what the simulated venue keeps per account: the balances it holds and the fills it has been given.

## The money side

- [The money ledger](atoms/the-money-ledger.md) — Praxis's own account of what a trade cost and what it made, kept beside the holdings.
- [Lots, and what a sell costs](atoms/lots-and-what-a-sell-costs.md) — a buy is remembered as an amount at the price it was bought at, and a sell is costed against those.

## Judging a run

- [What a paper run's figures add](atoms/what-a-paper-runs-figures-add.md) — the step series a paper run brings, what it insists on, and the gap it works out for itself.
- [The paper report](atoms/the-paper-report.md) — worked out afterwards from fills and mark samples.
- [The mark sampler](atoms/the-mark-sampler.md) — what the market was worth between trades, and the gaps it leaves.
- [What a replay is given](atoms/what-a-replay-is-given.md) — the bars, the money and the strategy text a replay run is handed before it starts.
- [What a replay reports](atoms/what-a-replay-reports.md) — the single result a replay hands back: bars walked, fills, amounts, fees and what was made.
- [The two bases the figures come from](atoms/the-two-bases-the-figures-come-from.md) — a run's summary figures are worked out twice, once from a series of steps and once from arrays of bars.
- [What the parity figures refuse](atoms/what-the-parity-figures-refuse.md) — what the bar basis turns away, what it quietly leaves out, and the costs it assumes.
- [The metrics](atoms/the-metrics.md) — the figures a run is summed up by, and the units they come in.

## How this wiki works

- [Which commits it describes](BASELINE.md) — every article is written against one version of the code, and names it.
- [The register](register.md) — every topic, whether it is written yet, and everything found while reading the code.
- [The file ledger](ledger.md) — which source files the wiki accounts for, and which it has not touched.
- [The article template](TEMPLATE.md) — what every page must carry, including the word limit.

Each article has a word limit. One that outgrows it is split into two rather than made longer, so the wiki grows by adding articles.

109 articles exist. Every Praxis module is named in the ledger: 46 are `full`, 37 `partial` and 5 `uncovered`. Of the 70 in Nexus, 16 are cited in passing and 54 untouched. The ledger lists them.

---

Created 2026-09-16 15:31 UTC · Last modified 2026-10-10 07:39 UTC
