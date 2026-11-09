---
row: P27-01
baseline: 49aa659
created: 2026-11-11 10:00 UTC
modified: 2026-11-16 13:30 UTC
evidence:
  - claim: "A protective order the venue reports cancelled gives that bracket's exit command an ending, since the command is not yet marked ended"
    source: "`execution_manager.py` 10663 passing, 10712-10713 into 10782, then 10784-10799"
  - claim: "That ending marks the command ended and drops it from the live ones"
    source: "`execution_manager.py` 10801-10804"
  - claim: "The exit command's name is worked out from the bracket's own, the same way every time"
    source: "`bracket_exit_command_id.py` 31, called at `execution_manager.py` 7608 and at 4915"
  - claim: "A bracket confirmed to hold an unprotected remainder is flattened where the account's policy says to, and that policy stands wherever an account names none"
    source: "`execution_manager.py` 6654-6655, reached at 6938-6939"
  - claim: "The flatten works that name out again, sends a market order under it, and installs the command back among the live ones"
    source: "`execution_manager.py` 7608 and 7763-7778, installed at 7814"
  - claim: "Where the flatten's order is already finished with something filled, an outcome is built for it with no record of ended commands consulted"
    source: "`execution_manager.py` 7859-7883"
  - claim: "The translator across the seam drops the second ending while it still remembers the name"
    source: "`outcome_translator.py` 156-164"
---
# The command that ends twice

One command name can report an ending twice. The path runs through [a bracket](protection.md) whose protection was lost and whose remainder was flattened.

## The first ending

The venue reports the protective order [cancelled](how-a-trade-is-cancelled.md). That report reaches the step that turns venue news into an outcome, which finds the order's command — the bracket's exit command — and finds it not yet marked as ended, so it builds an ending for it.

That ending marks the command ended and drops it from the live ones.

[The exit command's name](the-name-a-brackets-exit-is-given.md) is not a fresh one. It is worked out from the bracket's own name, the same way every time, so anything that works it out again arrives at the same name.

## The flatten that follows

A bracket confirmed to be holding a position with no protection is remediated. Where the account names no policy for that, the fail-safe one stands: flatten the remainder.

The flatten works out the exit command name again, sends a market order under it, and installs that command back among the live ones — the name that was dropped a moment ago. Several things can turn it back before the send, so this is the path rather than the rule.

## The second ending

Where the flatten's own order is already finished with something filled by the time the send returns, an outcome is built for it there and then. Nothing on that path reads the record of commands that have ended.

So the same name carries that ending and then a fill. [The translator](what-the-translator-remembers.md) drops the second while it still remembers the name, and [what becomes of it past that](what-the-translator-remembers.md) is the translator's own subject.

## Related

- [Protection](protection.md)
- [When protection is lost](when-protection-is-lost.md)
- [The name a bracket's exit is given](the-name-a-brackets-exit-is-given.md)
- [What the translator remembers](what-the-translator-remembers.md)
