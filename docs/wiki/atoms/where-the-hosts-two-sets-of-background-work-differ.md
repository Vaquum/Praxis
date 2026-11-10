---
row: P124-02
baseline: 49aa659
created: 2026-11-09 09:46 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "The samplers are built one per account, and the book pollers one per distinct symbol across those same accounts"
    source: "`launcher.py` 3731, against 3819, then 3822"
  - claim: "A sampler's cadence is read from the environment on every build, where a poller's is a figure standing in the module"
    source: "`launcher.py` 3722, against 3827, the figure at 197"
  - claim: "A sampler writes what it finds to the host's record under the epoch, where a poller writes into a cache the host keeps"
    source: "`launcher.py` 3725-3726, against 3826"
  - claim: "A poller's asking is bound to one symbol and asks a fixed depth"
    source: "`launcher.py` 3825 into 638-639, the depth at 198"
  - claim: "Starting the samplers stops where the record is missing, and starting the pollers where the venue is missing"
    source: "`launcher.py` 3699, against 3799"
  - claim: "Both builds are handed to the Praxis loop and waited on for ten seconds"
    source: "`launcher.py` 3702, then 3705, and 3802, then 3805"
  - claim: "Each build takes what it needs off the host and does nothing where it is missing or where a set already stands"
    source: "`launcher.py` 3715, then 3717 into 3718, and 3813, then 3815 into 3816"
  - claim: "Each records its set only once every one of them is built"
    source: "`launcher.py` 3753, and 3838"
  - claim: "Each stop reads its set off the host before handing a stop of every one to the loop"
    source: "`launcher.py` 3843 into 3844, or 3846, then 3852, and 3761, then 3767"
  - claim: "Both stop everything already started when a build fails"
    source: "`launcher.py` 3748-3751, and 3833-3836"
  - claim: "Both keep their list where a stop fails"
    source: "`launcher.py` 3772, and 3857"
---
# Where the host's two sets of background work differ

The host runs two sets of work beside its trading — samplers writing down what positions are worth, and [pollers keeping the book](the-kept-book.md) — and the two are built from one pattern with four departures from it.

## What they share

Each build takes what it needs off the host, does nothing where that is missing or where a set already stands, and records its set only once every one is built. Each build is handed to the Praxis loop and waited on for ten seconds. Each stops everything it had already started when the build fails. Each stop reads its set off the host first, and keeps that set where the stop fails, clearing it only where the stop answered.

## How many of each

One sampler per account. One poller per distinct symbol across those same accounts — so two accounts trading one symbol get two samplers and one poller.

## What settles the cadence

A sampler's is read from the environment on every build. A poller's is a figure standing in the module, which no setting reaches.

## Where each writes

A sampler writes what it finds to the host's own record, under the epoch. A poller writes into a cache the host keeps, which nothing outside the run survives.

## What each needs to start at all

The samplers stop where the host's record is missing. The pollers stop where the venue is missing. So a host with a record and no venue samples and does not poll, and one with a venue and no record polls and does not sample.

## Related

- [How the mark samplers are started and stopped](how-the-mark-samplers-are-started-and-stopped.md)
- [The kept book](the-kept-book.md)
- [The stop that waits for its pollers](the-stop-that-waits-for-its-pollers.md)
