---
row: P66-03
baseline: 49aa659
created: 2026-11-08 19:59 UTC
modified: 2026-11-08 19:59 UTC
evidence:
  - claim: "Registering is the one named command, and it takes the account's name and its starting money as arguments, the coin balance standing at nought where it is left out"
    source: "`__main__.py` 275-278"
  - claim: "The directory comes from the environment rather than from an argument, and a missing one ends the command with a message"
    source: "`__main__.py` 283, then 285-287"
  - claim: "Each money argument is turned into a figure, and one that will not convert ends the command with a message naming the argument"
    source: "`__main__.py` 289-290, into 261-265"
  - claim: "Nothing here asks either figure to be finite or to stand at or above nought, which the ledger asks as the account is built"
    source: "`__main__.py` 259-265, against `ledger.py` 287-297"
  - claim: "The lock on the directory is held across reading the saved state and registering into it"
    source: "`__main__.py` 250, around 252 and 254-256"
  - claim: "A directory another process holds ends the command with that refusal's own message"
    source: "`__main__.py` 299-300"
  - claim: "The minted key is written to the standard output on its own line, which is the one time it is shown to anybody"
    source: "`__main__.py` 304, the only writing of it"
---
# Registering an account from the command line

[The simulated venue](binsim.md) has one named command, and it exists to hand an operator a key.

## What it takes

The account's name and its starting money. The coin balance may be left out and stands at nought where it is.

The directory comes from the environment rather than from an argument, and a missing one ends the command with a message saying so.

## What it checks

Each money argument is turned into a figure. One that will not convert ends the command with a message naming the argument.

Nothing here asks either figure to be finite, or to stand at or above nought. [The ledger asks both](what-registering-an-account-refuses-and-the-key-it-mints.md) as the account is built, so a figure that is no number is refused a step later and by a different complaint.

## The lock around it

The lock on the directory is held across reading the saved state and registering into it. That is what stops the command and a running service each writing over the other.

A directory another process holds ends the command with [that refusal's own message](what-a-refused-writer-is-told.md).

## The key

The minted key is written to the standard output on its own line.

That is the one time it is shown to anybody. The ledger keeps only a scrambled form of it, so an operator who does not capture that line cannot be given the key again.

## Related

- [Binsim](binsim.md)
- [What registering an account refuses, and the key it mints](what-registering-an-account-refuses-and-the-key-it-mints.md)
- [The lock one writer holds](the-lock-one-writer-holds.md)
