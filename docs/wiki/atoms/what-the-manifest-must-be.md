---
row: N71-05
baseline: 49aa659
created: 2026-11-08 21:14 UTC
modified: 2026-11-08 21:14 UTC
evidence:
  - claim: "The manifest is read from a fixed name under the folder predictions are mounted at, and a path leading to no file warns with the path"
    source: "`nexus/strategy/predict_loop.py` 428, then 429-431"
  - claim: "It is parsed and must be a mapping, a parsed value of any other shape warning with the path"
    source: "`nexus/strategy/predict_loop.py` 433-434, then 436-438"
  - claim: "Nothing here catches a failure of the parsing, so a file that is not well-formed leaves this step by raising"
    source: "`nexus/strategy/predict_loop.py` 434, standing in no attempt"
  - claim: "That raising is logged by the loop's own turn and handed on by a turn asked for by hand"
    source: "`nexus/strategy/predict_loop.py` 307-316, against 282"
  - claim: "Its moment must be text, a value of any other kind warning without naming what arrived"
    source: "`nexus/strategy/predict_loop.py` 445-448"
  - claim: "A moment ending in the universal-time letter has that letter swapped for the offset spelled out before it is parsed"
    source: "`nexus/strategy/predict_loop.py` 450"
  - claim: "A moment parsed with no zone is taken as universal time, and one with a zone is moved to it"
    source: "`nexus/strategy/predict_loop.py` 452-453, then 455"
  - claim: "A series the manifest does not name warns, and an entry whose path is not text or is empty warns, each naming the series"
    source: "`nexus/strategy/predict_loop.py` 374-380, then 382-388"
---
# What the manifest must be

Every turn of [the prediction loop](which-prediction-row-is-used.md) begins by reading one file that says where the predictions are.

## Finding it

A fixed name under the folder predictions are mounted at. A path leading to no file warns with the path, and the turn ends.

## Reading it

It is parsed and must be a mapping. A parsed value of any other shape warns with the path.

Nothing here catches a failure of the parsing itself, so a file that is not well-formed leaves this step by raising. What becomes of that raising depends on the road: the loop's own turn logs it and goes on to the next pairing, while a turn asked for by hand hands it to the caller.

## Its moment

The moment the manifest was made must be text. A value of any other kind warns — without naming what arrived, which is the one complaint here that does not.

A moment ending in the universal-time letter has that letter swapped for the offset spelled out before parsing. One parsed with no zone at all is taken as universal time; one with a zone is moved to it.

## The entry for a series

A series the manifest does not name warns. An entry whose path is text with nothing in it warns, and so does one whose path is of any other kind. Each names the series, so a reader learns which binding went unserved.

## Related

- [Which prediction row is used](which-prediction-row-is-used.md)
- [Starting the loop, and one turn by hand](starting-the-loop-and-one-turn-by-hand.md)
