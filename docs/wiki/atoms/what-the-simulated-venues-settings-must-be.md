---
row: P66-01
baseline: 49aa659
created: 2026-11-08 19:59 UTC
modified: 2026-11-08 19:59 UTC
evidence:
  - claim: "Two settings are required, each trimmed and refused where nothing is left: the token for the depth source and the directory the state lives in"
    source: "`__main__.py` 83, then 85-87, and 89, then 91-93"
  - claim: "The host and the address of the depth source each fall back to a built-in where the setting is absent and again where it holds only space"
    source: "`__main__.py` 95, and 97"
  - claim: "Four settings are read as whole numbers, each falling back to a built-in where it holds nothing"
    source: "`__main__.py` 96, or 98-100, or 101-103, or 107-109, the falling back at 133-136"
  - claim: "A whole number that will not convert is refused by name, and one outside the bounds given for that setting refused by name as well"
    source: "`__main__.py` 138-142, then 144-146, then 148-150"
  - claim: "The bounds differ by setting: the port runs from nought, the staleness and the poll interval from one, and the count of stuck polls from two, with only the port given a ceiling"
    source: "`__main__.py` 96, and 98-100, and 101-103, and 107-109"
  - claim: "The depth floor is read as a figure, falling back where it holds nothing, refused where it will not convert, and refused where it is not finite or stands at or below nought"
    source: "`__main__.py` 104-106 into 161-164, then 166-170, then 172-174"
  - claim: "The directory is taken as written, nothing asking whether it exists or can be made"
    source: "`__main__.py` 116"
---
# What the simulated venue's settings must be

[The simulated venue](binsim.md) is started from its environment, and reads nine settings from it.

## The two it must have

A token for the depth source, and a directory for its state. Each is trimmed, and each refused by name where nothing is left.

## The seven it can do without

Each falls back to a built-in value where the setting is absent, and the host and the depth address fall back again where the setting holds only space.

Four are read as whole numbers. One that will not convert is refused by name, and one outside the bounds set for it is refused by name as well.

Those bounds differ. The port runs from nought, the staleness and the poll interval from one, and the count of stuck polls from two. Only the port is given a ceiling.

So a port of nought is accepted, and a count of stuck polls of one is refused where the same figure passes for the two intervals.

## The floor on depth

The depth floor is read as a figure. It falls back where the setting holds nothing, is refused where it will not convert, and is refused again where it is not finite or stands at or below nought.

## The directory

Taken as written. Nothing here asks whether it exists, or whether it can be made — [the lock taken on it](the-lock-one-writer-holds.md) is the first thing to try.

## Related

- [Binsim](binsim.md)
- [The lock one writer holds](the-lock-one-writer-holds.md)
