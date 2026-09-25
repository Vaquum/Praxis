# How Praxis and Nexus work

Short articles about the system's own workings, in plain words. Each explains one thing and links to the rest from inside the text.

Read them in order if you are new. Nothing below assumes you already know the vocabulary.

## The vocabulary

- [What a venue is](atoms/what-a-venue-is.md) — what Praxis asks of whatever it sends orders to.
- [What an account is](atoms/what-an-account-is.md) — the name that owns work, and what registering one creates.
- [Trades, requests and orders](atoms/what-a-trade-is.md) — the three names in play, and which one answers which question.
- [Order types](atoms/order-types.md) — the eight kinds, and how each one reaches the venue.
- [The prices an order must name](atoms/the-prices-an-order-must-name.md) — the set each kind owns, and what never passes the check.
- [What a fill is](atoms/what-a-fill-is.md) — one execution the venue reports, and what it must have.
- [Where duplicates stop](atoms/where-duplicates-stop.md) — the record's refusal, and what counts as the same execution.
- [What a fill changes](atoms/what-a-fill-changes.md) — the two projections it is handed to, and what each keeps.
- [When a projection fails](atoms/when-a-projection-fails.md) — the guards around the account loop, and which failures stop it.
- [Fills and the order](atoms/fills-and-the-order.md) — the totals, the status, and a fill that arrives after the end.
- [Holdings](atoms/holdings.md) — what an account has from a trade, and when the record goes away.
- [The commission and the amount](atoms/the-commission-and-the-amount.md) — when a fill credits less than it reports.
- [When the commission swallows the fill](atoms/when-the-commission-swallows-the-fill.md) — a commission at or above the amount, and the four ways it lands.
- [Where the order type decides](atoms/where-the-order-type-decides.md) — the places the kind alone changes the outcome.
- [The order book](atoms/the-order-book.md) — what a venue publishes, who asks for it, and how deep each asker looks.
- [The kept book](atoms/the-kept-book.md) — the copy Praxis polls for, and the two checks that read it.

## Getting an order to the venue

- [What turns work away](atoms/what-turns-work-away.md) — the gates before anything is written down.
- [Order placement](atoms/how-an-order-is-placed.md) — the two stages, and what each one does.
- [When a send's outcome is unknown](atoms/when-a-send-is-unclear.md) — the failures that settle nothing, and what Praxis asks the venue.
- [A reply that cannot be read](atoms/a-reply-that-cannot-be-read.md) — four endings, depending on where the reading fails.
- [The likely-price check](atoms/how-the-likely-price-is-checked.md) — when the order book's answer can stop an order.
- [Estimating the likely price](atoms/how-the-likely-price-is-worked-out.md) — walking the book, and the arithmetic behind the figure.
- [The account worker](atoms/how-waiting-work-is-drained.md) — the circuit each account goes round, and what it takes from where.
- [The priority line](atoms/the-priority-line.md) — where cancellations and changes wait, and why they go first.
- [Work already under way](atoms/work-already-under-way.md) — what the worker carries on with between the two queues.

## Time running out

- [Deadlines](atoms/deadlines.md) — two clocks, and the moments each is read.
- [The expiry cancel](atoms/the-expiry-cancel.md) — what the venue's answer changes, and when nothing is reported.

## Stopping one

- [Cancellation](atoms/how-a-trade-is-cancelled.md) — asking, refusing, and what a confirmed cancellation does and does not prove.

## How this wiki works

- [Which commits it describes](BASELINE.md) — an article is written against a specific version, and says so.
- [The register](register.md) — every topic, its state, and everything found while tracing.
- [The file ledger](ledger.md) — which files are accounted for, and which are not.
- [The article template](TEMPLATE.md) — what every page must carry, including the word limit.

An article that outgrows the limit is split rather than lengthened, so the wiki grows sideways.

This wiki is early. Twenty-eight articles exist. Almost every file in both projects is untouched. The ledger lists them.

---

Created 2026-09-16 15:31 UTC · Last modified 2026-09-25 19:59 UTC
