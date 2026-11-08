---
row: P66-04
baseline: 49aa659
created: 2026-11-13 00:00 UTC
modified: 2026-11-13 00:00 UTC
evidence:
  - claim: "Logging is arranged before the arguments are even read, though a complaint about an argument is written by the argument reader itself rather than through it"
    source: "`__main__.py` 270 ahead of 272, the reading at 280"
  - claim: "A run naming the one command registers and answers, going no further"
    source: "`__main__.py` 282, returning at 306"
  - claim: "A run naming no command falls past that and reads the settings, so the service is what running it plainly gives"
    source: "`__main__.py` 308, reached where 282 does not hold"
  - claim: "The lock on the directory is taken around the whole of the running, and let go only as the running ends"
    source: "`__main__.py` 311, around 312"
  - claim: "A directory another process holds ends the attempt with that refusal's own message rather than a trace"
    source: "`__main__.py` 313-314"
  - claim: "Started as a program, a failure of the ordinary kind is written out with its trace and the program answers with a failure"
    source: "`__main__.py` 320-324"
  - claim: "Nothing outside that guard catches a failure of the settings, so a bad setting takes the same road as any other failure"
    source: "`__main__.py` 308 standing outside the catch at 310-314"
---
# What running the simulated venue plainly does

[The simulated venue](binsim.md) is one program with one named command, and leaving the command out is how the service itself is run.

## Before anything else

Logging is arranged before the arguments are even read. A complaint about an argument is nonetheless written by the argument reader itself, straight to the error stream, rather than through the logging just arranged.

## The two roads

A run naming the command registers an account and answers, going no further.

A run naming no command falls past that and reads [the settings](what-the-simulated-venues-settings-must-be.md). So the service is what running the program plainly gives, and registering is the exception rather than the rule.

## The lock

The lock on the directory is taken around the whole of the running, and let go only as the running ends. A service therefore holds it for as long as it is up, which is what makes a second service, or a registering command, fail rather than quietly disagree.

A directory another process holds ends the attempt with that refusal's own message rather than a trace, so an operator reads a sentence instead of a stack.

## Everything else

Started as a program, a failure of the ordinary kind is written out with its trace and the program answers with a failure. Reading the settings stands outside the catch for a held directory, so a bad setting takes that road.

[Which failures give a sentence and which a stack](which-failures-give-a-sentence-and-which-a-stack.md) turns on what kind of thing each one is.

## Related

- [Binsim](binsim.md)
- [What the simulated venue's settings must be](what-the-simulated-venues-settings-must-be.md)
- [Registering an account from the command line](registering-an-account-from-the-command-line.md)
- [Which failures give a sentence and which a stack](which-failures-give-a-sentence-and-which-a-stack.md)
