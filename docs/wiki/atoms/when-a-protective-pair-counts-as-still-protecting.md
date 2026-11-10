---
row: P169-01
baseline: 49aa659
created: 2026-11-09 12:47 UTC
modified: 2026-11-09 12:47 UTC
evidence:
  - claim: "The list is asked after by its name"
    source: "`execution_manager.py` 7203, then 7204"
  - claim: "A list the venue no longer knows answers that nothing is protecting"
    source: "`execution_manager.py` 7207, then 7208, naming the one failure it catches"
  - claim: "A list the venue reports as refused, or as having all its legs done, answers the same"
    source: "`execution_manager.py` 7210-7212, then 7213"
  - claim: "A working list is answered with, so its legs can be followed again"
    source: "`execution_manager.py` 7215"
  - claim: "Any other venue failure reaches the caller, which remembers it and tries the next name"
    source: "`execution_manager.py` 7204, against 7380, then 7381, then 7382"
  - claim: "A list answered with has its legs re-tracked and the protection made active again"
    source: "`execution_manager.py` 7384 into 7385-7386, then 7389-7391"
---
# When a protective pair counts as still protecting

A protective pair counts as still protecting while the venue reports its list as working, and the reading that decides this answers with the list itself or with nothing.

## The three nothings

A list the venue no longer knows: nothing is protecting under that name.

A list the venue reports as refused: the same.

A list whose legs the venue reports as all done — cancelled, or one of them filled — the same again. A pair that has done its job is no longer doing it.

## The something

A working list is answered with rather than merely confirmed, so its legs can be followed again by the names the venue gives for them.

## The failure that is not an answer

Only the venue's not knowing the list is caught here. Any other venue failure reaches [the watchdog](which-order-the-watchdog-asks-about-first.md) that asked, which remembers it and tries the next name — and a list answered with has its legs re-tracked and the protection made active again.

So the three answers are: this pair is working, this pair is finished, or the venue could not be asked. The reading here gives the first two, and the third is left to travel.

## Related

- [Which order the watchdog asks about first](which-order-the-watchdog-asks-about-first.md)
- [How a cancelled protection pair is judged still working](how-a-cancelled-protection-pair-is-judged-still-working.md)
- [How much a cancelled protection pair filled](how-much-a-cancelled-protection-pair-filled.md)
