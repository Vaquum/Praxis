---
row: P181-02
baseline: 49aa659
created: 2026-11-09 13:14 UTC
modified: 2026-11-09 13:14 UTC
evidence:
  - claim: "Six things are handed over: the account's name, its three queues, its trading record and its money record"
    source: "`execution_manager.py` 577, then 578, then 579, then 580, then 587, then 588"
  - claim: "Two further queues are made fresh, one for work to be reacted to and one for events waiting to be taken in"
    source: "`execution_manager.py` 581, then 582-584"
  - claim: "A count of events in flight starts at nothing, and a wake-up starts unset"
    source: "`execution_manager.py` 585, then 586"
  - claim: "Four marks about where the account stands all start false: reconciling, booting, a failed boot, and poisoned"
    source: "`execution_manager.py` 596, and 597, and 598, and 601"
  - claim: "A count of places reserved in the command queue starts at nothing"
    source: "`execution_manager.py` 595"
  - claim: "A request for a protection scan starts unmade"
    source: "`execution_manager.py` 602"
  - claim: "The live work, the live trades, the amend counts and the amends still owing all start empty"
    source: "`execution_manager.py` 591, and 592, and 593, and 594"
---
# What an account's runtime is built holding

Each registered account gets one of these, and what it is built with divides cleanly: six things handed over, and everything else starting empty or false.

## Handed over

The account's name, its three queues — for commands, for the things that jump the line, and for news from outside — its trading record and its money record.

## Made fresh

Two further queues: one for work to be reacted to, and one for events waiting to be taken in. Neither is handed over, so no two accounts can share them.

## Starting empty

The live work, the live trades, the counts of changes made, and the changes still owing.

## Starting at nothing or false

A count of events in flight, and a count of places reserved in the command queue. A wake-up, unset. A request for a protection scan, unmade.

And four marks about where the account stands, all false at the start: reconciling, booting, a failed boot, and [poisoned](what-poisons-an-account.md).

## Related

- [What an account is](what-an-account-is.md)
- [What poisons an account](what-poisons-an-account.md)
- [What a queue reservation is for](what-a-queue-reservation-is-for.md)
