---
row: P61-04
baseline: 49aa659
created: 2026-11-08 19:05 UTC
modified: 2026-11-08 19:05 UTC
evidence:
  - claim: "A revision of a protective pair must be a whole number at or above one, with a true-or-false refused by a test standing beside the one for kind"
    source: "`events.py` 91-93, the floor declared at 76"
  - claim: "A count given under a field's own name is held to the same, by a second check written the same way"
    source: "`events.py` 1326-1328"
  - claim: "A run of figures is held entry by entry to being a finite figure of the exact kind above nought"
    source: "`events.py` 1316-1319"
  - claim: "A run with nothing in it passes that check, the walk having no entry to weigh"
    source: "`events.py` 1316, the test standing inside the walk"
  - claim: "A replanned scheme refuses a run of sizes with nothing in it by a test of its own, and the ladder's runs carry no such test"
    source: "`events.py` 433-435, against the ladder's checks at 1364-1377 and 1409-1431"
  - claim: "Two records ask a field to be one of the named ones by matching it against a frozen set holding those names' values"
    source: "`events.py` 1639-1642, and 1674-1677, the sets built at 77-78"
  - claim: "The named things are declared plainly rather than as words, so one of them does not match its own value and is refused by those two tests, while the bare word passes"
    source: "`praxis/core/domain/enums.py` 41-46, and 49-54, matched against at `events.py` 1639 and 1674"
  - claim: "One record asks the same question by kind, which the named thing passes and the bare word fails, the opposite way round from the other two"
    source: "`events.py` 1963-1965"
  - claim: "A ladder's phase is held to two words written out where it is tested"
    source: "`events.py` 1525-1527"
---
# What the shared checks pass over

Three checks are written once and used across [the forty-two records](what-every-event-is-held-to.md), and each is narrower than its name suggests.

## The two counts

A revision of a protective pair must be a whole number standing at or above one. A true-or-false is refused by a test beside the one for kind, which is there because a true-or-false counts as a whole number.

A count given under a field's own name is held to the same, by a second check written the same way.

## A run of figures

A run is walked and each entry held to being a finite figure of the exact kind above nought.

A run with nothing in it passes. The test stands inside the walk, so with no entry to weigh there is nothing to refuse.

A replanned scheme refuses an empty run of sizes by a test of its own. The ladder's runs carry no such test, so an empty ladder is accepted where an empty replan is not.

## Three ways of asking for a named value

Two records match the field against a frozen set holding the named values. The named things themselves are declared plainly, so a named thing is a separate value from the word it holds and matches nothing in that set. The bare word matches; the named thing is refused.

One record asks by kind. There the named thing passes and the bare word is refused — the opposite way round.

A ladder's phase is asked a third way, against two words written out where the test is made.

So one question is answered three ways, and a caller handing over the named things is right in one place and refused in two.

## Related

- [What every event is held to](what-every-event-is-held-to.md)
- [The grounds a figure is weighed on](the-grounds-a-figure-is-weighed-on.md)
