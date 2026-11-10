---
row: P146-01
baseline: 49aa659
created: 2026-11-09 11:22 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "An account the manager does not hold ends the pass at once"
    source: "`execution_manager.py` 2220, then 2221 into 2222"
  - claim: "One walk over the same history gathers the accepted commands, the scheme starts, the submitted intents and the names their orders were given"
    source: "`execution_manager.py` 2232, then 2233 into 2234, or 2235 into 2236, or 2237 into 2238-2239"
  - claim: "A command is counted as finished where a send of its order answered either way, found through the name that order was given"
    source: "`execution_manager.py` 2240 into 2241, then 2242 into 2243"
  - claim: "It is counted as finished again where an outcome of a terminal status was recorded for it"
    source: "`execution_manager.py` 2244-2247 into 2248"
  - claim: "The first kind is an accepted command with no intent, unfinished and beginning no scheme"
    source: "`execution_manager.py` 2250, then 2251, then 2252, then 2254-2259"
  - claim: "The second is a command whose order was intended, unfinished and beginning no scheme"
    source: "`execution_manager.py` 2260-2263"
  - claim: "The third is a scheme start with no terminal outcome that the resumes did not rebuild"
    source: "`execution_manager.py` 2264-2268"
  - claim: "The first kind is refused one at a time"
    source: "`execution_manager.py` 2270, then 2271-2275"
---
# The three kinds of orphan a boot finds

An orphan is a command the record shows starting and never shows finishing, and a boot sorts them into three kinds by what the record holds about each.

## What one walk gathers

The accepted commands with their trades. The scheme starts, the first for each command. The submitted intents, and the name each intent's order was given.

A command counts as finished two ways: a send of its order answered, either way — found through the name that order was given — or an outcome of a terminal status was recorded for it.

So a send that failed counts as finishing a command just as a send that succeeded does. What makes an orphan is silence, not failure.

## The three kinds

An accepted command with no intent at all, unfinished, beginning no scheme. Its order was never even meant.

A command whose order was intended, unfinished, beginning no scheme. Its order may have gone out.

A scheme start with no terminal outcome that [the resumes](what-stops-a-scheme-being-resumed.md) did not rebuild. Its scheme was running and could not be brought back.

## Why each test excludes the schemes

The first two kinds both exclude commands that began a scheme, because a scheme's own ending is the third kind's business. A command would otherwise be refused as an orphan and ended as a scheme both.

## What becomes of the first

Each is refused, one at a time, carrying the trade the record named for it.

## Related

- [What stops a scheme being resumed](what-stops-a-scheme-being-resumed.md)
- [What a boot ends an unfinished scheme with](what-a-boot-ends-an-unfinished-scheme-with.md)
- [What a restart puts back](what-a-restart-puts-back.md)
