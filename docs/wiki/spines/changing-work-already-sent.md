---
row: S-03
baseline: 49aa659
created: 2026-10-15 08:20 UTC
modified: 2026-10-15 20:40 UTC
evidence:
  - claim: "The host's own refusals run before the manager is reached"
    source: "`trading.py` 1913-1916 before `execution_manager.py` 3048"
  - claim: "Every admitted change is queued, none going to the venue from here"
    source: "`execution_manager.py` 3060-3072 into 3074"
  - claim: "A protective pair's change is the first arm inside the pass, before the ended-command check"
    source: "`execution_manager.py` 8616-8620 before 8622-8624"
  - claim: "An unknown command and an unsettled previous change are refused past that arm"
    source: "`execution_manager.py` 8627-8629 and 8631-8636"
  - claim: "A run and a ladder take their own arms, and return from them"
    source: "`execution_manager.py` 8639-8646 into 8653"
  - claim: "What is left is a single order or a part-shown one, anything else refused"
    source: "`execution_manager.py` 8655-8661"
  - claim: "The stop-price, weighted-field and buy-exposure refusals all run before the change is queued"
    source: "`validate_trade_modify.py` 200-208, 210-218 and 220-226, reached from `execution_manager.py` 3060 before 3074"
  - claim: "A command ended with protection of its own left to amend is carried past the ended-command check"
    source: "`validate_trade_modify.py` 171-175"
  - claim: "An order the record has as anything but resting at a price is refused on the worker"
    source: "`execution_manager.py` 8680-8684"
  - claim: "A part-shown order's change may name only the amount to show, keeping its price"
    source: "`execution_manager.py` 10213-10225"
---
# Changing work already sent

The route a change takes from the caller to the venue, and the arm it leaves by for each way of working. Each sentence hands off to the article owning the behaviour it names, and the order they happen in is proved below rather than borrowed.

**Starts from** a caller asking Praxis to alter work it has already submitted.

**Ends** with the work altered, with the change refused on the call, with it logged and returned where the caller hears nothing, or with it set aside for a later pass.

## Before the worker sees it

1. The settings a change carries are built before any of this, and must name the command, the account and a reason — one with nothing set at all cannot be made — [The change each way of working accepts](../atoms/the-change-each-way-of-working-accepts.md).

2. The host refuses a change while it is shutting down, before it has been started, and while the named account is not ready — [What the host refuses first](../atoms/what-the-host-refuses-first.md).

3. The checks that turn a change away happen here, before it is queued, not on the worker: a command already ended with no protection of its own left to amend is answered as a no-op — [The change each way of working accepts](../atoms/the-change-each-way-of-working-accepts.md). A change to a single order naming either of its stop prices is refused, whichever side it is — [The change each way of working accepts](../atoms/the-change-each-way-of-working-accepts.md). So is one asking to alter a weighted run's weights — [The change each way of working accepts](../atoms/the-change-each-way-of-working-accepts.md). So is one raising what a buy commits, the caller told to place a new order instead — [The change each way of working accepts](../atoms/the-change-each-way-of-working-accepts.md).

4. Everything admitted joins [the priority line](../atoms/the-priority-line.md) — every kind, with none going to the venue from here — [Changing work already sent](../atoms/changing-work-already-sent.md).

5. [The worker's next pass](draining-an-accounts-queues.md) takes that line — [How waiting work is drained](../atoms/how-waiting-work-is-drained.md).

6. A change reaching it while the account is catching up with the venue is put back rather than carried out, and tried again on a later pass — [A change waiting out a hold](../atoms/a-change-waiting-out-a-hold.md).

## One arm per way of working

7. **Arm one — a protective pair.** A change naming one is dispatched before any other check here — [Changing work already sent](../atoms/changing-work-already-sent.md) — and takes its own route from there — [How protection's prices are changed](../atoms/how-protections-prices-are-changed.md).

8. Past that arm a command that ended while it waited is answered as a no-op, this being the second such check and the one that catches it — [Changing work already sent](../atoms/changing-work-already-sent.md).

9. A command the record has no entry for takes nothing, and so does one whose previous change is still settling, which keeps two from being in flight at once — [Changing work already sent](../atoms/changing-work-already-sent.md).

10. **Arm two — work fed out over time.** The count of parts and the gap are altered, and only a new count plans the remaining amounts again — [How a schedule change is carried out](../atoms/how-a-schedule-change-is-carried-out.md).

11. **Arm three — a ladder.** The whole grid is replaced: the old rungs come down and are confirmed over before any new rung goes up — [How a ladder's prices are changed](../atoms/how-a-ladders-prices-are-changed.md). What can leave that grid short is its own matter — [What stops a ladder's new rungs](../atoms/what-stops-a-ladders-new-rungs.md).

12. **Arm four — a single order or a part-shown one.** A change naming neither of those two kinds of settings is refused here — [Changing work already sent](../atoms/changing-work-already-sent.md).

13. An order the record has as anything but resting at a named price is refused — [Changing work already sent](../atoms/changing-work-already-sent.md). A part-shown order's change may name only the amount to show, keeping the price it had — [What each change insists on](../atoms/what-each-change-insists-on.md).

14. Otherwise the order is replaced: cancelled, settled, and a fresh one placed for what is left — [How a price change is carried out](../atoms/how-a-price-change-is-carried-out.md). Where the figures cannot be settled, the change is parked and the original left unfinished — [How a price change is carried out](../atoms/how-a-price-change-is-carried-out.md). Where the cancel itself is unconfirmed, nothing is placed and the order is left live — [When a price change places nothing](../atoms/when-a-price-change-places-nothing.md).

## Where this route is not taken

- Giving up on work entirely asks for an abandonment, which takes its own route — [Abandoning work outright](../atoms/abandoning-work-outright.md).
- A protective pair put up again after a loss arrives by the placing road — [When protection is put up again](../atoms/when-protection-is-put-up-again.md).

---

Created 2026-10-15 08:20 UTC · Last modified 2026-10-15 20:40 UTC
