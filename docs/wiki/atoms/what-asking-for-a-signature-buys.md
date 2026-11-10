---
row: P89-02
baseline: 49aa659
created: 2026-11-09 07:07 UTC
modified: 2026-11-09 07:07 UTC
evidence:
  - claim: "Four endpoints demand a signed caller before anything else, and the name they get back is the account"
    source: "`server.py` 289, and 300, and 307, and 271"
  - claim: "Two of them answer an empty list and nothing more"
    source: "`server.py` 302, and 309"
  - claim: "One raises a not-found carrying a venue-shaped body of its own"
    source: "`server.py` 291-294 into 295"
  - claim: "The account's balances are asked of the ledger under the name the signature gave"
    source: "`server.py` 272, then 274-275"
  - claim: "A name the ledger does not hold becomes an unauthorized rather than a not-found"
    source: "`server.py` 276 into 277"
  - claim: "Both balances are answered as text with nothing locked against either"
    source: "`server.py` 279-284"
---
# What asking for a signature buys

Four of binsim's endpoints demand a signed caller before anything else, and what the demand buys is a name: the account the caller is asking about.

## The three that answer nothing much

Two answer an empty list and nothing more. One raises a not-found carrying a venue-shaped body of its own, so a caller asking after a single order is told the venue has no such thing in the venue's own words.

All three demand the signature first, and so a caller with no signature learns nothing about whether the thing they asked for exists.

## The one that uses the name

The account's balances are asked of the ledger under the name the signature gave. A name the ledger does not hold becomes an unauthorized rather than a not-found.

So an unknown account and an unsigned request come back the same way. A caller cannot tell a bad signature from a good signature for an account binsim has never heard of.

## What a balance looks like

Both are answered as text, with nothing locked against either. Binsim reports no held amounts at all, so the locked figure is a constant: it says that binsim keeps no such tally, and says the same whatever the account holds.

## Related

- [What binsim's read endpoints answer](what-binsims-read-endpoints-answer.md)
