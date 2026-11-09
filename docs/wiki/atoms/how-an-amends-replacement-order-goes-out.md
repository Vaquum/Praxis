---
row: P151-01
baseline: 49aa659
created: 2026-11-15 20:00 UTC
modified: 2026-11-15 20:00 UTC
evidence:
  - claim: "A part-shown amount is carried only where it was given and stands below the remainder, and is otherwise nothing"
    source: "`execution_manager.py` 10321"
  - claim: "One moment is taken for the intent, which is recorded before the send"
    source: "`execution_manager.py` 10322, then 10324-10330"
  - claim: "A timeout or a name the venue already knows sends the order to be rescued by that name"
    source: "`execution_manager.py` 10355 into 10356-10358"
  - claim: "A rescue that finds nothing records the send as failed and then reports the amend as failed, ending the pass"
    source: "`execution_manager.py` 10359 into 10360-10365"
  - claim: "A rescue that finds the order uses it and stamps the moment afresh"
    source: "`execution_manager.py` 10366, then 10367"
  - claim: "A venue failure and a parameter the adapter will not take are handled as one, recording the send as failed and the amend as failed"
    source: "`execution_manager.py` 10368 into 10369-10374"
  - claim: "Past all of it the submission is recorded under the answer's moment and applied"
    source: "`execution_manager.py` 10376-10381, then 10382, then 10383"
  - claim: "The command is then replaced with one carrying the amended price and part-shown amount"
    source: "`execution_manager.py` 10385-10387"
  - claim: "Each fill the answer already carried is written under that same moment"
    source: "`execution_manager.py` 10389, then 10390-10394"
---
# How an amend's replacement order goes out

A replacement order for an amended command is sent much as a fresh slice is, with one difference: every failure reports the amend as failed as well as the send.

## What is settled first

A part-shown amount, carried only where it was given and stands below the remainder, and otherwise nothing. Then one moment, used for the intent, which is recorded before the send goes out.

## The failures that report twice

A timeout or a name the venue already knows sends the order to be rescued. A rescue that finds nothing records the send as failed and then reports the amend as failed.

A venue failure and a parameter the adapter will not take are handled as one branch, recording both the same way — where [a fresh slice](the-four-roads-out-of-a-slices-send.md) keeps those two apart and reports only the send.

So the amend's own failure record is what this road adds, and it is written on every road out but the rescued one.

## What success writes

The submission, under the moment the venue's answer came back, recorded and applied. Then the command itself is replaced with one carrying the amended price and part-shown amount — so the command's own parameters are rewritten only once the venue has taken the new order.

Each fill the answer already carried is written under that same moment.

## Related

- [The four roads out of a slice's send](the-four-roads-out-of-a-slices-send.md)
- [How a price change is carried out](how-a-price-change-is-carried-out.md)
- [Changing work already sent](changing-work-already-sent.md)
