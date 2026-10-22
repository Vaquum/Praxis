---
row: S-05
baseline: 49aa659
created: 2026-10-15 08:55 UTC
modified: 2026-10-16 09:40 UTC
evidence:
  - claim: "The record's marks are walked before any of it is replayed"
    source: "`trading.py` 513 before 515"
  - claim: "Only the started run's events are read, and they are grouped by account"
    source: "`trading.py` 515 and 517-519"
  - claim: "One account is registered and started to the end before the next is begun"
    source: "`trading.py` 521-524"
  - claim: "Orphan commands are answered straight after replay, before the orphan venue sweep"
    source: "`trading.py` 548 before 550-552, before 567"
  - claim: "Answering one is a report sent on the account's behalf, not only a classification"
    source: "`execution_manager.py` 2270-2271 and 2277-2281 into 2330"
  - claim: "The orphan venue sweep is what the readiness flag is taken from"
    source: "`trading.py` 567 into 606"
  - claim: "The feed is opened after that sweep"
    source: "`trading.py` 567 before 588"
  - claim: "The branch is the adapter's kind, and on it the backfill is waited on before the squaring"
    source: "`trading.py` 569 into 590-591, the backfill before the squaring at 1459-1464"
  - claim: "Any other adapter reaches the squaring with no feed opened"
    source: "`trading.py` 594-595"
  - claim: "What the squaring queued is drained before an unfinished close is picked up"
    source: "`trading.py` 598 before 600"
  - claim: "The account may trade where the sweep succeeded and nothing poisoned it"
    source: "`trading.py` 604 and 606-608"
  - claim: "A start that raises cleans up the accounts already started"
    source: "`trading.py` 526-527"
---
# Starting a host back up

The route one account takes inside a starting host, from the record on disk to the moment it is let trade or refused. Each sentence hands off to the article owning the behaviour it names, and the order they happen in is proved below rather than borrowed.

**Starts from** a process whose settings are read, starting the trading it runs.

**Ends** with the account let trade, or logged as not ready and its feed closed.

## Once for the whole record

1. Starting trading is the second of the things a host starts, and the steps below all happen inside it — [Starting a host](../atoms/starting-a-host.md).

2. The record's own marks are walked before any of it is replayed, and a record whose marks do not hold is refused — [What the chain proves](../atoms/what-the-chain-proves.md). What that walk cannot notice is its own subject — [What the chain misses](../atoms/what-the-chain-misses.md).

3. Only the events of the run being started are read back, and they are grouped by account — [The event spine](../atoms/the-event-spine.md).

## Then one account at a time

4. An account is marked as starting, which is what makes its worker do nothing while this runs — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md). Its whole start then finishes before the next account is begun, which the evidence below is what proves — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

5. Its events are replayed, rebuilding the live work at the point it had reached — [What a restart puts back](../atoms/what-a-restart-puts-back.md). A bracket comes back by what its pair was doing, and only one with nothing recorded, or still going out, is placed — [What a restart puts back of a bracket](../atoms/what-a-restart-puts-back-of-a-bracket.md).

6. Work the record cannot account for is answered straight after that replay, so a caller waiting on it hears something — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md).

7. Orders the venue still shows and the record has never heard of are swept next — though only those whose names carry a command this account owns are cancelled, the rest being left alone — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md).

8. Where the venue is reached through the Binance adapter — which the simulated venue is too — the feed is opened after that sweep — [The venue feed](../atoms/the-venue-feed.md).

9. On that same branch — and only it, any other adapter reaching the squaring below with no feed opened and no such fetch — trades missed while the account was down are fetched a page at a time, waited on before that squaring — [Backfilling missed trades](../atoms/backfilling-missed-trades.md).

10. Each order the record still holds as working is then squared against the venue, fills taken in before any ending is concluded — [How an order is brought back into step](../atoms/how-an-order-is-brought-back-into-step.md).

11. What that squaring queued is drained, and only then is a close left unfinished picked up — [How an unfinished close is recovered](../atoms/how-an-unfinished-close-is-recovered.md).

## Let trade, or not

12. The account may trade where its sweep succeeded and nothing poisoned it — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md). Only then do the ways in accept anything for it — [What the host refuses first](../atoms/what-the-host-refuses-first.md).

13. A sweep that failed leaves it refused — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md) — and so does an account poisoned on the way through — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

14. On that same adapter branch, a backfill coming back incomplete leaves the hold on without stopping the account being let trade, and only a feed reconnection asks again — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

15. What a watcher is told meanwhile says less than it looks — [What a starting host reports](../atoms/what-a-starting-host-reports.md).

## Where this route is not taken

- A start that raises cleans up the accounts already started and goes no further — [What a failure at startup does](../atoms/what-a-failure-at-startup-does.md).
- Money that moved in or out is not fetched here: the start only marks where to look from, and the squaring tick fetches it later — [The window a movement is found in](../atoms/the-window-a-movement-is-found-in.md).
- A report that never crossed back is replayed by its own path — [How an undelivered outcome is replayed](../atoms/how-an-undelivered-outcome-is-replayed.md).

---

Created 2026-10-15 08:55 UTC · Last modified 2026-10-16 09:40 UTC
