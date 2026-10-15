---
row: S-05
baseline: 49aa659
created: 2026-10-15 08:55 UTC
modified: 2026-10-15 10:30 UTC
evidence:
  - claim: "The record's marks are walked before any of it is replayed"
    source: "`trading.py` 513 before 515"
  - claim: "Only the started run's events are read, and they are sorted by account"
    source: "`trading.py` 515 and 517-519"
  - claim: "One account is registered and started to the end before the next is begun"
    source: "`trading.py` 521-524"
  - claim: "Orphan commands are answered straight after replay, before the venue is asked anything"
    source: "`execution_manager.py` 2254-2258 reached from `trading.py` 550, before 567"
  - claim: "The orphan venue sweep is what decides the account may trade"
    source: "`trading.py` 567 into 606-608"
  - claim: "The feed is opened after that sweep"
    source: "`trading.py` 567 before 588"
  - claim: "Against a live venue the backfill and squaring run together, and another venue reaches the squaring alone"
    source: "`trading.py` 590-591 against 594-595"
  - claim: "What the squaring queued is drained before an unfinished close is picked up"
    source: "`trading.py` 598 before 600"
  - claim: "The account may trade where the sweep succeeded and nothing poisoned it"
    source: "`trading.py` 604 and 606-608"
  - claim: "A start that raises cleans up the accounts already started"
    source: "`trading.py` 526-527"
---
# Starting a host back up

The route one account takes inside a starting host, from the record on disk to the moment it is let trade or refused. Each step hands off to the article that owns it.

**Starts from** a process whose settings are read, starting the trading it runs.

**Ends** with the account let trade, or logged as not ready and its feed closed.

## Once for the whole record

1. Starting trading is the second of the things a host starts, and the steps below all happen inside it — [Starting a host](../atoms/starting-a-host.md).

2. The record's own marks are walked before any of it is replayed, and a record whose marks do not hold is refused — [What the chain proves](../atoms/what-the-chain-proves.md). What that walk cannot notice is its own subject — [What the chain misses](../atoms/what-the-chain-misses.md).

3. Only the events of the run being started are read back, each run's being kept apart in the record — [The event spine](../atoms/the-event-spine.md).

## Then one account at a time

4. An account is marked as starting, which is what makes its worker do nothing while this runs, and its whole start is finished before the next account is begun — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

5. Its events are replayed, rebuilding the live work at the point it had reached — [What a restart puts back](../atoms/what-a-restart-puts-back.md). A bracket comes back by what its pair was doing, and only one with nothing recorded, or still going out, is placed — [What a restart puts back of a bracket](../atoms/what-a-restart-puts-back-of-a-bracket.md).

6. Work the record cannot account for is answered straight after that replay, so a caller waiting on it hears something — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md).

7. Orders the venue still shows and the record has never heard of are swept next, and whether that sweep succeeded is what decides this account may trade — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md).

8. Against a live venue the feed is opened after that sweep, so anything the sweep cancelled is gone before the feed could deliver news of it — [The venue feed](../atoms/the-venue-feed.md).

9. On that same live path, trades missed while the account was down are fetched a page at a time — [Backfilling missed trades](../atoms/backfilling-missed-trades.md). Against a simulated venue there is no feed and no such fetch, and the squaring below is reached directly — [Binsim](../atoms/binsim.md).

10. Each order the record still holds as working is then squared against the venue, fills taken in before any ending is concluded — [How an order is brought back into step](../atoms/how-an-order-is-brought-back-into-step.md).

11. What that squaring queued is drained — [How waiting work is drained](../atoms/how-waiting-work-is-drained.md) — and only then is a close left unfinished picked up — [How an unfinished close is recovered](../atoms/how-an-unfinished-close-is-recovered.md).

## Let trade, or not

12. The account may trade where its sweep succeeded and nothing poisoned it — [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md). Only then do the ways in accept anything for it — [What the host refuses first](../atoms/what-the-host-refuses-first.md).

13. A sweep that failed, and an account poisoned on the way through, are each logged and leave it refused — [What a failure at startup does](../atoms/what-a-failure-at-startup-does.md), [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

14. A squaring that failed or came back incomplete is a separate matter: it leaves the hold on without stopping the account being let trade, and only a feed reconnection asks again — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

15. What a watcher is told meanwhile says less than it looks — [What a starting host reports](../atoms/what-a-starting-host-reports.md).

## Where this route is not taken

- A start that raises cleans up the accounts already started and goes no further — [What a failure at startup does](../atoms/what-a-failure-at-startup-does.md).
- Money that moved in or out is not fetched here: the start only marks where to look from, and the squaring tick fetches it later — [The window a movement is found in](../atoms/the-window-a-movement-is-found-in.md).
- A report that never crossed back is replayed by its own path — [How an undelivered outcome is replayed](../atoms/how-an-undelivered-outcome-is-replayed.md).

---

Created 2026-10-15 08:55 UTC · Last modified 2026-10-15 10:30 UTC
