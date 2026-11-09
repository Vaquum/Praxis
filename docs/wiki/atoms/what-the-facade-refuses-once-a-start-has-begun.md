---
row: P98-01
baseline: 49aa659
created: 2026-11-14 02:30 UTC
modified: 2026-11-14 02:30 UTC
evidence:
  - claim: "The refusal fires where the started flag is set, and equally where a loop is merely held"
    source: "`praxis/trading.py` 363 into 364-368"
  - claim: "It names the method that was called, so the refusal says which setter came too late"
    source: "`praxis/trading.py` 365-366"
  - claim: "Each of the callback setters asks for that refusal before it does anything else"
    source: "`praxis/trading.py` 405, or 442, or 468, or 497"
---
# What the facade refuses once a start has begun

The facade refuses to have its callbacks changed once starting has begun, and the refusal fires earlier than a reader of the started flag would expect.

## The two conditions

The started flag being set. Or a loop merely being held — which a start sets before it finishes.

So the window where a setter is refused opens partway through starting, not at the end of it. A caller that waits for the facade to report itself started has already been locked out for the whole of the starting.

## What the refusal says

The name of the method that was called. So the refusal says which setter came too late, rather than only that something did.

## Where it stands

Each of the callback setters asks for that refusal before it does anything else. None of them does any work first and checks afterwards, so a refused call leaves nothing changed.

## Related

- [How a caller's callback is wrapped](how-a-callers-callback-is-wrapped.md)
