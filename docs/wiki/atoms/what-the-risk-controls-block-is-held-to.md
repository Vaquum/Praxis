---
row: N60-02
baseline: 49aa659
created: 2026-11-08 18:50 UTC
modified: 2026-11-08 18:50 UTC
evidence:
  - claim: "A block left out of the manifest becomes an empty mapping, and so does one written with no value under its key, that substitution standing ahead of the test of its shape"
    source: "`nexus/infrastructure/manifest.py` 350-353, ahead of 355-357"
  - claim: "A block that is not a mapping is refused"
    source: "`nexus/infrastructure/manifest.py` 355-357"
  - claim: "Three named figures are read out of it, and whatever else it holds is passed over"
    source: "`nexus/infrastructure/manifest.py` 359-363"
  - claim: "Each is read by a helper that answers nothing where the key is absent, and the same where the key is there with no value under it"
    source: "`nexus/infrastructure/manifest.py` 299-300"
  - claim: "That helper refuses only what will not convert to a figure, asking nothing about the figure's size or sign"
    source: "`nexus/infrastructure/manifest.py` 303, refusing at 304-306"
---
# What the risk-controls block is held to

[A manifest](the-settings-a-host-is-given.md) may carry a block of limits for the account, and the block is held to little.

## Three ways of saying nothing

A manifest with no such block gets an empty mapping in its place, and so does one whose key is written with no value under it. Leaving the block out, writing it bare, and writing one with nothing in it therefore come to the same thing.

That substitution is made before the shape is tested, so a bare key reaches the test as a mapping. A block holding something that is not a mapping is refused there.

## Three keys, and the rest ignored

Three named figures are read out of it. Whatever else the block holds is passed over without a word, so a limit written under a misspelled key is read by nothing and complained about by nothing.

## What a figure in it is asked

Each is read by a helper that answers nothing where the key is absent, and the same where the key is there with no value under it. Otherwise it converts the value to a figure.

The helper refuses a value the conversion cannot read as a figure, and that is the whole of what it asks. Nothing here asks the figure to be finite or above nought, so a limit that is no real quantity gets past this block — and is refused a step later by [the record the three are handed to](the-limits-that-may-be-left-out.md), which holds each limit that is present to being a finite figure above nought.

## Related

- [The settings a host is given](the-settings-a-host-is-given.md)
- [The limits that may be left out](the-limits-that-may-be-left-out.md)
- [The complaint that names the wrong block](the-complaint-that-names-the-wrong-block.md)
- [What the strategy records refuse](what-the-strategy-records-refuse.md)
