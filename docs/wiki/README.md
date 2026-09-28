# How Praxis and Nexus work

Short articles about the system's own workings, in plain words. Each explains one thing and links to the rest from inside the text.

Read them in order if you are new. Every term is explained where it first appears.

## The vocabulary

- [What a venue is](atoms/what-a-venue-is.md) — whatever Praxis sends orders to, real or simulated, and what it is asked to do.
- [What a refusal says](atoms/what-a-refusal-says.md) — the kinds of refusal a venue sends back, and how Praxis reads each.
- [What an account is](atoms/what-an-account-is.md) — the name that owns work, and what is set up when one is registered.
- [Trades, requests and orders](atoms/what-a-trade-is.md) — three names for work at three sizes, and when to use each.
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
- [Orders at several prices](atoms/orders-at-several-prices.md) — spreading an amount across named prices, all sent at once.
- [The account worker](atoms/how-waiting-work-is-drained.md) — the loop each account runs, and what it picks up on each pass.
- [The priority line](atoms/the-priority-line.md) — the separate queue for cancelling and changing, and why it is served first.
- [Work already under way](atoms/work-already-under-way.md) — the work the loop moves along between taking one request and the next.

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

## How this wiki works

- [Which commits it describes](BASELINE.md) — every article is written against one version of the code, and names it.
- [The register](register.md) — every topic, whether it is written yet, and everything found while reading the code.
- [The file ledger](ledger.md) — which source files the wiki accounts for, and which it has not touched.
- [The article template](TEMPLATE.md) — what every page must carry, including the word limit.

Each article has a word limit. One that outgrows it is split into two rather than made longer, so the wiki grows by adding articles.

This wiki is early. Forty-three articles exist, and almost every file in both projects is still untouched. The ledger lists them.

---

Created 2026-09-16 15:31 UTC · Last modified 2026-09-28 07:27 UTC
