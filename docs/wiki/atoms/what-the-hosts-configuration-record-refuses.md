---
row: P43-01
baseline: 49aa659
created: 2026-11-12 00:30 UTC
modified: 2026-11-12 00:30 UTC
evidence:
  - claim: "The three venue addresses are each tested for truth alone, so an address of blank space is kept"
    source: "`trading_config.py` 119-121, or 123-125, or 127-129"
  - claim: "Three spans are each refused at or below nought by comparison, nothing being asked of their kind"
    source: "`trading_config.py` 131-133, or 135-137, or 139-144"
  - claim: "So a span that is a number with no value — not-a-number — is kept, the comparison answering false for it, where a span that is no number at all raises from the comparison"
    source: "`trading_config.py` 131 letting the first by and raising on the second"
  - claim: "The credentials mapping's keys must be text with something left once trimmed"
    source: "`trading_config.py` 148-150"
  - claim: "Its values must be of the credentials kind, and each key and secret is tested for truth alone"
    source: "`trading_config.py` 152-154, or 156-161"
  - claim: "The ways of working it is given must each be a way of working"
    source: "`trading_config.py` 169-172"
---
# What the host's configuration record refuses

The record a host's settings are gathered into checks them again once they reach it, after [the reading that refuses most of them](which-settings-are-refused.md).

## The addresses

Three: where the venue answers, where it streams, and where it takes orders over that stream. Each is tested for its truth and nothing more, so an address of blank space alone is kept and carried.

## The spans

A span to wait while stopping, a span between reconciliations, and a deadline for putting protection back. Each is refused at or below nought, by comparison.

Nothing is asked of their kind, and the comparison answers for them in two ways. A number with no value — not-a-number — passes, the comparison answering false, and is kept. Something that is no number at all, text or nothing, makes the comparison itself raise.

## The credentials

Each key in the mapping must be text with something left once the blank space is trimmed off — the trimming testing it only, so a padded account name is kept as it arrived.

Each value must be of [the credentials kind](where-credentials-come-from.md), and each key and secret within it is tested for truth. A secret of blank space alone therefore passes here, as it does [where the store reads one](what-a-credential-record-must-hold.md).

## The ways of working

Each name given must be a way of working. [What becomes of the list afterwards](what-the-configuration-record-holds-afterwards.md) is its own subject.

## Related

- [Which settings are refused](which-settings-are-refused.md)
- [What the configuration record holds afterwards](what-the-configuration-record-holds-afterwards.md)
- [What a credential record must hold](what-a-credential-record-must-hold.md)
