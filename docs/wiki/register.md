# Path register

One row per topic. A row exists before its article does. No row, no trace; no trace, no article.

Status: `seeded` approved but not traced · `traced` evidence gathered · `written` article exists · `reviewed` reviewer re-derived it from source.

## Package 1

| ID | Topic | Status | Article |
|---|---|---|---|
| P1-01 | Trades, requests and orders | written | [what-a-trade-is.md](atoms/what-a-trade-is.md) |
| P1-02 | Order placement | written | [how-an-order-is-placed.md](atoms/how-an-order-is-placed.md) |
| P1-03 | The account worker | written | [how-waiting-work-is-drained.md](atoms/how-waiting-work-is-drained.md) |
| P1-04 | Cancellation | written | [how-a-trade-is-cancelled.md](atoms/how-a-trade-is-cancelled.md) |
| P1-05 | The likely-price check | written | [how-the-likely-price-is-checked.md](atoms/how-the-likely-price-is-checked.md) |
| P1-06 | Estimating the likely price | written | [how-the-likely-price-is-worked-out.md](atoms/how-the-likely-price-is-worked-out.md) |
| P1-07 | When a send's outcome is unknown | written | [when-a-send-is-unclear.md](atoms/when-a-send-is-unclear.md) |
| P1-08 | The priority line | written | [the-priority-line.md](atoms/the-priority-line.md) |
| P1-09 | Work already under way | written | [work-already-under-way.md](atoms/work-already-under-way.md) |
| P1-10 | A reply that cannot be read | written | [a-reply-that-cannot-be-read.md](atoms/a-reply-that-cannot-be-read.md) |

## Package 2 — the vocabulary

Package 1 leans on terms it never defines. Counted over its ten bodies: venue 24 times, account 21, filled or fill 9, run 7, ladder 7, slice 5, market order and order book throughout the two price articles. A reader meeting any of these for the first time has nowhere to go.

Seeded, not traced. No article exists for these yet.

