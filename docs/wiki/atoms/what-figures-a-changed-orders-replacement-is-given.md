---
row: P164-02
baseline: 49aa659
created: 2026-11-09 12:36 UTC
modified: 2026-11-09 12:36 UTC
evidence:
  - claim: "A change to an order showing part of itself takes its price from the change where one is given and from the command otherwise"
    source: "`execution_manager.py` 10213, then 10215-10219"
  - claim: "The size it shows is settled the same way, and both are answered together"
    source: "`execution_manager.py` 10220-10224, then 10225"
  - claim: "A change to a plain resting order takes its price the same way and answers with no shown size at all"
    source: "`execution_manager.py` 10228-10230, then 10231"
  - claim: "Each road insists the command's own settings are of the kind the change is"
    source: "`execution_manager.py` 10214, or 10227"
---
# What figures a changed order's replacement is given

The figures a replacement order goes out with are settled by reading the change against the command, figure by figure: what the change names is used, and what it leaves out is taken from the command as it stands.

## An order showing part of itself

Its price comes from the change where one is given, and from the command otherwise. The size it shows is settled the same way, and the two are answered together.

So a change naming only the price leaves the shown size as it was, and a change naming only the shown size leaves the price. Either is a change to one figure rather than a fresh pair.

## A plain resting order

Its price is settled the same way, and the answer carries no shown size at all — there is none to carry, and the road that places the replacement is told so rather than left to work it out.

## What each road insists on

That the command's own settings are of the kind the change is. A change meant for an order showing part of itself, against a command that places a plain one, is refused where the two are read together rather than carried further.

## Related

- [How a single order's amend is named](how-a-single-orders-amend-is-named.md)
- [What an amend asks the venue before it replaces](what-an-amend-asks-the-venue-before-it-replaces.md)
- [How a change is routed to its handler](how-a-change-is-routed-to-its-handler.md)
