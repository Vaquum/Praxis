---
row: P144-01
baseline: 49aa659
created: 2026-11-09 11:13 UTC
modified: 2026-11-09 13:45 UTC
evidence:
  - claim: "Both list names a bracket might be protected by are gathered, the one it holds and any replacement still owing, with an absent name left out"
    source: "`execution_manager.py` 7419-7426, the two running totals started at 7427, then 7428"
  - claim: "Each is asked after at the venue, its list first and then every leg of that list, the legs' fills summed"
    source: "`execution_manager.py` 7430, then 7429, then 7431-7433, then 7434, then 7435, then 7436-7438, then 7439"
  - claim: "A list the venue does not know is passed over and the walk goes on"
    source: "`execution_manager.py` 7440 into 7441"
  - claim: "Any other venue failure abandons the whole resolving"
    source: "`execution_manager.py` 7442 into 7443"
  - claim: "Each candidate's legs are then reconciled against what the venue said, and a failure to reconcile abandons the resolving too"
    source: "`execution_manager.py` 7445-7447, then 7448, then 7449-7451, then 7452-7456, then 7457 into 7458"
  - claim: "What the venue said and what was projected locally are accumulated across the candidates"
    source: "`execution_manager.py` 7460, then 7461"
  - claim: "A position closed by a protective fill has the exit's outcome built as filled, from the admitted totals, where that command exists and admitted anything"
    source: "`execution_manager.py` 7465-7468, then 7469 into 7470-7478"
  - claim: "The bracket is then dropped, and a remainder still standing is sent to be remediated as naked"
    source: "`execution_manager.py` 7480, then 7486, against 7488-7495"
---
# What the venue is asked when no protection is working

When the venue confirms that neither of a bracket's candidate lists is working, the outcome is settled by asking the venue what those lists actually filled rather than by reading what Praxis projected.

## The two candidates

The list the bracket holds, and any replacement still owing. An absent name is left out, so a bracket mid-amend offers two and one not amending offers one.

## What each is asked

Its list, and then every leg of that list, with the legs' fills summed. A list the venue does not know is passed over and the walk goes on to the next.

Any other venue failure abandons the whole resolving — so a resolution is attempted only where every candidate the venue knows about answered.

## The reconciling

Each candidate's legs are reconciled against what the venue said, and a failure to reconcile abandons the resolving as well. Only past that are the venue's figure and the local projection accumulated.

So this routine has three ways of giving up and each leaves the bracket exactly as it was, for a later pass to try again.

## The two endings

A position closed by a protective fill: the exit's outcome is built as filled from [the admitted totals](two-ways-of-asking-what-a-command-filled.md), where that command exists and admitted anything, and the bracket is dropped.

A remainder still standing: the position is genuinely unprotected, and it is sent to be remediated as such.

## Related

- [The remainder subtraction written twice](the-remainder-subtraction-written-twice.md)
- [What a resumed bracket's protection is taken from](what-a-resumed-brackets-protection-is-taken-from.md)
- [Protection](protection.md)