| ID | Topic | Status | Article |
|---|---|---|---|
| P2-11 | What a venue is, and what Praxis asks of one | written | [what-a-venue-is.md](atoms/what-a-venue-is.md) |
| P2-12 | What an account is | written | [what-an-account-is.md](atoms/what-an-account-is.md) |
| P2-13 | The order book, and what a venue publishes in it | written | [the-order-book.md](atoms/the-order-book.md) |
| P2-26 | The kept copy of the book, and the two checks that read it | written | [the-kept-book.md](atoms/the-kept-book.md) |
| P2-27 | The places the order type alone changes the outcome | written | [where-the-order-type-decides.md](atoms/where-the-order-type-decides.md) |
| P2-28 | The prices each order type must and must not name | written | [the-prices-an-order-must-name.md](atoms/the-prices-an-order-must-name.md) |
| P2-29 | The two running pictures a fill updates, and what each keeps | written | [what-a-fill-changes.md](atoms/what-a-fill-changes.md) |
| P2-30 | When the commission comes out of the amount credited | written | [the-commission-and-the-amount.md](atoms/the-commission-and-the-amount.md) |
| P2-31 | What a fill does to the order it belongs to | written | [fills-and-the-order.md](atoms/fills-and-the-order.md) |
| P2-32 | Where a repeated fill is caught, and what counts as the same one | written | [where-duplicates-stop.md](atoms/where-duplicates-stop.md) |
| P2-33 | What happens when a commission equals or exceeds the fill it is charged on | written | [when-the-commission-swallows-the-fill.md](atoms/when-the-commission-swallows-the-fill.md) |
| P2-34 | Where a failed update lands, and which ones stop the account | written | [when-an-update-fails.md](atoms/when-an-update-fails.md) |
| P2-35 | The hashes sealing one row to the next | written | [the-chain.md](atoms/the-chain.md) |
| P2-36 | What a walk of the chain refuses, and what it leaves unsaid | written | [what-the-chain-proves.md](atoms/what-the-chain-proves.md) |
| P2-37 | The changes a walk of the chain does not catch | written | [what-the-chain-misses.md](atoms/what-the-chain-misses.md) |
| P2-38 | What happens between an outcome being made and the caller hearing it | written | [how-an-outcome-is-delivered.md](atoms/how-an-outcome-is-delivered.md) |
| P2-39 | How an outcome the caller never took is sent again | written | [how-an-undelivered-outcome-is-replayed.md](atoms/how-an-undelivered-outcome-is-replayed.md) |
| P2-40 | The figures an outcome must agree on, and the arithmetic nothing checks | written | [the-figures-an-outcome-carries.md](atoms/the-figures-an-outcome-carries.md) |
| P2-41 | What settles a replayed outcome, and what leaves it owed | written | [outcomes-that-never-come-back.md](atoms/outcomes-that-never-come-back.md) |
| P2-42 | The figures an outcome is never checked against | written | [what-an-outcome-does-not-check.md](atoms/what-an-outcome-does-not-check.md) |
| P2-43 | What the slice counts and the progress figure are worth, by producer | written | [the-figures-an-outcome-reports.md](atoms/the-figures-an-outcome-reports.md) |
| P2-45 | What a venue refusal says, and how each kind is read | written | [what-a-refusal-says.md](atoms/what-a-refusal-says.md) |
| P3-01 | Replay, and driving the live path over recorded bars | written | [replay.md](atoms/replay.md) |
| P3-02 | The simulated clock a replay runs on | written | [the-replay-clock.md](atoms/the-replay-clock.md) |
| P3-03 | The in-process venue a replay sends to | written | [the-replay-venue.md](atoms/the-replay-venue.md) |
| P3-04 | What a replay run is given, and what it reports | seeded | — |
| P3-05 | Binsim, the standalone simulated venue | written | [binsim.md](atoms/binsim.md) |
| P3-06 | Binsim's book, and the feed that replaces it | written | [binsims-book.md](atoms/binsims-book.md) |
| P3-07 | Binsim's per-account balances and fills | written | [binsims-ledger.md](atoms/binsims-ledger.md) |
| P3-08 | Paper trading, and the report built from the spine | written | [the-paper-report.md](atoms/the-paper-report.md) |
| P3-09 | The mark sampler, and the equity series it keeps | written | [the-mark-sampler.md](atoms/the-mark-sampler.md) |
| P3-10 | What the metrics measure, and the conventions they report in | written | [the-metrics.md](atoms/the-metrics.md) |
| P3-11 | The double-entry ledger: accounts and balanced entries | written | [the-money-ledger.md](atoms/the-money-ledger.md) |
| P3-12 | Lots, the two ways of keeping them, and what a sell costs | written | [lots-and-what-a-sell-costs.md](atoms/lots-and-what-a-sell-costs.md) |
| P3-13 | Changing work already submitted | written | [changing-work-already-sent.md](atoms/changing-work-already-sent.md) |
| P3-14 | How an order is named | written | [how-an-order-is-named.md](atoms/how-an-order-is-named.md) |
| P3-15 | Health, and what a failing venue does to an account | written | [health.md](atoms/health.md) |
| P3-16 | The venue feed, and what arrives on it | written | [the-venue-feed.md](atoms/the-venue-feed.md) |
| P3-17 | Backfilling trades the feed missed | written | [backfilling-missed-trades.md](atoms/backfilling-missed-trades.md) |
| P3-18 | Rate limiting, and the budget a send takes from | seeded | — |
| P3-19 | Where credentials come from | seeded | — |
| P3-20 | Alerts, and what raises one | seeded | — |
| P3-21 | What a send failure is classified as | seeded | — |
| P3-23 | The guard against a second protective pair, and the two endings recovery can report | written | [when-protection-is-put-up-again.md](atoms/when-protection-is-put-up-again.md) |
| P3-22 | Modes allowed only against a real venue | seeded | — |
| P2-44 | Which caller a restart offers an outcome to again, and which it does not | written | [who-a-restart-tells-again.md](atoms/who-a-restart-tells-again.md) |
| P2-14 | Order types, and what a market order means here | written | [order-types.md](atoms/order-types.md) |
| P2-15 | What a fill is | written | [what-a-fill-is.md](atoms/what-a-fill-is.md) |
| P2-16 | Holdings, and how a fill changes them | written | [holdings.md](atoms/holdings.md) |
| P2-17 | The event spine, and what writing down means | written | [the-event-spine.md](atoms/the-event-spine.md) |
| P2-18 | Outcomes, and what partial reports | written | [what-an-outcome-is.md](atoms/what-an-outcome-is.md) |
| P2-19 | Runs, and the slices they are fed out in | written | [work-fed-out-over-time.md](atoms/work-fed-out-over-time.md) |
| P2-20 | Ladders, and their rungs | written | [orders-at-several-prices.md](atoms/orders-at-several-prices.md) |
| P2-21 | Protection, and the order that carries it | written | [protection.md](atoms/protection.md) |
| P2-22 | Hidden-size orders, and what the venue shows | written | [part-shown-orders.md](atoms/part-shown-orders.md) |
| P2-23 | Deadlines, and the two clocks they run on | written | [deadlines.md](atoms/deadlines.md) |
| P2-24 | What turns work away before it is queued | written | [what-turns-work-away.md](atoms/what-turns-work-away.md) |
| P2-25 | The expiry cancel | written | [the-expiry-cancel.md](atoms/the-expiry-cancel.md) |

