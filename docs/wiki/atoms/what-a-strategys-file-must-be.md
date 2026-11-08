---
row: N59-03
baseline: 49aa659
created: 2026-11-12 16:30 UTC
modified: 2026-11-12 16:30 UTC
evidence:
  - claim: "The files are checked once the whole manifest has been built and every other check has passed"
    source: "`nexus/infrastructure/manifest.py` 559-569, then 571"
  - claim: "The folder they are resolved against is the one the manifest file itself sits in"
    source: "`nexus/infrastructure/manifest.py` 571, resolved at 587"
  - claim: "A path written from the root of the disk is refused"
    source: "`nexus/infrastructure/manifest.py` 592-594"
  - claim: "A path that resolves outside that folder is refused, which is what turns away one climbing out through its parent"
    source: "`nexus/infrastructure/manifest.py` 596-602"
  - claim: "The file must be there, and a folder with the right name does not count"
    source: "`nexus/infrastructure/manifest.py` 604-606"
  - claim: "Its bytes must decode as UTF-8, and only then must the text parse as Python"
    source: "`nexus/infrastructure/manifest.py` 609, the decoding asked for inside the same statement that parses"
  - claim: "Nothing beyond parsing is asked of what the text holds"
    source: "`nexus/infrastructure/manifest.py` 608-612, the only reading of the text at 609"
---
# What a strategy's file must be

Each strategy in [a manifest](the-settings-a-host-is-given.md) names a file, and that file is held to five things.

## When the holding happens

Once the manifest has been built whole and every other check has passed. So a manifest whose shares are wrong is refused for the shares, with no file ever opened; and a manifest that is right in every other way is refused for a file that is missing.

## Where it is looked for

In the folder the manifest file itself sits in, resolved to a real path first.

## The five

It must be written as a path relative to that folder, so one written from the root of the disk is refused.

Resolved against the folder, it must still lie inside it. That is the test that turns away a path climbing out through its parent, and it is made on the resolved path rather than on the words, so the climbing cannot be hidden by a longer route.

It must be a file that is there. A folder carrying the right name does not pass.

Its bytes must decode as UTF-8. That is asked for in the same breath as the parsing and comes first, so a file written in another encoding fails here even where it declares that encoding in the way Python itself accepts.

Its text must then parse as Python.

## What is not asked

Decoding and parsing are the whole of what the text is held to. Nothing here looks for a class, a name, or anything a strategy is supposed to provide — [what the loader asks of what it found](what-the-loader-asks-of-what-it-found.md) comes later, when the file is run.

## Related

- [The settings a host is given](the-settings-a-host-is-given.md)
- [The order a strategy entry is read in](the-order-a-strategy-entry-is-read-in.md)
- [What the loader asks of what it found](what-the-loader-asks-of-what-it-found.md)
