---
row: P127-01
baseline: 49aa659
created: 2026-11-15 08:00 UTC
modified: 2026-11-15 08:00 UTC
evidence:
  - claim: "Four roads out of the trading side are set as it is started"
    source: "`launcher.py` 2997, or 3005, then 3038, then 3039, then 3040"
  - claim: "Money moving, a disagreement found and a protection to put right each resolve the account's runtime first, and refuse where none stands"
    source: "`launcher.py` 3008-3009, and 3019-3020, and 3030-3031, into 3969, then 3972 into 3973-3977"
  - claim: "The road an outcome takes resolves no runtime, reading the account's queue and its wiring instead"
    source: "`launcher.py` 2974, then 2985-2986"
  - claim: "Where the settings carry a caller's own road, the host's routing runs first and the caller's is awaited after"
    source: "`launcher.py` 2996 into 2997, or 3001-3002, then 3003"
  - claim: "The trading side is started only after all four are set, and waited on for thirty seconds"
    source: "`launcher.py` 3042, then 3043, past 3038-3040"
  - claim: "Starting it refuses outright where the host's loop has not been started"
    source: "`launcher.py` 2946 into 2947-2948"
---
# Which roads out wait for an account to be ready

The trading side reports back along four roads, all set as it starts, and three of the four will not deliver to an account that is still being built.

## The three that wait

Money moving, a disagreement found, and a protection to put right. Each [resolves the account's runtime](when-an-account-can-be-delivered-to.md) before it does anything, and refuses where none stands — so each is held and offered again rather than lost.

## The one that does not

The road an outcome takes resolves no runtime at all. It reads the account's queue, and reads [the account's wiring](the-two-mappings-an-account-lives-in.md), and works from those.

The wiring is written from inside an account's build and the runtime only after it, so this is the one road that can act on an account the other three would refuse. That is what the two mappings are for: an outcome has figures to move whether or not anything can be asked of the account yet.

## The caller's own road

Where the settings carry one, the host's routing runs first and the caller's is awaited after. So a caller's road cannot stop the host's, and cannot run before it.

## When the side itself starts

Only after all four roads are set, and then waited on for thirty seconds. Starting it at all refuses outright where the host's loop has not been started.

## Related

- [When an account can be delivered to](when-an-account-can-be-delivered-to.md)
- [The two mappings an account lives in](the-two-mappings-an-account-lives-in.md)
- [The road an arriving report takes](the-road-an-arriving-report-takes.md)
