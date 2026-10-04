---
row: P4-21
baseline: 49aa659
created: 2026-10-01 10:34 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "The log line's count of accounts is a count of threads"
    source: "`launcher.py` 3901, counted at 2835"
  - claim: "The endpoint asks four things: the stop flag, trading, the loop thread, and each account's thread"
    source: "`launcher.py` 3865-3878, refused at 3880-3884"
  - claim: "An account's thread is started before its account is built"
    source: "`launcher.py` 3902 ahead of 3992-3995"
---
# What a starting host reports

A [host](starting-a-host.md) says two things about itself while it starts: a count in its log, and an answer at the endpoint a watcher polls. Both are about threads.

## The count

The accounts are started by starting threads, and a thread is started before the account it will go on to build. What the count reports is how many were started, not how many are running.

## The answer

The endpoint asks four things: whether the stop flag is set, whether trading is up, whether the loop thread is alive, and whether each account's thread is alive. None of them asks whether an account finished building, so a host whose accounts are all still building, with the flag clear, answers that it is well.

## Related

- [Starting a host](starting-a-host.md)
- [Health](health.md)
