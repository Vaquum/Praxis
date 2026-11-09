---
row: P159-02
baseline: 49aa659
created: 2026-11-16 00:00 UTC
modified: 2026-11-16 00:00 UTC
evidence:
  - claim: "The version the change carries is one past the version standing, and the new pair's name is worked out from it as a retry number"
    source: "`execution_manager.py` 9430, then 9431-9436"
  - claim: "The request is recorded first, and only then is the version put on the bracket and its standing moved to amend-requested"
    source: "`execution_manager.py` 9449, then 9450, then 9451"
  - claim: "A cancel the venue refuses leaves the standing unknown and stamps the moment it became so"
    source: "`execution_manager.py` 9463, then 9464"
  - claim: "A cancel the venue confirms is recorded and the standing moved to cancel-confirmed"
    source: "`execution_manager.py` 9474, then 9480, then 9481"
  - claim: "The new pair's name and its three prices are then parked on the bracket"
    source: "`execution_manager.py` 9483, then 9484, then 9485, then 9486"
  - claim: "The driving reads those four back off the bracket rather than being handed them"
    source: "`execution_manager.py` 9488, read at 9522-9525"
  - claim: "They are cleared on one road only, once the replacement's send has been recorded"
    source: "`execution_manager.py` 9741, then 9744, then 9745, then 9746, then 9747"
---
# What a protection change writes on the bracket

A change to a [protective pair](protection.md) is carried out in steps against the venue, and the bracket is where each step it has reached is written down.

## The version and the name

The version the change carries is one past the version standing, and the new pair's name is worked out from it: the same name the first pair had, with the version as its retry number. So the name a pair rests under says which change put it up.

The request is recorded first, and only then is the version put on the bracket and its standing moved to amend-requested.

## The standing, step by step

A cancel the venue refuses leaves the standing unknown and stamps the moment it became so. A cancel the venue confirms is recorded and the standing moved to cancel-confirmed.

## The four figures

The new pair's name and its three prices are then parked on the bracket. The driving that places the replacement reads those four back off the bracket rather than being handed them, which is what lets [a second pass](what-picks-a-held-protection-change-up-again.md) place the same pair the first pass had planned.

They are cleared on one road only: once the replacement's send has been recorded. Every ending short of that send leaves them standing, so a change that stopped halfway still carries the figures it stopped with.

## Related

- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [What picks a held protection change up again](what-picks-a-held-protection-change-up-again.md)
- [When protection is put up again](when-protection-is-put-up-again.md)