Numbering starts at P2-11 because the harvest already bound P2-01 to P2-04 to modification, the bracket change, run cancellation and the schedule change. Those rows now name their subject rather than an ID that pointed at nothing.

Order follows dependency. A venue and an account own nothing else and are used most. The book and the order types come next because the two price articles rest on both without defining either. A fill is one execution at the venue; holdings are what a fill changes, netting a fee the command's own total does not. The spine is what package 1 calls writing down and recording, which currently stand unexplained. Outcomes own *partial*, which is a report status and not a kind of fill — that distinction is why a fill and an outcome are two rows and not one. Runs own *slice*; ladders are a separate arm of the dispatch that submits every rung at once, so neither folds into the other. A hidden-size order is a third arm again, sending one order for the whole amount while showing the venue a smaller one. Deadlines are seeded rather than held back because there are two clocks, not one: unstarted work is judged from when it was accepted, and a run that has started is judged from a fresh window opened when it started.

Two costs are known before tracing starts. Each article makes every unlinked mention of its term in package 1 a check failure, so each carries a pass back through the existing ten. And the term check only carries terms whose string cannot mean anything else. The rest were put to a reviewer against all ten bodies, phrase by phrase, before any of these articles is written. The mentions that must *not* link:

| Phrase | In | Why not |
|---|---|---|
| "until the order is filled", "too thin to fill" | estimating the likely price | the book walk completing, not a recorded execution |
| "a held or failed account", "on hold", "what holds a pass back" | the worker, the priority line, work already under way | an account suspended, not inventory |
| "the run stays on the books" | work already under way | an idiom; neither the order book nor a spine write |
| "this runs early", "cancellations still run", "until the money runs out" | work already under way, the priority line, estimating | execution order and exhaustion, not a fed-out run |
| "when a send's outcome is unknown" | its own title, and two links to it | whether the send arrived, not the request's outcome |
| "refuse the order on the result", "stopped by the result" | the likely-price check | the calculation's result |
| "the worker logs it", "the record is put back for a later pass" | a reply that cannot be read, work already under way | diagnostic logging and retry state, not spine writes |

Two facts fall out of that pass. The spine's subject is carried entirely without its name — "writes down", "records", "the intent stays recorded" across five articles — so a string check would have found none of it. And *partial* appears in no body at all, so the second half of P2-18 has nothing in package 1 to attach to yet.


Five are written: venue, account, deadlines, and two carved out while writing them — the expiry cancel from deadlines, and the pre-queue gates from order placement, both because stating their branches accurately took the parent past the cap.

A second reviewer read the first four of these until its account ran out of credit. Everything since has had one reviewer only, and all five changed after that second one last read them. They want another pass when it is available.

### Held back from package 2

| Topic | Why |
|---|---|
| What an execution mode is | A survey of the modes is a table of contents until the modes themselves are written. The bodies never use the word. |
| What a linked pair is | The ten bodies never use it; the mentions are in evidence only. It reads as venue machinery, so it follows P2-11 if it is wanted at all. |
| What a slice is | Owned by P2-19 rather than standing alone. |

Two foundations and two of the subjects the brief names. Cancellation is written, so modification is unblocked; it waits behind the vocabulary rather than ahead of it, since it is carried out as a cancel followed by a replacement and both ends are terms package 2 defines.

