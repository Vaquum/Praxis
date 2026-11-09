---
row: P32-01
baseline: 49aa659
created: 2026-11-08 16:29 UTC
modified: 2026-11-08 16:29 UTC
evidence:
  - claim: "A record read as text must be valid JSON, and text that will not parse is refused as malformed"
    source: "`secret_store.py` 130-134"
  - claim: "A record that parses but is not an object is refused the same way"
    source: "`secret_store.py` 157-159"
  - claim: "The key and the secret must each be text"
    source: "`secret_store.py` 163-170"
  - claim: "Each must also be true, so an empty one is refused and one of blank space alone is kept"
    source: "`secret_store.py` 166-167"
  - claim: "Two keys are read and two are carried, so anything else the record holds is ignored"
    source: "`secret_store.py` 161-162 into 172"
  - claim: "The road that is handed credentials directly reads no record at all, keeping what it was given"
    source: "`secret_store.py` 229 and 247"
---
# What a credential record must hold

A record read as text — by [the keyring road or the file road](where-credentials-come-from.md) — must pass the same checks before it becomes credentials.

## The shape

Valid JSON, and a JSON object. Text that will not parse is refused as malformed, and so is a list, a number or a string where an object was expected.

## The two fields

A key and a secret, each of them text. A record whose key is a number is refused even though the field is there.

Each must also be true. An empty key is refused; a key of blank space alone is kept and used, since what is asked is truth rather than content. That is [the same escape](the-escape-in-the-shared-check-for-a-name.md) this side leaves open in its records' names, in a fifth place.

## What is ignored

Two keys are read and two are carried. Anything else in the record — a label, a note, a third field left over from an older shape — passes through unexamined and is dropped.

## The road with no record

The third road is handed credentials already made, one per account, and keeps them as it was given them. Nothing above happens on it: there is no text to parse and no record to check.

## Related

- [Where credentials come from](where-credentials-come-from.md)
- [Which accounts are refused](which-accounts-are-refused.md)
- [The records a file of credentials is read into](the-records-a-file-of-credentials-is-read-into.md)
