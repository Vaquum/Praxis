---
row: P154-02
baseline: 49aa659
created: 2026-11-09 12:01 UTC
modified: 2026-11-09 12:01 UTC
evidence:
  - claim: "A command with no order, or whose order is anything but a resting limit, is reported and the change dropped"
    source: "`execution_manager.py` 8680 into 8684"
  - claim: "The old order's name and the command's amount are both insisted upon past that"
    source: "`execution_manager.py` 8686, then 8687"
  - claim: "The new price and the new part-shown amount are worked out from the command and the change together"
    source: "`execution_manager.py` 8688"
  - claim: "A change that yields no price at all is reported and dropped"
    source: "`execution_manager.py` 8689 into 8693"
  - claim: "The new order's name is worked out from the mode, the command and a count of how many amends that command has had, raised by one"
    source: "`execution_manager.py` 8695, then 8696-8698"
  - claim: "The initiation is recorded naming both the old order and the new, the price and the part-shown amount, and written to the record"
    source: "`execution_manager.py` 8700-8712, then 8713"
---
# How a single order's amend is named

Changing one resting order replaces it with another, and the replacement's name is worked out from how many times that command has been changed before.

## What must be true first

The command must have an order, and that order must be a resting limit order. Anything else is reported and the change dropped.

Past that, the old order's name and the command's amount are both insisted upon rather than tested — so a command reaching here without either stops the worker.

## The price

The new price and the new part-shown amount are worked out from the command and the change together, so a change naming only one of them keeps the other. A change that yields no price at all is reported and dropped, since there is nothing to amend to.

## The name

From the mode, the command, and a count of how many amends that command has had — raised by one.

So each amend of one command gets a distinct name by counting, and the count is what makes the names of a twice-amended order differ. That count is kept per command on the account, and [a restart rebuilds it](how-a-restart-reads-its-record-back.md) by counting the initiations in the record.

## The record

The initiation, naming both the old order and the new, the price and the part-shown amount, written to the record before anything is sent.

## Related

- [How an order is named](how-an-order-is-named.md)
- [How a price change is carried out](how-a-price-change-is-carried-out.md)
- [How an amend's replacement order goes out](how-an-amends-replacement-order-goes-out.md)
