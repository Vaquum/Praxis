---
row: P178-02
baseline: 49aa659
created: 2026-11-16 09:30 UTC
modified: 2026-11-16 09:30 UTC
evidence:
  - claim: "The pass looks the account up and ends there where the manager holds no such account"
    source: "`execution_manager.py` 7323, then 7324 into 7325"
  - claim: "It walks a copy of the account's live work"
    source: "`execution_manager.py` 7327"
  - claim: "Work with no phase written, or no context held, is passed over"
    source: "`execution_manager.py` 7328 into 7329"
  - claim: "Each other is driven again"
    source: "`execution_manager.py` 7331"
  - claim: "The driving itself does nothing where the context is gone, so the context is read twice"
    source: "`execution_manager.py` 7328, then 7331, reaching 8970, then 8971 into 8972"
  - claim: "The held-protection scan selects on a stamped moment and reads no standing at all"
    source: "`execution_manager.py` 7328, against 9834 into 9835"
---
# What picks a stalled ladder change up again

A change to a ladder's grid that stopped halfway is driven on by a scan over the account's live work, and the scan chooses by the two marks the change leaves.

## What the scan reads

It looks the account up and ends there where the manager holds no such account, then walks a copy of that account's live work.

Work with no phase written, or no context held, is passed over. Both marks have to be there.

## Read twice

The driving the scan calls does nothing where the context is gone, so the context is read once by the scan and once by the driving. The scan's reading is what keeps the driving from being called at all for work that has none.

## Beside it

[The scan over held protection changes](what-picks-a-held-protection-change-up-again.md) selects on a stamped moment and reads no standing at all. The two scans sit in the same module, run from the same tick, and choose their work on unlike grounds — one on marks that say where the work stopped, the other on a moment that says when.

## Related

- [What picks a held protection change up again](what-picks-a-held-protection-change-up-again.md)
- [How a ladder's change moves from one phase to the next](how-a-ladders-change-moves-from-one-phase-to-the-next.md)
- [Which way a ladder's change is given up](which-way-a-ladders-change-is-given-up.md)
