---
row: P154-01
baseline: 49aa659
created: 2026-11-15 21:30 UTC
modified: 2026-11-15 21:30 UTC
evidence:
  - claim: "An account the manager does not hold ends the pass"
    source: "`execution_manager.py` 7908, then 7909 into 7910"
  - claim: "An account whose settings answer anything but flatten-then-halt ends it too, so the recovery runs only where the settings ask for a flatten"
    source: "`execution_manager.py` 7912-7915 into 7916"
  - claim: "One walk gathers the bracket starts and the protections reported failed"
    source: "`execution_manager.py` 7918-7919, then 7920, then 7921 into 7922, or 7923 into 7924"
  - claim: "Each failed protection has its flatten's name worked out from the mode, the command and the flatten's own place"
    source: "`execution_manager.py` 7926, then 7927-7929"
  - claim: "A flatten already ended having filled something is passed over"
    source: "`execution_manager.py` 7930, then 7931-7934 into 7935"
  - claim: "A failed protection with no bracket start recorded is reported and passed over"
    source: "`execution_manager.py` 7938, then 7939 into 7947"
  - claim: "The command is rebuilt from that start and the protective side taken as the opposite of its own"
    source: "`execution_manager.py` 7949, then 7950, then 7951-7953"
  - claim: "The venue is asked about that flatten, a name it is unaware of read as nothing and any other failure reported and passed over"
    source: "`execution_manager.py` 7955-7960, then 7961 into 7962, or 7963 into 7970"
  - claim: "A flatten the venue says filled something is reconciled and the command passed over"
    source: "`execution_manager.py` 7972 into 7973-7980, then 7982"
---
# Which failed protections a boot re-flattens

A boot re-sends the flatten that a failed protection should have placed, and it does so only for accounts whose settings ask for a flatten at all.

## The two that end the pass

An account the manager does not hold. And an account whose settings answer anything but flatten-then-halt — so a deployment that answers otherwise never re-flattens, whatever its record holds.

## What one walk gathers

The bracket starts, and the protections reported failed. Each failed protection is then taken in turn.

## The name worked out

The flatten's name, from the mode, the command and the flatten's own place — the same working-out that named it when it was sent. A flatten already ended having filled something is passed over, since the position it was for is already closed.

## The two that pass one over

A failed protection with no bracket start recorded, which is reported — there is nothing to rebuild the command from.

And a venue failure asking about the flatten, also reported and left for a later reconcile. A name the venue is unaware of reads as nothing instead, and the pass carries on with it.

## What the venue's answer settles

A flatten the venue says filled something is reconciled against that answer, and the command passed over — its flatten did go out, and what remains is to get the fills into the record.

## Related

- [Why a flatten is recovered only once](why-a-flatten-is-recovered-only-once.md)
- [What a lost protection is reported with](what-a-lost-protection-is-reported-with.md)
- [How big a flatten goes out](how-big-a-flatten-goes-out.md)
