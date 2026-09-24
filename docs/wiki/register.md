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
| P2-11 | What a venue is, and what Praxis asks of one | seeded | — |
| P2-12 | What an account is | seeded | — |
| P2-13 | The order book, and what a venue publishes in it | seeded | — |
| P2-14 | Order types, and what a market order means here | seeded | — |
| P2-15 | What a fill is | seeded | — |
| P2-16 | Holdings, and how a fill changes them | seeded | — |
| P2-17 | The event spine, and what writing down means | seeded | — |
| P2-18 | Outcomes, and what partial reports | seeded | — |
| P2-19 | Runs, and the slices they are fed out in | seeded | — |
| P2-20 | Ladders, and their rungs | seeded | — |
| P2-21 | Protection, and the order that carries it | seeded | — |
| P2-22 | Hidden-size orders, and what the venue shows | seeded | — |
| P2-23 | Deadlines, and the two clocks they run on | seeded | — |

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
| H-043 | A plain single order still pending or partly filled once its acceptance deadline has passed is cancelled at the venue and reported expired. A not-found cancel still counts as expired; a failed one carries the failure in the reason. None of the ten bodies says this happens. | `execution_manager.py` 4411-4436 | P2-23 | folds into P2-23; needs a pass back through P1-02 |
| H-044 | A run or a ladder that has started is judged against a new window opened at its start, not against the clock its command was accepted on. | `execution_manager.py` 5784-5787 and 6128-6131, against 2925 | P2-23 | folds into P2-23 |
| H-042 | A ladder cancelled before its first rung, reaching `_start_ladder` before its deadline, passes a zero slice total into the terminal emitter. `TradeOutcome` refuses it, the `ValueError` is caught and logged, and no outcome is produced at the time. The command survives as an accepted command with no intent, so the next start classes it a boot orphan and dispatches a REJECTED outcome. The caller is told, but only after a restart, and as a rejection rather than a cancellation. | `execution_manager.py` 6077-6081 into 8411-8423, refused by `trade_outcome.py` 146-148, swallowed at 4012-4019; recovered at 2254-2275 into 2297-2330 | P1-04 | U-03 corrected: a deferred, mislabelled report, not a lost one |
| H-041 | Changing the weight curve of a Scheduled VWAP order is not supported. | 10070-10071 | schedule change | folds into the schedule change |

---

Created 2026-09-16 09:39 UTC · Last modified 2026-09-24 20:11 UTC
