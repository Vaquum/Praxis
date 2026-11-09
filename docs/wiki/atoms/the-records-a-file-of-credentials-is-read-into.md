---
row: P32-02
baseline: 49aa659
created: 2026-11-08 16:29 UTC
modified: 2026-11-08 16:29 UTC
evidence:
  - claim: "The file road keeps what it decoded, and answers from that where it has it"
    source: "`secret_store.py` 288-289, kept at 311"
  - claim: "What it kept is set only after the whole file has been read and decoded without failing"
    source: "`secret_store.py` 311 standing after 291-310"
  - claim: "So a read that failed is made again at the next question, and a file put right is picked up"
    source: "`secret_store.py` 288 finding nothing kept, then 292"
  - claim: "A read that succeeded is not made again, so a file changed afterwards is not looked at"
    source: "`secret_store.py` 288-289 answering from what was kept"
  - claim: "The decoding walks the file's own accounts rather than the one asked for, and stops at the first record it refuses"
    source: "`secret_store.py` 307-310 into 157-159, or into 163-170"
---
# The records a file of credentials is read into

[The road that reads credentials from a file](where-credentials-come-from.md) keeps what it decoded and answers from that.

## What it keeps, and when

The first question causes the file to be read, parsed and decoded. What that produced is kept — but only once the whole file has gone through without a failure.

So a read that failed keeps nothing, and the next question reads the file again. A file put right after a bad start is picked up by the same store, with no restart needed.

A read that succeeded is never made again. A file changed on disk afterwards is not looked at, so a credential rotated under a running host reaches nothing until the host is started over.

## Which accounts the decoding walks

The decoding walks the accounts the file holds rather than the one that was asked for, and stops at the first record it refuses.

So a file holding one bad record refuses the first question asked of it, whatever account that question was about — and the accounts whose records are sound are refused along with it, until the bad one is fixed.

## Related

- [Where credentials come from](where-credentials-come-from.md)
- [What a credential record must hold](what-a-credential-record-must-hold.md)
- [Which accounts are refused](which-accounts-are-refused.md)
