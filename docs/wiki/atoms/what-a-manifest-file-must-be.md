---
row: N60-03
baseline: 49aa659
created: 2026-11-12 18:00 UTC
modified: 2026-11-12 18:00 UTC
evidence:
  - claim: "A path that is not a file refuses the reading with a kind of failure no refusal written here uses"
    source: "`nexus/infrastructure/manifest.py` 382-384, every refusal written here raising at 389-391 onwards"
  - claim: "A folder carrying the manifest's name is turned away by that same test"
    source: "`nexus/infrastructure/manifest.py` 382, which asks for a file rather than for anything at that path"
  - claim: "The file is opened under UTF-8, and the bytes are decoded under it when the reader reads them"
    source: "`nexus/infrastructure/manifest.py` 386, read at 387"
  - claim: "Its text is read by the YAML reader in the form that builds only plain values, which refuses a tag asking for an object to be made"
    source: "`nexus/infrastructure/manifest.py` 387"
  - claim: "What the reader gives back must be a mapping, so a file holding a list or a bare value is refused before any field is looked for"
    source: "`nexus/infrastructure/manifest.py` 389-391"
---
# What a manifest file must be

Before any field of [a manifest](the-settings-a-host-is-given.md) is looked for, the file itself is held to three things.

## A file at that path

The path must be a file. A folder carrying the manifest's name fails here, because what is asked is for a file rather than for anything at all at that path.

This is the one refusal written here that raises a missing-file failure; every other one written here raises the ordinary kind. A caller sorting failures by kind sees a third sort as well, since a malformed file comes back as the reader's own failure rather than as a refusal of this module's.

## Bytes that decode

The file is opened under UTF-8. The bytes are decoded under that when the reader reads them, so a byte that UTF-8 has no reading for fails there, with a complaint about a byte rather than about anything the manifest is meant to say. A file saved under another encoding whose bytes happen to be valid UTF-8 — anything written in plain ASCII — passes.

## A mapping

The text is handed to the YAML reader in the form that builds only plain values. A file carrying a tag that asks for an object to be made is refused by the reader on that tag.

What comes back must be a mapping. A file holding a list, or a single bare value, or nothing at all, is refused there — before any field is looked for, and so with a complaint about the shape of the whole file rather than about a field.

## Related

- [The settings a host is given](the-settings-a-host-is-given.md)
- [The two refusals the manifest record adds](the-two-refusals-the-manifest-record-adds.md)
- [What a strategy's file must be](what-a-strategys-file-must-be.md)
