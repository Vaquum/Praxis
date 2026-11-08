---
row: P68-02
baseline: 49aa659
created: 2026-11-13 01:00 UTC
modified: 2026-11-13 01:00 UTC
evidence:
  - claim: "An address beginning with the secured form is allowed outright"
    source: "`binance_ws.py` 167"
  - claim: "An address beginning with the plain form is allowed only where the setting naming a simulator holds something once trimmed"
    source: "`binance_ws.py` 166, then 168"
  - claim: "A setting holding only space counts as holding nothing, so it opens no allowance"
    source: "`binance_ws.py` 166, trimming before the truth of it is read"
  - claim: "Anything else is refused with a complaint naming the address as written"
    source: "`binance_ws.py` 170-172"
  - claim: "The test reads the beginning of the address alone, so nothing asks what follows the form"
    source: "`binance_ws.py` 167, and 168"
  - claim: "The address is taken from the adapter rather than read here, and the check stands before the credentials are fetched or any connection opened"
    source: "`binance_ws.py` 158, with 170-172 ahead of 174 and 177"
  - claim: "It stands after the tearing down of whatever the stream already held, so a refused address is met with nothing in hand"
    source: "`binance_ws.py` 152-156 ahead of 170-172"
---
# The address the stream will accept

Before [the venue feed](the-venue-feed.md) opens anything, the address it was given is held to one of two forms.

## The secured form

An address beginning with the secured form is allowed outright. That is the form a real venue uses, whether the live one or its practice copy.

## The plain form, conditionally

An address beginning with the plain form is allowed only where the setting naming a simulator holds something.

That setting is trimmed before its truth is read, so one holding only space counts as holding nothing and opens no allowance. A host configured with a blank setting therefore cannot reach an unsecured address by accident.

## Anything else

Refused, with a complaint naming the address exactly as written.

## What the test does not ask

It reads the beginning of the address and nothing more. What follows the form — the host, the port, the path — is not looked at here, so an address of the right form pointing anywhere at all passes.

## Where it stands

The address comes from the adapter rather than being read here. The check runs before the credentials are fetched and before any connection is opened.

It runs after [the tearing down of whatever the stream already held](what-setting-up-tears-down-first.md), though. So a wrong address costs the connection the stream had, not merely the complaint.

## Related

- [The venue feed](the-venue-feed.md)
- [What opening the stream does and does not do](what-opening-the-stream-does-and-does-not-do.md)
