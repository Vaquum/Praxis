---
row: P107-01
baseline: 49aa659
created: 2026-11-09 08:20 UTC
modified: 2026-11-09 08:20 UTC
evidence:
  - claim: "Both submitting roads refuse while a stop is under way, each with wording of its own"
    source: "`praxis/trading.py` 1878 into 1879-1880, and 1904 into 1905-1906"
  - claim: "That refusal stands ahead of the demand that the account be ready"
    source: "`praxis/trading.py` 1878, ahead of 1881, and 1904, ahead of 1907"
  - claim: "Each then hands the asking to the inbound side, one awaiting it and one not"
    source: "`praxis/trading.py` 1882-1884, against 1908"
  - claim: "Both ways of asking for the health figures demand a started facade and hand the asking to the venue"
    source: "`praxis/trading.py` 1958, then 1959, and 1982, then 1983"
  - claim: "The two differ in nothing but one being awaitable, both reading the same figures from the same venue"
    source: "`praxis/trading.py` 1959, and 1983"
---
# What a submitting road refuses first

Both ways of sending something to the venue refuse the same two things, and the order they refuse in decides what a caller is told.

## The stop comes first

Both roads refuse while a stop is under way, each with wording of its own. That refusal stands ahead of the demand that the account be ready.

So a caller submitting into a stopping facade is told the facade is shutting down, rather than that its account is not ready — even where the account is not ready either. The first answer is the true one and the more useful.

## Then the account

Each demands the account be ready, and then hands the asking to the inbound side. One awaits that handing and one does not, so one road reports a failure from inbound to its caller and the other cannot.

## The health figures, asked two ways

Both ways demand a started facade and hand the asking to the venue. They differ in nothing but one being awaitable: the same figures, from the same venue, by the same call.

The awaitable one exists for a caller that must dispatch onto the facade's loop from another thread. The plain one exists because the work needs no loop at all, and scheduling it on a busy loop to read figures already in memory would be waste.

## Related

- [What a stop will not leave running](what-a-stop-will-not-leave-running.md)
