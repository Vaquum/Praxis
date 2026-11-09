---
row: P145-02
baseline: 49aa659
created: 2026-11-15 17:00 UTC
modified: 2026-11-15 17:00 UTC
evidence:
  - claim: "An entry holding nothing has its bracket registered all the same, with no protection placed and the skip reported"
    source: "`execution_manager.py` 4887 into 4898, then 4904"
  - claim: "Otherwise the bracket is marked as having its protection placed before anything is sent"
    source: "`execution_manager.py` 4906"
  - claim: "The protective side is the opposite of the entry's, settled by testing the entry for a buy"
    source: "`execution_manager.py` 4909-4911"
  - claim: "The three protective prices are worked out from the command and the average entry price"
    source: "`execution_manager.py` 4912-4914"
  - claim: "The exit's name is derived from the entry's, and the order's name worked out from the entry's mode, the command and the protection's place"
    source: "`execution_manager.py` 4915, then 4916-4920"
  - claim: "What the exit is allowed to fill is recorded by amount alone, with no money figure"
    source: "`execution_manager.py` 4927"
  - claim: "Legs falling on the wrong side of the entry's fill are refused as an adapter failure before the venue is reached"
    source: "`execution_manager.py` 4960-4962, then 4965"
  - claim: "Only past that is the pair sent to the venue"
    source: "`execution_manager.py` 4967-4975"
  - claim: "The exit command is installed, given the entry's trade name and mapped to its order only after the send has answered"
    source: "`execution_manager.py` 5017, then 5018, then 5019, past 5015"
---
# What placing a bracket's protection writes first

Placing a bracket's protection marks the bracket as protected before it sends anything, and writes the exit command's own records only after the venue has answered.

## The entry that holds nothing

Its bracket is registered all the same, with no protection placed, and the skip reported. So a bracket exists for an entry that filled nothing, carrying no protection and nothing owing.

## The mark that comes before the send

The bracket is marked as having its protection placed before the pair is built, let alone sent. A failure anywhere after that leaves a bracket claiming a protection that may never have reached the venue.

## What is worked out

The protective side, as the opposite of the entry's, settled by testing the entry for a buy. The three prices, from the command and the average entry price. The exit's name, derived from the entry's. The order's name, from the entry's mode, the command and the protection's place.

What the exit is allowed to fill is recorded by amount alone, with no money figure — so nothing caps it by value.

## The refusal before the venue

Legs falling on the wrong side of the entry's fill are refused as an adapter failure, before the venue is reached at all. Only past that is the pair sent.

## What waits for the answer

The exit command is installed, given the entry's [trade name](what-a-trade-is.md), and mapped to its order only after the send has answered. So between the mark and the answer the bracket says it is protected while nothing yet maps the exit to an order.

## Related

- [Protection](protection.md)
- [What a bracket's protective exit is registered as](what-a-brackets-protective-exit-is-registered-as.md)
- [How a venue failure is sorted](how-a-venue-failure-is-sorted.md)
