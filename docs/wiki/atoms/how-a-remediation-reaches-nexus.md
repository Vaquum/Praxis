---
row: P185-01
baseline: 49aa659
created: 2026-11-09 13:45 UTC
modified: 2026-11-09 13:45 UTC
evidence:
  - claim: "Nothing is handed on at all where the manager was built with no way of handing one on"
    source: "`execution_manager.py` 6781, then 6782"
  - claim: "The remediations waiting for that one account are gathered, the rest left where they are"
    source: "`execution_manager.py` 6784-6788"
  - claim: "Each is handed on in turn, and a failure leaves it waiting while the walk goes on to the next"
    source: "`execution_manager.py` 6789, then 6790, then 6791, then 6792, then 6799"
  - claim: "A success is recorded as a delivery and the remediation dropped from those waiting"
    source: "`execution_manager.py` 6801-6806, then 6807, then 6808"
  - claim: "A replay gathers the deliveries already recorded and remembers again only the failures none answers for"
    source: "`execution_manager.py` 6757-6761, then 6763, then 6764, then 6765-6770"
  - claim: "A lost protection remembers its remediation as the failure is recorded, and drains the waiting ones last"
    source: "`execution_manager.py` 6922-6924, then 6943"
---
# How a remediation reaches Nexus

A remediation is what Praxis tells Nexus about a position whose protection it could not keep, and it waits in memory until Nexus takes it.

## Who hands it on

Nothing is handed on at all where the manager was built with no way of handing one on. Where there is one, the remediations waiting for that one account are gathered and the rest left where they are.

Each is handed on in turn. A failure leaves it waiting and the walk goes on to the next, so one unreachable Nexus does not hold up the others.

## How one stops waiting

A success is recorded as a delivery, and the remediation dropped from those waiting. The record is what survives a restart: a replay gathers the deliveries already recorded, and remembers again only the failures none answers for.

So a remediation handed on and recorded is never handed on twice, and one handed on without the record reaching the spine is handed on again after a restart.

## When it is remembered

As the failure is recorded. The draining of those waiting is the last thing [the lost protection's own road](what-happens-before-a-lost-protections-close-is-attempted.md) does.

## Related

- [What happens before a lost protection's close is attempted](what-happens-before-a-lost-protections-close-is-attempted.md)
- [When protection is lost](when-protection-is-lost.md)
- [The holds a report places](the-holds-a-report-places.md)
