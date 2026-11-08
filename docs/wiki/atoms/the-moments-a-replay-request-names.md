---
row: P14-01
baseline: 49aa659
created: 2026-11-10 13:00 UTC
modified: 2026-11-10 13:00 UTC
evidence:
  - claim: "A moment ending in a capital Z is rewritten to a zero offset, and any other text is handed to the reader as it stands"
    source: "`replay_api.py` 260-262"
  - claim: "So a moment with no zone is kept, a date on its own is taken as midnight without one, and a lower-case z is refused"
    source: "`replay_api.py` 260-262"
  - claim: "One edge carrying a zone and one not raises at the comparison between them, rather than reaching the refusal that comparison is written for"
    source: "`replay_api.py` 207, against the refusal at 208-209"
  - claim: "Two edges both without a zone are refused where the frames are read"
    source: "`load_replay_bars.py` 58-60, reached from `replay_api.py` 211-218"
  - claim: "A failure of any of those kinds comes back as a bad request carrying the raiser's own words"
    source: "`replay_api.py` 129-130, around the call at 127-128"
---
# The moments a replay request names

A [replay request](asking-for-a-replay-from-outside.md) names the two edges of the window it wants, each as text in the standard written form.

## What the service does to them

One letter: a trailing capital Z becomes an explicit offset of zero. Everything else is handed to the standard reader as it stands.

So a lower-case z is refused, since the rewriting never reaches it. A moment with no zone at all is kept as written, and a date on its own — no time, no zone — is taken as midnight.

## Which refusal catches a missing zone

An edge without a zone is refused, but where depends on the other edge.

Where one edge carries a zone and the other does not, comparing the two for order is itself what raises: the pair never reaches the test that comparison was written for, nor [the frames](where-a-replays-bars-come-from.md).

Where neither carries a zone, the two compare without complaint, and the refusal comes later, from the reading of the frames.

## What the asker is told

Each of these comes back as a bad request carrying the words of whatever raised. The asker reads the complaint of the comparison, or of the standard reader, or of the frame loader — not one message the service writes for the field.

## Related

- [Asking for a replay from outside](asking-for-a-replay-from-outside.md)
- [Where a replay's bars come from](where-a-replays-bars-come-from.md)
- [What stopping the replay listener does](what-stopping-the-replay-listener-does.md)
