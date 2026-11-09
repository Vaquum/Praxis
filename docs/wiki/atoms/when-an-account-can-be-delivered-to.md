---
row: P125-02
baseline: 49aa659
created: 2026-11-15 07:00 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "One thread is made per account, each a daemon named after its account, kept in a list and started at once"
    source: "`launcher.py` 3892, then 3895-3900, then 3901, then 3902"
  - claim: "Starting the threads refuses where the trading stack or the loop is missing, where a thread finding the same thing answers at once instead"
    source: "`launcher.py` 3888 into 3889-3890, against 3988 into 3989"
  - claim: "The account's runtime is published under a lock of its own once its build has answered"
    source: "`launcher.py` 3993 into 3994"
  - claim: "Delivering to an account reads that runtime under the same lock and refuses where none stands"
    source: "`launcher.py` 3969, then 3970, then 3972 into 3973-3977, or 3979"
  - claim: "Three roads deliver that way"
    source: "`launcher.py` 3008, and 3019, and 3030"
  - claim: "An ordinary stop unpublishes the runtime before any of the account's loops is stopped"
    source: "`launcher.py` 4001 into 4002, ahead of 4004-4007"
  - claim: "A failure unpublishes it after the failure is reported, and then sets the host's own stop"
    source: "`launcher.py` 4037-4038, then 4040"
---
# When an account can be delivered to

An account can be delivered to only while its runtime is published, and the publishing happens once its own thread has finished building it.

## The thread

One per account, each a daemon named after its account, kept in a list and started at once.

Starting them refuses where the trading stack or the loop is missing. A thread that finds the same thing answers at once instead, with no word — so the condition that stops the host when the starter meets it leaves one silent thread when the thread does.

## The publishing

Once the build has answered, the runtime goes into a mapping under a lock of its own. Delivering reads it back under that same lock and refuses where none stands.

Three roads deliver that way. A refusal from any of them means the account is still building, and what the refusal reaches holds the thing undelivered rather than dropping it.

## The unpublishing

An ordinary stop unpublishes the runtime before any of the account's loops is stopped. So between that line and the loops going quiet, the account's own loops are still running while nothing can be delivered to them.

A failure unpublishes it after the failure is reported, and then sets the host's own stop. So one account failing takes the whole host down, and the account is unreachable from the moment the failure is logged.

## Related

- [Starting a host](starting-a-host.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)
- [Stopping a host](stopping-a-host.md)
