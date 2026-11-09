---
row: P109-01
baseline: 49aa659
created: 2026-11-14 08:00 UTC
modified: 2026-11-14 08:00 UTC
evidence:
  - claim: "Signing works on a copy of what it was given, so the caller's own parameters are left as they were"
    source: "`binance_adapter.py` 528"
  - claim: "A moment is added to that copy, read off the clock as whole milliseconds"
    source: "`binance_adapter.py` 529"
  - claim: "The copy is then laid out as a query, and the seal is taken over exactly that text"
    source: "`binance_adapter.py` 530, then 531-535"
  - claim: "The seal is appended to the same text, so what is sent and what was sealed agree by construction"
    source: "`binance_adapter.py` 536"
  - claim: "A session is refused outright where the adapter has been closed"
    source: "`binance_adapter.py` 499 into 500-501"
  - claim: "One is made where none is held or the one held is closed, and the one held is answered otherwise"
    source: "`binance_adapter.py` 503 into 504, then 505"
  - claim: "Credentials for an account that was never registered raise as a failure to authenticate, with the original cause dropped"
    source: "`binance_adapter.py` 479-480 into 481, then 482-483"
---
# What signing a request adds

Signing adds a moment and a seal to a request, and it does both on a copy so the caller's parameters are untouched.

## The copy and the moment

Signing works on a copy of what it was given. A moment is added to that copy, read off the clock as whole milliseconds.

So the caller cannot tell from its own parameters that a moment was added, and two signings of the same parameters differ by their moments.

## The seal

The copy is laid out as a query, and the seal is taken over exactly that text. The seal is then appended to the same text.

So what is sent and what was sealed agree by construction rather than by care: the text is built once, sealed, and extended. There is no second rendering that could differ from the first.

## The session it will go on

Refused outright where the adapter has been closed. Otherwise one is made where none is held or the one held is closed, and the one held is answered.

So a closed adapter refuses to build a session rather than building one nobody tracks — which is what [closing arranges by setting its mark first](what-closing-the-adapter-does-first.md).

## The credentials

For an account that was never registered, they raise as a failure to authenticate, with the original cause dropped. So the raised error names the account and says nothing about the lookup that failed.

## Related

- [What closing the adapter does first](what-closing-the-adapter-does-first.md)
