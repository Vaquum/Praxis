---
row: P123-02
baseline: 49aa659
created: 2026-11-09 09:42 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "Each sweep answers an empty list where the trading stack is missing"
    source: "`launcher.py` 3631 into 3632, and 3657 into 3658"
  - claim: "Cancelling gathers the command names off the account's open orders and walks them in order"
    source: "`launcher.py` 3634-3637, then 3640"
  - claim: "Each abort is sent under a wrapping of its own, naming the operator as the reason and stamped with the host's clock"
    source: "`launcher.py` 3642, then 3643-3646"
  - claim: "Only a command whose abort raised nothing reaches the answer, and the gathered names are handed back once the walk is done"
    source: "`launcher.py` 3650, under the loop at 3640, then 3652"
  - claim: "Closing walks the account's positions and passes over any whose amount stands at or below nothing"
    source: "`launcher.py` 3662, then 3663, then 3665 into 3666"
  - claim: "The closing side is the opposite of the position's, settled by testing it for a buy"
    source: "`launcher.py` 3668-3672"
  - claim: "One market order for the whole amount is sent under a wrapping of its own, with a deadline of its own"
    source: "`launcher.py` 3674, then 3675-3683, the deadline at 3680"
  - claim: "A trade whose order raised still reaches the answer, carrying an error where a command name would be, and the whole list is handed back once the walk is done"
    source: "`launcher.py` 3684 into 3686, or 3688, then 3690"
---
# What a sweep does to each item

A sweep walks one account's working orders, or its open positions, and acts on each in turn, with a failure on one costing only that one.

## Where neither starts

An empty list, where the trading stack is missing. An operator asking before the host has started is answered as though there were nothing to sweep.

## Cancelling

The command names are gathered off the account's open orders and walked in order. An abort goes out for each under a wrapping of its own, naming the operator as the reason and stamped with the host's clock.

Only a command whose abort raised nothing reaches the answer, and the gathered names are handed back once the walk is done.

## Closing

The account's positions are walked, and any whose amount stands at or below nothing is passed over. The closing side is the opposite of the position's, settled by testing it for a buy. One market order goes out for the whole amount under a wrapping of its own, with a deadline of its own rather than the host's usual one.

A trade whose order raised still reaches the answer, carrying an error where a command name would be.

## Where the two answers differ

Both sweeps carry on past a failure on one item. The closing says so in what it answers; the cancelling leaves that command out of the list.

So an operator reading a cancelling's answer learns which commands were aborted and cannot tell whether any were missed, where a closing's answer names every position it tried.

## Related

- [What the operator's two sweeps answer with](what-the-operators-two-sweeps-answer-with.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
- [How big a flatten goes out](how-big-a-flatten-goes-out.md)
