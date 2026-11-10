---
row: P148-02
baseline: 49aa659
created: 2026-11-09 11:31 UTC
modified: 2026-11-09 11:31 UTC
evidence:
  - claim: "The parameters are insisted upon as a bracket's and the amount as present, before anything is written"
    source: "`execution_manager.py` 4499, then 4500"
  - claim: "A start is recorded carrying both protective prices, both offsets, the stop's limit price, the whole amount and the command's timeout, and applied"
    source: "`execution_manager.py` 4502, then 4503-4517, then 4518, then 4519"
  - claim: "Only then is the entry sent, as a market slice for the whole amount at the entry's own place"
    source: "`execution_manager.py` 4521-4522"
  - claim: "An entry whose send answered with no order ends the command with nothing filled, saying the entry's submission failed"
    source: "`execution_manager.py` 4525 into 4526-4533"
  - claim: "Otherwise the command is mapped to that order and a live bracket registered holding both"
    source: "`execution_manager.py` 4535, then 4536, then 4537"
  - claim: "An entry order already in a terminal state is settled at once"
    source: "`execution_manager.py` 4539, then 4541 into 4542"
  - claim: "Otherwise the outcome is built from the admitted totals, with the average price the admitted money over the admitted amount"
    source: "`execution_manager.py` 4544-4546, then 4547-4549, then 4551"
---
# What starting a bracket writes before its entry

Starting a bracket records the whole shape of it before the entry is sent, so a crash between the two leaves a record of a bracket whose entry never went out.

## What is insisted upon

That the parameters are a bracket's and that the amount is present. Both are insisted upon rather than tested, so a command reaching here without them stops the worker rather than being refused.

## The record written first

A start carrying both protective prices, both offsets, the stop's limit price, the whole amount and the command's timeout. It is written to the record and applied.

Only then is the entry sent — as a market slice for the whole amount, at the entry's own place in the naming.

## The two ways it ends

An entry whose send answered with no order ends the command with nothing filled, saying the entry's submission failed. The start already written stays in the record.

Otherwise the command is mapped to that order, a live bracket registered holding both, and the entry order read back. An entry already in a terminal state is settled at once.

## The outcome of a bracket still working

Built from [the admitted totals](two-ways-of-asking-what-a-command-filled.md), with the average price the admitted money over the admitted amount. So a bracket whose entry is still resting answers with whatever has been admitted so far rather than with nothing.

## Related

- [What placing a bracket's protection writes first](what-placing-a-brackets-protection-writes-first.md)
- [The four roads out of a slice's send](the-four-roads-out-of-a-slices-send.md)
- [Protection](protection.md)
