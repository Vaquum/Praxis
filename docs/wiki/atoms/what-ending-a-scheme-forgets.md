---
row: P153-02
baseline: 49aa659
created: 2026-11-15 21:00 UTC
modified: 2026-11-15 21:00 UTC
evidence:
  - claim: "One moment is taken and carried by the outcome, any closing record, and the outcome written down"
    source: "`execution_manager.py` 8405, used at 8422, and 8435, and 8444"
  - claim: "The average price is the money over the amount, and nothing where nothing filled"
    source: "`execution_manager.py` 8407-8409"
  - claim: "The outcome is built carrying the command's whole amount as its target"
    source: "`execution_manager.py` 8411-8424, the target at 8416"
  - claim: "The command is marked terminal and then dropped, and any abort noted against it dropped too"
    source: "`execution_manager.py` 8426, then 8427, then 8428"
  - claim: "A scheme that filled something and closes its position has a closing record written and projected"
    source: "`execution_manager.py` 8430-8432 into 8433-8438, then 8439, then 8440"
  - claim: "The outcome is then written down under that same moment"
    source: "`execution_manager.py` 8442-8449"
---
# What ending a scheme forgets

Ending a fed-out order writes its outcome and takes the command out of three places, and the order of those two things is what a later reader sees.

## The one moment

Taken once and carried by the outcome handed on, by any closing record, and by the outcome written down. So all three agree on when the scheme ended, whatever the clock did in between.

## What the outcome says

The command's whole amount as its target, whatever was actually filled. The average price is the money over the amount, and nothing at all where nothing filled.

## The three forgettings

The command is marked terminal, then dropped from the held commands, and any abort noted against it dropped as well.

All three happen before the outcome is written down. So between the forgetting and the write, the command is terminal and held nowhere — and anything reading the held commands in that window finds nothing for a command whose outcome has not yet been recorded.

## The closing record

A scheme that filled something and closes its position has a closing record written and projected, before the outcome. So the position's closing is in the record ahead of the outcome that caused it.

## Related

- [What a boot ends an unfinished scheme with](what-a-boot-ends-an-unfinished-scheme-with.md)
- [Whether a fill closes a position](whether-a-fill-closes-a-position.md)
- [Which child news a scheme acts on](which-child-news-a-scheme-acts-on.md)
