---
row: P140-02
baseline: 49aa659
created: 2026-11-09 10:57 UTC
modified: 2026-11-09 10:57 UTC
evidence:
  - claim: "Whether the account has fail-stopped is checked before the append"
    source: "`execution_manager.py` 3229 into 3230-3231"
  - claim: "The event is appended to the record, and the same check is made again afterwards"
    source: "`execution_manager.py` 3233, then 3235 into 3236-3237"
  - claim: "An append that answers with no sequence answers nothing at all"
    source: "`execution_manager.py` 3239 into 3240"
  - claim: "What the manager now holds under that account's name is compared against the account in hand by identity"
    source: "`execution_manager.py` 3242 into 3243-3247"
  - claim: "That refusal says the event is durable and will project when the record is read back"
    source: "`execution_manager.py` 3243-3247"
  - claim: "The projection is wrapped, the interruption a cancelled task raises is passed straight on, and any other failure marks the account fail-stopped, is reported, and is passed on too"
    source: "`execution_manager.py` 3249-3250, then 3251 into 3252, or 3253 into 3254-3261"
  - claim: "Only past all of that is the sequence answered"
    source: "`execution_manager.py` 3263"
---
# The two checks around an append

Appending an event and projecting it are one step, and the same question is asked on both sides of the append because the append is awaited.

## The question asked twice

Whether the account has fail-stopped, checked before the append and again after it. The append is awaited, so an account can fail-stop while it is in progress — and the second check is the only thing that sees that.

## The account compared by identity

What the manager now holds under that account's name is compared against the account in hand, by identity rather than by name.

An account unregistered and registered again during the append is a different object under the same name, and is refused. The refusal says what matters: the event is already durable, and it will project when the record is read back.

So an event admitted across an account's departure is kept rather than lost, and simply not projected into a runtime that has gone.

## The projection wrapped

The interruption a cancelled task raises is passed straight on, untouched. Any other failure marks the account fail-stopped, is reported, and is passed on as well.

So a projection that fails takes the account out of service rather than leaving it holding a record it has not applied. Only past all of that is the sequence answered.

## Related

- [What admitting an event refuses](what-admitting-an-event-refuses.md)
- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
- [The event spine](the-event-spine.md)
