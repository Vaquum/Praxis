---
row: P66-05
baseline: 49aa659
created: 2026-11-13 00:00 UTC
modified: 2026-11-13 00:00 UTC
evidence:
  - claim: "Started as a program, the guard around the whole run catches the ordinary kind of failure, writes it out with its trace, and answers with a failing code"
    source: "`__main__.py` 320-324"
  - claim: "An ending asked for outright is of another kind altogether and is not caught by that guard"
    source: "`__main__.py` 322, naming the ordinary kind alone"
  - claim: "Four roads end the run by asking for one, each with a message of its own: a money figure that will not convert, a missing directory for the command, a directory another process holds during the command, and the same during the run"
    source: "`__main__.py` 264-265, or 286-287, or 300, or 314"
  - claim: "The reading of the arguments ends the run the same way, writing its own complaint to the error stream first"
    source: "`__main__.py` 280"
  - claim: "Reading the settings raises the ordinary kind, so a bad setting is the one of these that reaches the guard"
    source: "`__main__.py` 308, raising at 86-87, or 92-93, or 141-142, or 145-146, or 149-150, or 169-170, or 173-174"
---
# Which failures give a sentence and which a stack

Started as a program, [the simulated venue](binsim.md) puts a guard around its whole run — and that guard sees some failures and not others.

## What the guard catches

A failure of the ordinary kind. It is written out with its trace, and the program answers with a failing code.

## What goes past it

An ending asked for outright. That is a thing of another kind altogether, and the guard names only the ordinary one, so an ending passes it untouched and the message travels on its own.

Four roads end the run that way, each with its own sentence: a money figure that will not convert, a missing directory for the command, a directory another process holds during the command, and the same during the run.

The reading of the arguments ends the run that way too, having written its own complaint to the error stream first.

## The one that does not

Reading the settings raises the ordinary kind. So a missing token, a missing directory, a whole number that will not convert, one outside its bounds, or a bad depth floor is the one sort of bad start that reaches the guard — and the only one an operator meets as a stack.

## Why it reads oddly

The careful sentences and the bare stack are not a judgement about which failure deserves which. They follow from the kind each failure happens to be.

## Related

- [What running the simulated venue plainly does](what-running-the-simulated-venue-plainly-does.md)
- [What the simulated venue's settings must be](what-the-simulated-venues-settings-must-be.md)
