---
row: N7-02
baseline: 49aa659
created: 2026-10-27 09:10 UTC
modified: 2026-10-27 15:00 UTC
evidence:
  - claim: "After the saving, the host asks the store for a checkpoint"
    source: "`nexus/startup/shutdown_sequencer.py` 893, reached at 193 after 190-191"
  - claim: "The locks that checkpoint needs are taken inside the store, where the launcher has given it a pair to take"
    source: "`nexus/infrastructure/state_store.py` 178 into 219-221, the pair given at `praxis/launcher.py` 4141"
  - claim: "The stopping wraps nothing around that call but a catch, so it holds neither lock when the store asks for them"
    source: "`nexus/startup/shutdown_sequencer.py` 192-195"
  - claim: "Both locks are of the kind that a second ask on the same thread waits on for ever"
    source: "`praxis/launcher.py` 4102 and `nexus/core/capital_controller/capital_controller.py` 107"
  - claim: "A failure there is logged and the host goes on to the last stage"
    source: "`nexus/startup/shutdown_sequencer.py` 192-195 before 196"
  - claim: "The account is given back last of all"
    source: "`nexus/startup/shutdown_sequencer.py` 196 after 193"
  - claim: "Giving it back is passed over with a line where the connection out or the account's name is absent"
    source: "`nexus/startup/shutdown_sequencer.py` 898-900"
  - claim: "A raise while giving it back is logged and the stopping ends anyway"
    source: "`nexus/startup/shutdown_sequencer.py` 902-905"
  - claim: "The giving back takes the account's stream off the host and closes it before it reaches the register at all"
    source: "`praxis/trading.py` 1844-1847 before 1851 into `praxis/core/execution_manager.py` 2952"
  - claim: "A wait that runs out cancels that work wherever it has got to, and the catch around the closing lets that cancelling through"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 370-375 against the catch at `praxis/trading.py` 1848"
  - claim: "Where that cancelling leaves the account turns on where it lands: the closing swallows one that arrives at its own waiting, and the taking out comes before the waiting after it"
    source: "`praxis/infrastructure/binance_ws.py` 273-277 under the stream installed at `praxis/trading.py` 581-589, and `praxis/core/execution_manager.py` 2952 before 2966-2969"
---
# The last record a stopping host writes

The last two things [a stopping host](what-a-stopping-host-halts-first.md) does are [ask its store for a checkpoint](what-a-checkpoint-holds.md) and give the account back, in that order, each wrapped so a failure in it is written down and passed over.

## Who takes the locks

The locks that checkpoint needs are taken inside the store, which the launcher has given a pair to take. The stopping wraps nothing around the call but a catch, so it holds neither lock when the store asks for them — both are of the kind a second ask on the same thread waits on for ever, so wrapping the call would take them first and leave the store waiting on itself.

## Why it is wrapped at all

A failure to write that checkpoint is logged and the host goes on to the last stage, so a host can finish having written no checkpoint of its own.

## Giving the account back

[The account](what-an-account-is.md) is given back last of all, and that is passed over with a line where the connection out or the account's name is absent.

A raise there is logged and the stopping ends anyway. The giving back takes that account's stream off the host and closes it before reaching the register, and a wait that runs out cancels the work wherever it has got to. Where that leaves the account turns on where the cancelling lands. The closing swallows one that arrives at its own waiting and finishes, so the register is reached after all. One that escapes the closing stops short of the register, with the stream already gone. One arriving later finds the account already taken out. The timeout alone does not say which.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [What a stopping host saves of its strategies](what-a-stopping-host-saves-of-its-strategies.md)

---

Created 2026-10-27 09:10 UTC · Last modified 2026-10-27 15:00 UTC
