---
row: N8-06
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-28 18:45 UTC
evidence:
  - claim: "The cap on entries counts them in one list for the whole account, with nothing naming a strategy in what it holds, so every strategy on the account spends the one allowance"
    source: "`nexus/core/validator/intake_stage.py` 98 and 112-120, the hooks built once at `praxis/launcher.py` 959-963 inside a walk built per account at 4104"
  - claim: "It reads an entry alone, drops what has aged out of the second behind it, refuses where the count stands at the cap, and counts the rest"
    source: "`nexus/core/validator/intake_stage.py` 102-103, 105-110, 112-118 and 120"
  - claim: "It is put in front of the other two only where a figure is carried, which on the one road a running host builds them by is the figure Praxis read from its environment and set on the settings"
    source: "`nexus/core/validator/intake_stage.py` 74-78, the one build outside the tests passing no figure of its own at `praxis/launcher.py` 959-963, the settings carrying it from 359 over 763"
---
# The cap on how fast entries may go in

A cap turns an entry away where the allowance for the second behind it is already spent.

## One allowance for the whole account

The cap keeps one list of the moments it let entries by, and what it keeps in that list names no strategy. There is one such list per [account](what-an-account-is.md), because the checks are built once for each account the host runs.

Every strategy on an account therefore spends the same allowance. One strategy sending hard can use the whole of it up and leave the others on the account turned away.

## What one pass does

It looks at entries alone and lets everything else by untouched. Then it drops from its list every moment that has reached a second old, refuses where what is left already stands at the cap, and otherwise adds this moment to the list and passes the entry on.

So the window slides with the clock rather than resetting on a boundary, and the allowance is spent and recovered continuously.

## Where it sits, and when it is there at all

The cap goes ahead of the other two hooks on [the same stage](the-checks-a-decision-passes.md), and only where a figure for it is carried. On the one road a running host builds those hooks by, that figure is the one Praxis read from its surroundings as it started and set on the host's settings.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [The window that turns a repeated entry away](the-window-that-turns-a-repeated-entry-away.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-28 18:45 UTC
