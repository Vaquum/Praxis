---
row: P126-01
baseline: 49aa659
created: 2026-11-15 07:30 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "A host is refused unless exactly one of a record and a path to one is given, both and neither failing the same test"
    source: "`launcher.py` 2750 into 2751-2752"
  - claim: "Where the key's permissions are to be enforced, every cap must be set, and the unset ones are named together in order"
    source: "`launcher.py` 2754, then 2755-2761, then 2762 into 2763-2768"
  - claim: "The caps weighed are the caller's where one was given, and otherwise a set read from the environment as though the host were not live"
    source: "`launcher.py` 2756-2758"
  - claim: "The caps kept are chosen the same way a second time, so a host given none reads the six settings twice"
    source: "`launcher.py` 2771, after 2757-2758, the six read at 760-767"
  - claim: "The same demand is written again where that set is built for a live host, with a failure of another kind and the names in their declared order"
    source: "`launcher.py` 780, then 781 into 782-786, against 2762 into 2763-2768"
  - claim: "Whether the host owns the record it writes to is remembered as whether none was handed in"
    source: "`launcher.py` 2779"
---
# What a host refuses to be built as

A host refuses two ways of being built before it does anything else, and both refusals are about what it was handed rather than what it finds.

## The record

Exactly one of a record and a path to one. The test compares the two absences against each other, so being handed both and being handed neither fail the same line.

Whether the host owns the record it writes to is remembered as whether none was handed in — which is what later decides whether closing the host closes the record.

## The caps

Where the key's permissions are to be enforced, every cap must be set. The unset ones are gathered and named together in order, so a deployment short of three learns about three.

The caps weighed are the caller's where one was given, and otherwise a set read from the environment as though the host were not live. The caps kept are chosen the same way a second time — so a host given none reads the six settings twice.

## The demand written twice

Building that set for a live host makes the same demand, with a failure of another kind and the names in the order they were declared rather than sorted.

So the same deployment, short of the same cap, is refused by one of two lines depending on how it was built: by the builder where the mode said live, and by the host where the caller said to enforce permissions.

## Related

- [What a host keeps as it is built](what-a-host-keeps-as-it-is-built.md)
- [The deployment caps](the-deployment-caps.md)
- [Starting a host](starting-a-host.md)
- [What a timing setting is held to](what-a-timing-setting-is-held-to.md)
