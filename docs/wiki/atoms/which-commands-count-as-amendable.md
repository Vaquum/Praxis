---
row: P133-02
baseline: 49aa659
created: 2026-11-15 11:00 UTC
modified: 2026-11-15 11:00 UTC
evidence:
  - claim: "The derived names of the brackets' protective exits are worked out first, to be taken out later"
    source: "`execution_manager.py` 1028-1030"
  - claim: "A command counts as having a live order where the order its name points at is there and its status is not a terminal one"
    source: "`execution_manager.py` 1031, then 1032, then 1033, then 1034 into 1035"
  - claim: "The running schemes, those live-order commands and the brackets are taken together, less the protective exits' names"
    source: "`execution_manager.py` 1037-1041"
  - claim: "Then the terminal commands are taken out, and the commands already waiting on an amend"
    source: "`execution_manager.py` 1042, then 1043"
  - claim: "Then any scheme held for protection, mid-amend, or draining is taken out"
    source: "`execution_manager.py` 1044-1049"
  - claim: "A scheme held in any other way is taken out only where it is a ladder"
    source: "`execution_manager.py` 1050-1053"
  - claim: "Each bracket entry is then settled last: added where its protection is placed, named and active, and discarded otherwise"
    source: "`execution_manager.py` 1056, then 1057-1061, then 1062 into 1063, or 1064 into 1065"
  - claim: "What is left is handed back in order"
    source: "`execution_manager.py` 1067"
---
# Which commands count as amendable

An amendable command is one the manager will let a change be aimed at, and the set is built by gathering three kinds and then taking five things out of them.

## What goes in

The running schemes. The commands whose order is live — meaning the order their name points at is there and its status is not a terminal one, looked up one command at a time. And the brackets.

## What comes out

The derived names of the brackets' protective exits, worked out before the gathering so they can be removed after it. Then the terminal commands. Then the commands already waiting on an amend.

Then any scheme held for protection, mid-amend, or draining.

## The hold that only costs a ladder

A scheme held in any other way is taken out only where it is a ladder. So the same hold leaves a scheme of another mode amendable and makes a ladder un-amendable.

## The brackets, settled last

Each bracket entry is then settled on its own: added where its protection is placed, named and active, and discarded otherwise.

That loop runs after every removal above it, and the adding asks nothing about what those removals did. So a bracket entry whose protection is active is amendable whatever any earlier line concluded about it.

## Related

- [What the manager tells you about an unknown account](what-the-manager-tells-you-about-an-unknown-account.md)
- [Changing work already sent](changing-work-already-sent.md)
- [A change waiting out a hold](a-change-waiting-out-a-hold.md)
