---
row: P4-20
baseline: 49aa659
created: 2026-10-01 10:18 UTC
modified: 2026-10-11 20:42 UTC
evidence:
  - claim: "A key that can withdraw, or cannot trade spot, raises"
    source: "`launcher.py` 3101-3112"
  - claim: "That raise is caught, trading stopped, and the failure carried out"
    source: "`launcher.py` 3117-3120, out through 3069-3074 and 5003-5008"
  - claim: "No account has a thread by then"
    source: "`launcher.py` 2829 ahead of 2830"
  - claim: "Where the whole check runs out of time instead, the waiting is abandoned with no stop, and the start is given up all the same"
    source: "`launcher.py` 3075-3079"
  - claim: "A port that cannot be taken carries the failure out of the start"
    source: "`launcher.py` 3303-3305 through 3270-3274, escaping 2831 before 2840"
  - claim: "Trading raising while it starts does the same, having first undone what it part-started"
    source: "`trading.py` 511-528, escaping `launcher.py` 3043 before 2840"
  - claim: "Trading merely taking too long carries the failure out with nothing undone, the wait not even cancelled"
    source: "`launcher.py` 3043 with nothing catching it, out through 2828 before 2840, ending at 5004-5008, against the wait that is cancelled at 3075-3079"
  - claim: "An account's thread catches everything from building to shutting down, and sets the stop flag"
    source: "`launcher.py` 4034-4040 over the span opened at 3991"
  - claim: "That flag is what every other account is waiting on"
    source: "`launcher.py` 3999"
  - claim: "An account still building reaches that wait only after it has finished building"
    source: "`launcher.py` 3992-3995 ahead of 3999"
  - claim: "A failure in a sampler or a poller is logged and trading carries on"
    source: "`launcher.py` 3704-3710 and 3804-3808"
  - claim: "A sampler build that fails stops the samplers it had already started, until one of those stops fails in its turn"
    source: "`launcher.py` 3747-3751"
---
# What a failure at startup does

A **failure at startup** is caught differently at each step of [starting a host](starting-a-host.md).

## The key check

A key that can withdraw, or cannot trade spot, raises. The raise is caught, trading is stopped, and the failure carries out of the host. No [account](what-an-account-is.md) has a thread by then.

Where instead the whole check runs out of time, the waiting is abandoned and trading is left running. The start is given up all the same.

## An account

An account's thread catches everything from building its account, through running it, to shutting it down, and sets the stop flag.

That flag is what every other account is waiting on, so one failing asks the rest to come down. Asks, not makes: an account still building reaches the wait only once it has finished building.

## Trading, and the endpoint

Trading raising while it starts, and a port that cannot be taken, both carry the failure out past the point where the host would shut itself down. Trading undoes what it part-started first; the endpoint undoes nothing, leaving trading running and the loop thread alive as the process unwinds.

Trading merely taking too long is a third case, and the bleakest: nothing catches the wait running out, so the failure carries out as before, but trading undoes nothing — the wait is not even cancelled, so what it was waiting on can still be taken up as the process unwinds.

## A sampler or a poller

Here a failure is logged and trading carries on. A sampler build that fails first stops whichever samplers it had already started.

## Related

- [Starting a host](starting-a-host.md)
- [What a starting host reports](what-a-starting-host-reports.md)
