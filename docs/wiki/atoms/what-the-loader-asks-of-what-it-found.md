---
row: N17-07
baseline: 49aa659
created: 2026-11-09 20:00 UTC
modified: 2026-11-09 20:00 UTC
evidence:
  - claim: "A module whose loading plan cannot be made is refused"
    source: "`nexus/strategy/loader.py` 105-107"
  - claim: "A failure while running the module is wrapped as one error naming the path"
    source: "`nexus/strategy/loader.py` 111-115"
  - claim: "The module must carry something under the expected name"
    source: "`nexus/strategy/loader.py` 78-80"
  - claim: "That something must be a class, and must inherit from the base"
    source: "`nexus/strategy/loader.py` 84-86, or 88-90"
  - claim: "It must not be the base itself"
    source: "`nexus/strategy/loader.py` 92-94"
  - claim: "A failure building the strategy is wrapped as one error naming the strategy rather than the path"
    source: "`nexus/strategy/loader.py` 31-35"
---
# What the loader asks of what it found

Running the file is how the thing being asked about comes to exist, and four questions follow about what turned up.

## Running it

A module whose loading plan cannot be made is refused. A failure while the module runs is wrapped as one error naming the path — so whatever a strategy file does at import time, what comes back out is one error pointing at the file.

## The four questions

The module must carry something under the expected name. That something must be a class. It must inherit from the base. And it must not be the base itself.

The last is the one a reader would not think to ask. A file that imports the base and exports it unchanged satisfies the three before it, and is refused by the fourth.

## One step later

Past all four, the class is built with the strategy's reference. A failure there is wrapped as one error too, naming the strategy rather than the file.

So the two wrappings mark the two places a strategy's own code runs, and each says which it was.

## Related

- [What the loader asks of a path](what-the-loader-asks-of-a-path.md)
- [What a strategy must provide](what-a-strategy-must-provide.md)
- [The wrapper every strategy sits behind](the-wrapper-every-strategy-sits-behind.md)
