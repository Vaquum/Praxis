---
row: P105-01
baseline: 49aa659
created: 2026-11-14 06:00 UTC
modified: 2026-11-14 06:00 UTC
evidence:
  - claim: "A start on an already started facade answers at once"
    source: "`praxis/trading.py` 506 into 507"
  - claim: "The running loop is taken and held before any of the work begins"
    source: "`praxis/trading.py` 509, ahead of 511"
  - claim: "Every account's stored events are read in one go and sorted into lists per account"
    source: "`praxis/trading.py` 515, then 517 into 518-519"
  - claim: "Each configured account is registered as booting, added to the managed set, and started with its own events"
    source: "`praxis/trading.py` 521, then 522, then 523, then 524"
  - claim: "A failure anywhere in that lets the loop go, undoes what was built, and raises on"
    source: "`praxis/trading.py` 525 into 526, then 527, then 528"
  - claim: "The undoing closes every stream it finds and clears it from the map whether the closing worked or not"
    source: "`praxis/trading.py` 806 into 807-810, then 811"
  - claim: "It then unregisters every managed account and clears each from three collections, again whether that worked or not"
    source: "`praxis/trading.py` 813 into 814-817, then 818, and 819, and 820"
  - claim: "The reconciling loop is set going and the started flag raised only once all of that has passed"
    source: "`praxis/trading.py` 530, then 531"
---
# What a failed start undoes

A start builds each account in turn, and a failure anywhere in that undoes all of it before raising.

## What is taken first

A start on an already started facade answers at once. Otherwise the running loop is taken and held before any of the work begins — which is what [closes the setters](what-the-facade-refuses-once-a-start-has-begun.md) from that moment on, before anything has actually started.

## The reading

Every account's stored events are read in one go and sorted into lists per account. So the spine is read once however many accounts there are, and each account is handed only its own.

## Each account

Registered as booting, added to the managed set, and started with its own events.

## The undoing

A failure anywhere lets the loop go, undoes what was built, and raises on.

The undoing closes every stream it finds and clears it from the map whether the closing worked or not. It then unregisters every managed account and clears each from three collections, again whether that worked or not.

So the undoing cannot itself fail to finish: each failure is reported and the clearing happens anyway. What it cannot do is put back anything the venue already knows about.

## What a success sets last

The reconciling loop is set going and the started flag raised only once all of that has passed.

## Related

- [What a stop will not leave running](what-a-stop-will-not-leave-running.md)