Six of the ten articles exist because another outgrew the limit. P1-10 was carved out when review found that an unreadable venue reply has four different endings depending on where the reading fails, and stating them took the parent past the cap. P1-09 was carved out when review found a whole stage missing from the worker article — a requested sweep of seven repair jobs, the first of which repeats the cancellation retry with its timing test dropped. Stating that accurately took the parent past the cap. P1-07 and P1-08 were carved out when the word count was corrected to include heading text: converting run-in bold paragraphs into headings during the voice rewrite had moved words off the counted side, and fixing that put four articles over. P1-07 was anticipated below as "an unclear answer from the venue"; P1-08 had already been linked by name from another article, which is the sign a term deserves its own page. P1-05 was carved out of P1-02 when the book check grew into a subject of its own. P1-06 was then carved out of P1-05 when a review added the sell-side sign flip and the ways the book can yield nothing, pushing it to 332 words: the check itself stayed in P1-05, the arithmetic moved to P1-06. Both splits were forced by the word count, which is the mechanism working. Expect the same for a venue refusing an order, and for an unclear answer from the venue.

### Considered and deferred

| Topic | Why |
|---|---|
| What execution modes are | A survey of five modes is either a list of names or an overflow, and spending a first-package slot on a table of contents delays the subjects the brief names. |
| How a trade is modified | Follows cancellation, which it is built on. |

## Considered and rejected

Kept so they are not rediscovered as new.

| Subject | Why |
|---|---|
| The venue filled more than I asked for. What does the system do with the extra? | Valid question, wrong package. Serves fills and accounting, not the modify, cancel and drain priority. |
| My order is waiting to be placed. When does it get its turn? | Permits a scheduler explanation with no usable conclusion. Its subject is now covered as P1-03. |
| I asked to change an order. What happens to the original one? | Asks the after-state. Modification is deferred to the next package in full. |
| How to tell whether an order is waiting, in flight, or live | A question a reader asks, not a subject the system has. Identifying state belongs inside the articles that describe each stage. |
| The place timed out. Can I send the same order again? | A distinct subject, deferred. P1-02 states only that a lookup happens, not what to do next. |

## Carried to the next package

Found while answering package 1, not answered by it. These enter the next package as candidates — not approved subjects yet, and the next round may reject or rewrite any of them.

| Candidate | Why it is here | Owner |
|---|---|---|
| After a placement times out, can the same order safely be sent again? | P1-02 says only that Praxis asks the venue about the name it used. What a caller should do next is untouched. | unassigned |
| What happens to an order fed out in slices, or a bracket, when its deadline passes? | P1-03 covers only the pass-level check before such work is started. | unassigned |
| How a trade is modified | Built on cancellation, which is now written. The next subject in line. | unassigned |
| Does the venue feed actually repair a record written off after an unanswerable lookup? | H-025 shows the claim lives only in a docstring. | unassigned |
| Is the deferred ladder-cancel report (U-03) worth raising against Praxis? | A caller waiting on that cancellation hears nothing until a restart, and then hears "rejected as a boot orphan" rather than "cancelled". Weaker than first recorded, since the report is not lost. | unassigned |
| Is the hardcoded base asset in the holdings fee-netting (U-04) a live defect? | Holdings net a buy's commission only when the fee asset is `'BTC'`. On any other symbol the record sits above the wallet by the commission on every buy — the compounding error the netting exists to prevent. Prod trades one symbol today, so the reach depends on whether a second is ever added. | unassigned |
| Are two terminal outcomes for one command id a live defect (U-05)? | H-050 traces `CANCELED` then `FILLED` for one exit command id through bracket protection recovery. A caller that treats the first terminal report as final would have the trade's end wrong. Needs a decision on whether the second report is intended, and whether the exit command should carry a fresh id. | unassigned |
| Does a schedule change survive a restart? | H-040 shows the docstring and TD-135 both say it is lost. Neither is a body. | unassigned |

## Harvest

Behaviours met while tracing. Each ends as a row, a fold into a row, or an exclusion with a reason. Nothing is dropped silently.

