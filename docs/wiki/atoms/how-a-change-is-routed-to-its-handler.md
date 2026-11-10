---
row: P145-01
baseline: 49aa659
created: 2026-11-09 11:18 UTC
modified: 2026-11-09 11:18 UTC
evidence:
  - claim: "A change whose parameters are a bracket's goes straight to the bracket handler and returns, before any other test is made"
    source: "`execution_manager.py` 8616 into 8617-8619, then 8620"
  - claim: "Past that, a command already terminal, a command the manager does not hold, and a command with an amend already pending are each reported and dropped"
    source: "`execution_manager.py` 8622 into 8624, or 8626, then 8627 into 8629, or 8631 into 8636"
  - claim: "A command running a scheme is routed by the shape of the change's own parameters, to the scheme handler or the ladder handler"
    source: "`execution_manager.py` 8638, then 8639, then 8640-8643 into 8644, or 8645 into 8646"
  - claim: "A shape neither handler takes is reported as unsupported for the command's mode, and the scheme road ends either way"
    source: "`execution_manager.py` 8647, then 8653"
  - claim: "Past the schemes, anything but a single-order or a part-shown change is reported as unsupported for that mode too"
    source: "`execution_manager.py` 8655 into 8661"
  - claim: "A single-order change carrying either stop field is reported as unsupported, limit price alone being amendable"
    source: "`execution_manager.py` 8663-8666 into 8672"
  - claim: "Only then is the order looked up, through the mapping from command to order, and read as nothing where no name is held"
    source: "`execution_manager.py` 8674, then 8675-8679"
  - claim: "The bracket handler makes its own tests instead, dropping the change where no live bracket stands or its protection is unplaced or unnamed"
    source: "`execution_manager.py` 9387, then 9388 into 9393, or 9395 into 9400, or 9402"
---
# How a change is routed to its handler

A change reaching the worker is sent to one of four handlers, and which one is settled by the shape of the change's own parameters rather than by the mode of the command it names.

## The road taken first

A change whose parameters are a bracket's goes straight to the bracket handler and returns. That happens before the tests the other roads make.

So a bracket change is never turned away here for naming a terminal command, an unheld command, or one with an amend already pending. The bracket handler makes its own tests instead — no live bracket, or a protection unplaced or unnamed — and those are different tests.

## The three that drop a change

Past the bracket road: a command already terminal, a command the manager does not hold, and a command with an amend already pending. Each is reported and dropped.

## The schemes

A command running a scheme is routed by the change's parameter shape — interval slices or volume weights to the scheme handler, a ladder's to the ladder handler. A shape neither takes is reported as unsupported for the command's mode, and the scheme road ends either way.

So the mode named in that report is the command's, while the thing that failed to match was the parameters' shape.

## What is left

Anything but a single-order or a part-shown change is reported as unsupported. A single-order change carrying either stop field is reported too — the limit price alone is amendable.

Only then is the order looked up, through the mapping from command to order, and read as nothing where no name is held.

## Related

- [Changing work already sent](changing-work-already-sent.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [Which commands count as amendable](which-commands-count-as-amendable.md)
