---
row: P174-02
baseline: 49aa659
created: 2026-11-09 12:57 UTC
modified: 2026-11-09 12:57 UTC
evidence:
  - claim: "One moment is taken and carried into both the record and the report"
    source: "`execution_manager.py` 2296, then 2299, and 2320"
  - claim: "The record says refused, with the boot's own reason"
    source: "`execution_manager.py` 2297-2304, the reason set at 2303, then 2305, then 2306"
  - claim: "The command is marked ended as the record goes down"
    source: "`execution_manager.py` 2307"
  - claim: "The report names a stand-in target of one, nothing filled and no average price"
    source: "`execution_manager.py` 2309-2321, the stand-in at 2314, its value at 177"
  - claim: "It names nought parts done of one"
    source: "`execution_manager.py` 2317, and 2318"
  - claim: "It is handed out with retries"
    source: "`execution_manager.py` 2330"
---
# What a boot's rejection of an orphan says

A command a boot finds accepted but never carried out is reported to Nexus as refused, and the report is made of stand-ins because nothing of the command itself was ever read.

## What is known and what is not

The command's name, its trade's name, and that it was accepted. Not its size, its side, or how it was meant to be worked.

So the report names a target of one, nothing filled, no average price, and nought parts done of one. The figures say nothing about the command; the status and the reason say everything.

## The record and the report

One moment is taken and carried into both, so the two agree about when.

The record says refused with the boot's own reason, and the command is marked ended as that record goes down — which keeps every later report for it from being made.

The report is then handed out with retries, so Nexus hears the refusal even if the first attempt to tell it fails.

## Related

- [The three kinds of orphan a boot finds](the-three-kinds-of-orphan-a-boot-finds.md)
- [What becomes of work still open](what-becomes-of-work-still-open.md)
- [What an outcome is](what-an-outcome-is.md)
