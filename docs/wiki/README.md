# How Praxis and Nexus work

Short articles about the system's own workings, in plain words. Each explains one thing and links to the rest from inside the text.

Read them in order if you are new. Every term is explained where it first appears.

## The vocabulary

- [What a venue is](atoms/what-a-venue-is.md) — whatever Praxis sends orders to, real or simulated, and what it is asked to do.
- [Backfilling missed trades](atoms/backfilling-missed-trades.md) — asking the venue for what was missed, and where the asking stops short.
- [Holding back sends](atoms/holding-back-sends.md) — the permits a call must take, and what the exchange says about its own limits.
- [Health](atoms/health.md) — what Praxis records about the venue answering, and who can halt an account on it.
- [The venue feed](atoms/the-venue-feed.md) — the open connection the venue speaks over, and what a reconnection cannot recover.
- [Who refused a send](atoms/who-refused-a-send.md) — which side a failed send is put down to, and when nothing can be said.
- [What a refusal says](atoms/what-a-refusal-says.md) — the kinds of refusal a venue sends back, and how Praxis reads each.
- [Alerts](atoms/alerts.md) — how Praxis says something needs a person, and what gets left out when it does.
- [Where credentials come from](atoms/where-credentials-come-from.md) — where the key and secret are kept, and how far the hiding goes.
- [Starting a host](atoms/starting-a-host.md) — the seven calls one process makes to bring Praxis and Nexus up, in the order it makes them.
- [What a failure at startup does](atoms/what-a-failure-at-startup-does.md) — which steps stop the host when they go wrong, and which are written off.
- [How a decision becomes a command](atoms/how-a-decision-becomes-a-command.md) — the five fields re-keyed as work crosses from Nexus into Praxis, and why.
- [The payload a mode's settings arrive in](atoms/the-payload-a-modes-settings-arrive-in.md) — the three shapes a mode's settings can cross in, and the one mode that behaves unlike the rest.
- [What a reconciliation tells Nexus](atoms/what-a-reconciliation-tells-nexus.md) — the findings that cross when Praxis squares its books, and the one request that comes the other way.
- [When a balance shortfall is reported](atoms/when-a-balance-shortfall-is-reported.md) — the venue holding less than the books say, and when that is small enough to leave alone.
- [Reports that do not get through](atoms/reports-that-do-not-get-through.md) — what happens to a shortfall Nexus never took, and the stale one that keeps waiting.
- [How an outcome crosses back](atoms/how-an-outcome-crosses-back.md) — one report from Praxis can become three for Nexus, or none at all.
- [The figures carried back on a fill](atoms/the-figures-carried-back-on-a-fill.md) — the differences a fill reports, and the two measures that cover more than the fill they ride on.
- [What stops an outcome crossing twice](atoms/what-stops-an-outcome-crossing-twice.md) — how a repeat is caught, how long it is remembered, and the repeat that gets through.
- [The settings a host is given](atoms/the-settings-a-host-is-given.md) — what a host reads from its environment and its manifests before it starts anything.
- [Which settings are refused](atoms/which-settings-are-refused.md) — the checks a setting must pass, and what a failed one does to the start.
- [The deployment caps](atoms/the-deployment-caps.md) — the six ceilings on what a host may do, and the one that is checked twice.
- [Which accounts are refused](atoms/which-accounts-are-refused.md) — the checks each account faces as its manifest is read.
- [Stopping a host](atoms/stopping-a-host.md) — the six steps a host takes to come down, and the two that carry a failure straight out.
- [What becomes of work still open](atoms/what-becomes-of-work-still-open.md) — the two passes over commands and orders, and the one order deliberately left standing.
- [Where an abandonment lands](atoms/where-an-abandonment-lands.md) — what giving up on a command does, by how far that command had got.
- [What stopping leaves undone](atoms/what-stopping-leaves-undone.md) — the three things stopping carries on past, and the one that cuts it short.
- [What a starting host reports](atoms/what-a-starting-host-reports.md) — the count in its log and the answer at its endpoint, and what neither of them looks at.
- [What an account is](atoms/what-an-account-is.md) — the name that owns work, and what is set up when one is registered.
- [Trades, requests and orders](atoms/what-a-trade-is.md) — three names for work at three sizes, and when to use each.
- [How an order is named](atoms/how-an-order-is-named.md) — the three parts of a name, and what is refused.
- [Order types](atoms/order-types.md) — the eight kinds of order Praxis can send, and how each one is built.
- [The prices an order must name](atoms/the-prices-an-order-must-name.md) — which kinds of order need a price, a trigger, or both.
- [What a fill is](atoms/what-a-fill-is.md) — a report that some of an order has traded, and what such a report must say.
- [The event spine](atoms/the-event-spine.md) — the file Praxis writes its events to, in the order it wrote them.
- [The chain](atoms/the-chain.md) — records carry codes drawn from the record before, so editing a coded one shows up.
- [What the chain proves](atoms/what-the-chain-proves.md) — what checking those codes can tell you, and what it cannot.
- [What the chain misses](atoms/what-the-chain-misses.md) — ways of altering the records that the check does not notice.
- [Where duplicates stop](atoms/where-duplicates-stop.md) — the same trade can be reported more than once, and this is where the repeat is caught.
- [What a fill changes](atoms/what-a-fill-changes.md) — the two running pictures a fill updates: the order, and the money.
- [When an update fails](atoms/when-an-update-fails.md) — updating those pictures can fail, and sometimes that stops the account.
- [Fills and the order](atoms/fills-and-the-order.md) — how a fill moves an order's totals and status, including one arriving too late.
- [Holdings](atoms/holdings.md) — how much of a coin a trade is holding, and when that record is removed.
- [The commission and the amount](atoms/the-commission-and-the-amount.md) — why holdings are sometimes credited less than the fill reported.
- [When the commission swallows the fill](atoms/when-the-commission-swallows-the-fill.md) — what happens when the fee equals or exceeds the amount traded.
- [Where the order type decides](atoms/where-the-order-type-decides.md) — the few places where the kind of order alone changes what Praxis does.
- [The order book](atoms/the-order-book.md) — the list of prices on offer, who asks the venue for it, and how far down each looks.
- [The kept book](atoms/the-kept-book.md) — a copy of that list, refreshed in the background, and the two checks that read it.

## Getting an order to the venue

- [What turns work away](atoms/what-turns-work-away.md) — the checks an order must pass before Praxis records it at all.
- [Order placement](atoms/how-an-order-is-placed.md) — recording an order, then sending it, and why those are separate.
- [When a send's outcome is unknown](atoms/when-a-send-is-unclear.md) — a send that neither succeeds nor fails, and how Praxis finds out which.
- [A reply that cannot be read](atoms/a-reply-that-cannot-be-read.md) — what happens when the venue answers in a shape Praxis cannot understand.
- [The likely-price check](atoms/how-the-likely-price-is-checked.md) — refusing an order that would trade too far from the market price.
- [Estimating the likely price](atoms/how-the-likely-price-is-worked-out.md) — how that price is worked out from the order book.
- [Work fed out over time](atoms/work-fed-out-over-time.md) — breaking an amount into slices, how they are sized, and when each goes.
- [Part-shown orders](atoms/part-shown-orders.md) — one resting order the venue displays only part of at a time.
- [Protection](atoms/protection.md) — the pair of orders put up after an opening order fills, and how much they cover.
- [When protection is put up again](atoms/when-protection-is-put-up-again.md) — the guard against a second pair, and the two endings recovery can report.
- [Orders at several prices](atoms/orders-at-several-prices.md) — spreading an amount across named prices, all sent at once.
- [The account worker](atoms/how-waiting-work-is-drained.md) — the loop each account runs, and what it picks up on each pass.
- [The priority line](atoms/the-priority-line.md) — the separate queue for cancelling and changing, and why it is served first.
- [Work already under way](atoms/work-already-under-way.md) — the work the loop moves along between taking one request and the next.

## Changing and stopping

- [Changing work already sent](atoms/changing-work-already-sent.md) — what each way of working lets you alter, and what is refused.

## When time runs out

- [Deadlines](atoms/deadlines.md) — the two time limits an order is measured against, and when each is looked at.
- [The expiry cancel](atoms/the-expiry-cancel.md) — cancelling an order whose time is up, and what the venue's answer changes.

## Reporting back

- [Outcomes](atoms/what-an-outcome-is.md) — the report Praxis sends back about a piece of work, and what it contains.
- [The figures an outcome carries](atoms/the-figures-an-outcome-carries.md) — the rules its numbers must satisfy, or it is refused.
- [What an outcome does not check](atoms/what-an-outcome-does-not-check.md) — the numbers those rules leave alone, and what that allows.
- [The figures an outcome reports](atoms/the-figures-an-outcome-reports.md) — why two of its numbers mean different things depending on what made the report.
- [How an outcome is delivered](atoms/how-an-outcome-is-delivered.md) — recording the report, then handing it over, and what happens if that fails.
- [How an undelivered outcome is replayed](atoms/how-an-undelivered-outcome-is-replayed.md) — how the next startup works out which reports are not yet accounted for.
- [Who a restart tells again](atoms/who-a-restart-tells-again.md) — a startup resends some reports and not others, and this is which.
- [Outcomes that never come back](atoms/outcomes-that-never-come-back.md) — why a resent report stops being resent, and when it never is.

## Cancelling

- [Cancellation](atoms/how-a-trade-is-cancelled.md) — asking the venue to stop an order, and what a confirmed stop does and does not mean.

## Replaying instead of trading

- [Replay](atoms/replay.md) — running the ordinary path over bars that already happened.
- [The replay clock](atoms/the-replay-clock.md) — the clock moved by hand, one bar at a time.
- [The replay venue](atoms/the-replay-venue.md) — what stands in for an exchange, and what it still refuses.

## A venue that is not real

- [Ways of working a host may drive](atoms/ways-of-working-a-host-may-drive.md) — the list a host is given of what it may do, and the three it cannot do against the simulator.
- [Binsim](atoms/binsim.md) — a simulated exchange Praxis can be pointed at, and the three questions it does not answer.
- [Binsim's book](atoms/binsims-book.md) — a list of prices handed to it, replaced whole, and filled against by walking.
- [Binsim's ledger](atoms/binsims-ledger.md) — the balances and fills it keeps, and why only one writer may hold them.

## The money side

- [The money ledger](atoms/the-money-ledger.md) — five accounts, entries that must balance, and what it refuses.
- [Lots, and what a sell costs](atoms/lots-and-what-a-sell-costs.md) — how a buy is remembered, and what happens when a sell is too big.

## Judging a run

- [The paper report](atoms/the-paper-report.md) — worked out afterwards from fills and mark samples.
- [The mark sampler](atoms/the-mark-sampler.md) — what the market was worth between trades, and the gaps it leaves.
- [What a replay is given](atoms/what-a-replay-is-given.md) — the bars, the money and the strategy text a replay run is handed before it starts.
- [What a replay reports](atoms/what-a-replay-reports.md) — the figures a finished run hands back, and where each one is worked out from.
- [The metrics](atoms/the-metrics.md) — the figures a run is summed up by, and the units they come in.

## How this wiki works

- [Which commits it describes](BASELINE.md) — every article is written against one version of the code, and names it.
- [The register](register.md) — every topic, whether it is written yet, and everything found while reading the code.
- [The file ledger](ledger.md) — which source files the wiki accounts for, and which it has not touched.
- [The article template](TEMPLATE.md) — what every page must carry, including the word limit.

Each article has a word limit. One that outgrows it is split into two rather than made longer, so the wiki grows by adding articles.

This wiki is early. Sixty-five articles exist, and almost every file in both projects is still untouched. The ledger lists them.

---

Created 2026-09-16 15:31 UTC · Last modified 2026-10-03 10:02 UTC