| Harvest ID | Question or observation | Source anchor | From | Disposition |
|---|---|---|---|---|
| H-001 | A newly queued order does not wake the worker. Only an admitted event sets the wake flag; commands wait out the poll interval, currently 0.1s. | `execution_manager.py` `_wait_for_work` 3876-3888, `admit` 3212, `_QUEUE_POLL_INTERVAL` 143 | P1-03 | folds into P1-03 |
| H-002 | While the account is still starting, the worker does nothing at all — it sleeps a poll interval and starts the round again. | `execution_manager.py` `_account_loop` 3903-3905 | P1-03 | folds into P1-03 |
| H-003 | The priority queue drains fully every pass. The command queue yields at most one order per pass. | `execution_manager.py` 3910, 3984 | P1-03 | folds into P1-03 |
| H-004 | A cancel runs even while the account is reconnecting or stopped; a change is deferred and put back on the queue to retry next pass. | `execution_manager.py` 3912-3928, 3953-3954 | P1-03 | split: cancel half folds P1-04, change half folds modify (deferred) |
| H-005 | A stopped account fails every waiting order instead of sending it. | `execution_manager.py` `_fail_queued_commands` 3963 | P1-03 | folds into P1-03 |
| H-006 | While reconnecting but not stopped, the worker halts before the command queue. Waiting orders are neither sent nor ended — they stay. | `execution_manager.py` 3966-3968 | P1-03 | folds into P1-03 |
| H-007 | Venue news is drained before any new order is started. | `execution_manager.py` `_drain_external_events` 3906 | P1-03 | folds into P1-03 |
| H-008 | A sliced order past its deadline is ended without being sent, with no slices placed. A single order has separate deadline handling after submission. | `execution_manager.py` `_expire_stale_command` 4100-4112 | P1-03 | folds into P1-03 |
| H-009 | Scheme slices, pending protection and a protection sweep all run before the command queue is reached. | `execution_manager.py` 3971-3978 | P1-03 | folds into P1-03 |
| H-010 | A cancel for an order that has not reached the venue is only marked, not acted on. The mark is what stops it later. | `execution_manager.py` `_process_abort` 8500-8511 | P1-04 | folds into P1-04 |
| H-011 | Every starting path checks the cancel mark before doing anything else, and ends the order with no fills if one is set. | `execution_manager.py` 4154, 4482, 5275, 5713, 6074 | P1-04 | folds into P1-04 |
| H-012 | Because cancels drain fully before any order is taken, a cancel already queued when a pass begins beats the order that pass would have sent. | `execution_manager.py` 3910 with 3984 | P1-04 | folds into P1-04 |
| H-013 | A cancel aimed at an order that already finished is dropped at submission and never queued. | `validate_trade_abort.py` 40-53, `execution_manager.py` 3014-3021 | P1-04 | folds into P1-04 |
| H-014 | A cancel for an order the venue already has takes a different route: it asks the venue to cancel and records whether the venue confirmed. | `execution_manager.py` `_process_abort` 8515-8532 | P1-04 | folds into P1-04 |
| H-015 | A cancel aimed at a sliced order goes to a separate path rather than the single-order one. | `execution_manager.py` `_abort_scheme` 8489-8491 | P1-04 | folds into P1-04 |
| H-016 | A price change is not an edit. The resting order is cancelled, the venue is asked what it really filled, and a fresh order is placed for what is left. | `execution_manager.py` `_process_modify` 8583-8600 | modify (deferred) | folds into modify (deferred) |
| H-017 | The replacement is placed only after the original is confirmed gone and any fill that raced the cancel has been accounted for. Both orders live at once is not reachable by this route. | `execution_manager.py` `_drive_single_amend` 8776-8800 | modify (deferred) | folds into modify (deferred) |
| H-018 | If the racing fill cannot be accounted for, the change is parked and the original is deliberately left unfinished, so the missed fill stays recoverable instead of being stranded. | `execution_manager.py` 8783-8784 with 8766-8771 | modify (deferred) | folds into modify (deferred) |
| H-019 | The size of the replacement is worked out from what the venue says was filled, not from the local picture, so a racing fill cannot cause over-ordering. | `execution_manager.py` 8797-8799 | modify (deferred) | folds into modify (deferred) |
| H-020 | A record is written before the cancel, so a restart in the middle rebuilds the sequence rather than reusing an order name. | `execution_manager.py` 8589-8595 | modify (deferred) | folds into modify (deferred) |
| H-021 | A change aimed at an order that already finished is dropped. A sliced order and a bracket each go to their own change path. | `execution_manager.py` 8615-8624 | modify (deferred) | folds into modify (deferred) |
| H-022 | Two different waits can time out and they are not the same event: the decision side waiting on the execution side, and the execution side waiting on the venue. The reader's evidence and the system's response differ for each. | Nexus `action_submit.py` 337-368; Praxis `_rescue_by_client_order_id` 5476-5545 | timeout (carried) | folds into timeout (carried) |
| H-023 | When the decision side gives up waiting, the order is marked unknown rather than failed. The money stays held and the records stay, so a later report can still be matched to it. | Nexus `action_submit.py` 338-368 | timeout (carried) | folds into timeout (carried) |
| H-024 | When the execution side gives up waiting on the venue, it asks the venue directly whether the order exists, using the name it sent. | Praxis `_rescue_by_client_order_id` 5518-5523 | timeout (carried) | folds into timeout (carried) |
| H-025 | If that question cannot be answered, the order is recorded as refused even though the venue may hold it. The body logs and gives up; that the venue feed later repairs the record appears only in the docstring at 5505-5510 and no body establishes it. | Praxis body 5533-5542 | timeout (carried) | promoted to U-01; repair claim unverified |
| H-026 | The money is given back straight away only for failures that provably happened before the request was handed over. | Nexus `action_submit.py` 273, 300, 325 | timeout (carried) | folds into timeout (carried) |
| H-027 | Is an order held under an unknown result ever swept and released, and on what schedule? Not established by this trace. | — | timeout (carried) | promoted to U-02 |
| H-028 | A replacement that fails to place ends the whole order as cancelled, counting the fills from both the old order and the failed replacement. The original is already gone by then. | `_emit_amend_failed` 10481-10513 | modification | folds into modification |
| H-029 | A replacement that times out is not assumed dead. The venue is asked about it first, and if the venue has it the change carries on normally. | `_process_modify` 10355-10366 | modification | folds into modification |
| H-030 | If that question to the venue cannot be answered, the order is ended as cancelled anyway, though the venue may hold the replacement. Same gap as U-01, on the replacement. | 10360-10365 with `_rescue_by_client_order_id` 5505-5511 | modification | folds into modification; extends U-01 |
| H-031 | Changing a bracket's protective prices is a cancel and replace, not an edit. The resting pair is cancelled, the exposure is recomputed from the venue, and a new pair is placed. | `_process_bracket_modify` 9366-9379 | bracket change | folds into the bracket change |
| H-032 | Each durable record is written before the venue action it authorises, so a crash cannot leave an action nobody recorded. | 9370-9375 | bracket change | folds into the bracket change |
| H-033 | Three endings: protection active again, an unclear cancel that stops and waits for reconciliation, or a definite failure to replace. What happens after a failure is decided elsewhere. | 9376-9379 | bracket change | folds into the bracket change |
| H-034 | Cancelling a running sliced order stops further scheduling and cancels any child still working at the venue. | `_abort_scheme` 6525-6532 | run cancellation | folds into run cancellation |
| H-035 | One cancelled result is reported for the whole order, and only once every child has settled — at once if none were working, otherwise as each cancel confirms. | 6528-6531 | run cancellation | folds into run cancellation |
| H-036 | A ladder caught mid-change retires both generations and places no replacement rungs. | 6530-6532 | run cancellation | folds into run cancellation |
| H-037 | Changing slice count or interval re-plans only the slices not yet fired, and restarts the clock so the next one is a full new interval away. | `_process_scheme_modify` 10054-10062 | schedule change | folds into the schedule change |
| H-038 | A new total at or below what has already fired is refused. Shrinking below what is done is not how you stop a scheme; cancelling is. | 10062-10065 | schedule change | folds into the schedule change |
| H-039 | A successful change resumes a scheme frozen by a failed slice, but one frozen for protection reasons cannot be resumed this way and the change is refused. | 10065-10068, 10083-10087 | schedule change | folds into the schedule change |
| H-040 | That a restart loses a schedule change is asserted by the docstring at 10068-10070 and by TD-135. Neither is a body. Re-trace the restart path before any article repeats it. | docstring only; body not traced | schedule change | blocked: needs a body trace |
| H-043 | A plain single order still pending or partly filled once its acceptance deadline has passed is cancelled at the venue and reported expired. A not-found cancel still counts as expired; a failed one carries the failure in the reason. None of the ten bodies says this happens. | `execution_manager.py` 4411-4436 | P2-23 | folds into P2-23; P1-02 now states it and links there |
| H-044 | A run or a ladder that has started is judged against a new window opened at its start, not against the clock its command was accepted on. | `execution_manager.py` 5784-5787 and 6128-6131, against 2925 | P2-23 | folds into P2-23 |
| H-042 | A ladder cancelled before its first rung, reaching `_start_ladder` before its deadline, passes a zero slice total into the terminal emitter. `TradeOutcome` refuses it, the `ValueError` is caught and logged, and no outcome is produced at the time. The command survives as an accepted command with no intent, so the next start classes it a boot orphan and dispatches a REJECTED outcome. The caller is told, but only after a restart, and as a rejection rather than a cancellation. | `execution_manager.py` 6077-6081 into 8411-8423, refused by `trade_outcome.py` 146-148, swallowed at 4012-4019; recovered at 2254-2275 into 2297-2330 | P1-04 | U-03 corrected: a deferred, mislabelled report, not a lost one |
| H-045 | The base-asset commission is netted out of holdings only where the fee asset equals a hardcoded `'BTC'`. A buy of any other symbol whose commission is charged in that symbol's base asset is credited gross, which is the condition the netting was written to remove. | `trading_state.py` 66 with the test at 84-85, netted at 483 | P2-16 | raised as U-04; the money ledger refuses a second symbol outright and that refusal is swallowed |
| H-046 | The `Fill` domain type validates its fields and carries a deduplication key, and nothing in the live path constructs one. Every fill flows as a `FillReceived` event instead. Exported from `domain/__init__` and exercised only by `test_domain_core.py`. | no construction site in `praxis/core` or `praxis/infrastructure`; built at `tests/test_domain_core.py` 35 | P2-15 | recorded; article describes the event |
| H-047 | A first BUY whose fee asset is `'BTC'` and whose fee equals the filled quantity exactly creates a holding of zero. `Position` permits zero, and the branch that drops an emptied record runs only for a reducing fill, so the empty record stands; a later same-side fill delivering zero against it divides zero by zero. A larger such fee makes the quantity negative and `Position` refuses construction. A sell, or any other fee asset, keeps the gross quantity and is unaffected. The money ledger refuses the same fill, and that refusal is swallowed. | `trading_state.py` 483 into 487-498, permitted by `position.py` 52-53, dropped only at 518-522, divided at 500-503; ledger refusal at `account_ledger.py` 305-307 swallowed by `execution_manager.py` 2092-2098 | P2-16 | recorded; P2-33 states the landings, including the second zero-delivery fill failing on the empty record |
| H-048 | Truncating the event spine is not detected. `verify_chain` walks the rows present, checking each backward link and recomputing each hash, and finishes without comparing the final row against any recorded tip or count. `spine_meta` stores the chain version, the genesis anchor and a legacy dedup symbol, and no expected tip. Removing a suffix of rows therefore leaves a chain that verifies, with no mark recomputed. | walked at `event_spine.py` 1254-1291 with no tip comparison; the meta keys at 100-102, written at 593-595 | P2-37 | recorded; P2-37 states truncation among the escapes |
| H-049 | Clearing the `hash` column on every row makes `verify_chain` treat the whole spine as the legacy prefix and skip it entirely. `in_legacy_prefix` starts true and is only cleared by the first hashed row, so an all-unhashed spine passes every check without one being run, and the contents can be changed freely with no mark recomputed and no row removed. Cheaper than the truncation of H-048, which at least leaves the surviving rows sealed. | `event_spine.py` 1255 into 1261-1269, with 1270 never reached | P2-37 | recorded; P2-37 states it among the escapes |
| H-050 | Two terminal outcomes for one `command_id` are reachable, refuting the universal uniqueness `TradeOutcome`'s module docstring claims is enforced upstream. A protective pair's cancellation produces `CANCELED` for the bracket's exit command; dispatch then hands the surviving bracket to protection recovery, which on a confirmed naked remainder under `FLATTEN_THEN_HALT` submits a flatten under the same exit command id, derived deterministically from the bracket's own, and re-installs that command after it was dropped as terminal. A closing order finished with something filled as that send returns then reaches `_build_outcome` with no guard, giving `CANCELED` then `FILLED` for one id. A fill arriving later on the feed instead meets the terminal-command guard at 10663 and is turned back, so it is specifically the immediate fill that does it. | claimed at `trade_outcome.py` 6-7; `CANCELED` at `execution_manager.py` 10662-10741; recovery at 3863-3865 into 4680-4696; the shared id derived at 7608 and the flatten submitted at 7707-7709; re-installed at 7814; unguarded at 7859-7883 against the four guards at 4786, 8482, 8622 and 10663 | P3-23 | confirmed by review as a reachable path, not a missing guard; raised as U-05. Replay is separately affected: its translation drops a row for a command it considers ended (`outcome_translator.py` 156-164), returning nothing, so that row contributes no piece to the plan and no later start finds it owed. This does not establish non-delivery live, where the composed callback still passes the original outcome on after translation returns empty (`launcher.py` 3001-3003) |
| H-051 | The outcome row and its replay builder lose slice progress, though the spine keeps it elsewhere. `TradeOutcomeProduced` carries no slice counts, so an outcome rebuilt from it substitutes one of one — while `SchemeStateChanged` does persist the cursor and a resumed scheme restores it, so the progress itself survives. No misreport follows the placeholder: every translated piece is built without slice counts, so it goes no further than the rebuilt object. Separately the live count is of slices **sent**, not finished. On the ordinary path the cursor advances once a slice goes out while its order may still be resting, so a slice sent and unfilled still counts. Ladder replacement does not accumulate: it places the new rungs without advancing, then sets cursor and total to the replacement plan's length, so a replacement stopping part way leaves the previous cursor standing. | row built without them at `execution_manager.py` 10817-10829; placeholder at `launcher.py` 1688-1689; pieces built without them at `outcome_translator.py` 265-270, 289-301, 314-325, 331-340 and 354-366; cursor persisted at `execution_manager.py` 6311-6322 and restored at 1970-1979; advanced past a still-active child at 5920-5923 and copied at 6515-6516; ladder replacement resetting both at 9315-9317 past the loop at 9301-9313 | P2-43 | recorded; P2-43 states the reporting limits |
| H-052 | The replay venue's order book carries a price but no amount on either side, so the likely-price working-out can price nothing against it. A replay run with a maximum deviation configured therefore refuses every **plain single** market order, since the guard rejects one whose estimate is absent. A market slice of work fed out over time submits directly and never reaches that guard, so it trades as normal — confirmed by review, which reproduced a scheduled VWAP fill of 0.5 BTC at 50,000 against the real replay adapter with a maximum of 1. Calling the estimator with a zero-amount book reports depth insufficient and returns nothing. | `replay_venue_adapter.py` 415-417; refused at `execution_manager.py` 4064-4079 reached at 4230, with the estimate attempted at 4194-4197; bypassed at 5979 | P3-03 | recorded; P3-03 states both halves |
| H-053 | `_consume_lots` takes from the lots and removes emptied ones before testing whether the sell exceeded them. On that failure the `ValueError` is raised with the lots already consumed and nothing restored, so an immediate retry of the same sell finds no lots left and fails again. The caller's failure is caught and logged by `_project_to_ledger`, so trading continues with the ledger's lots reduced by a sell that was refused. | confirmed by review, reproducing a buy of 1 then a sell of 2 under both ways of costing: the lots end empty while balances, journal and profit are unchanged. Taken at `account_ledger.py` 364-373 before the test at 375-377; the failure swallowed at `execution_manager.py` 2092-2098 | P3-12 | recorded; P3-12 states the ordering |
| H-041 | Changing the weight curve of a Scheduled VWAP order is not supported. | 10070-10071 | schedule change | folds into the schedule change |

---

Created 2026-09-16 09:39 UTC · Last modified 2026-09-30 16:47 UTC
