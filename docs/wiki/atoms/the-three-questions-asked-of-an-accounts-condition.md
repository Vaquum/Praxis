---
row: P139-02
baseline: 49aa659
created: 2026-11-15 14:00 UTC
modified: 2026-11-15 14:00 UTC
evidence:
  - claim: "Whether an account has fail-stopped is answered true only where the account is registered and carries that mark"
    source: "`execution_manager.py` 3324, then 3326"
  - claim: "Whether it can send orders is answered false where it is unregistered, and otherwise only where it is neither reconciling nor fail-stopped"
    source: "`execution_manager.py` 3344, then 3345 into 3346, or 3348"
  - claim: "A reconciling account is answered false by both, the one because it is reconciling and the other because it carries no fail-stop mark"
    source: "`execution_manager.py` 3348, against 3326"
  - claim: "Whether anything of the account's still awaits handling is true where an admission is in flight or an outside event is queued"
    source: "`execution_manager.py` 2861-2864"
  - claim: "It answers false for an unregistered account, so a drained account and an absent one answer alike"
    source: "`execution_manager.py` 2857, then 2858 into 2859"
  - claim: "Asking for a protection sweep sets a flag on the account and answers nothing, doing nothing at all where the account is unregistered"
    source: "`execution_manager.py` 3301, then 3302 into 3303, or 3305"
---
# The three questions asked of an account's condition

Three questions are asked about what an account can do rather than about what it holds, and the three draw their lines in different places.

## Whether it has fail-stopped

True only where the account is registered and carries that mark. An unregistered account answers false, the same as a registered and healthy one.

## Whether it can send orders

False where the account is unregistered. Otherwise true only where it is neither reconciling nor fail-stopped.

A reconciling account is therefore answered false by both: by this one because it is reconciling, and by the first because it carries no fail-stop mark. The two answers agree and the reasons do not, so only a caller asking both can tell [a gate that will lift](when-an-account-is-reconciling-or-poisoned.md) from one that will not.

## Whether anything still awaits handling

True where an admission is in flight or an outside event is queued. An unregistered account answers false, so an account fully drained and an account that was never there answer alike.

## The one that is not a question

Asking for a protection sweep sets a flag on the account and answers nothing at all. Where the account is unregistered it does nothing, and a caller cannot tell that from a sweep duly asked for.

## Related

- [What the manager tells you about an unknown account](what-the-manager-tells-you-about-an-unknown-account.md)
- [Protection](protection.md)
- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
