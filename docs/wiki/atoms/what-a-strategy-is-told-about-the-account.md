---
row: P121-02
baseline: 49aa659
created: 2026-11-09 09:32 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "With no state or no settings to read, a strategy is told of no positions, no money and a halted mode"
    source: "`launcher.py` 2497 into 2498-2502, asked through 4166"
  - claim: "A strategy the settings do not name is told the same"
    source: "`launcher.py` 2504, then 2509 into 2510-2514"
  - claim: "Otherwise its money is the pool at its share, less what it has deployed, held at nothing at the least"
    source: "`launcher.py` 2516, then 2517, then 2518"
  - claim: "The positions are copied under the lock where one was given, and without it where none was"
    source: "`launcher.py` 2520 into 2521-2522, or 2524"
  - claim: "Only after that copy are they narrowed to the strategy's own"
    source: "`launcher.py` 2526-2528, past 2520-2524"
  - claim: "The mode is the strategy's own where it has one and the account's where it has none, and all three are answered together"
    source: "`launcher.py` 2530, then 2531, then 2533"
---
# What a strategy is told about the account

A strategy is handed its own positions, the money left to it, and the mode it is working under, and all three are worked out fresh each time it is asked.

## When there is nothing to tell

With no state or no settings to read, the answer is no positions, no money and a halted mode. A strategy the settings do not name is told the same.

So a strategy removed from the settings while the host is up gets an answer rather than a refusal, and that answer is the one a halted account gets.

## The money

The pool at that strategy's share of it, less what the strategy already has deployed, held at nothing at the least. A strategy deployed past its share is told it has nothing left rather than a figure below nothing.

## The positions

Every position the account holds is copied under the positions lock, where one was given, and without it where none was. Only after that copy are they narrowed to the strategy's own.

So the lock covers the copy and not the narrowing, and an account holding many positions for many strategies copies all of them to answer about one.

## The mode

The strategy's own where it has one, and the account's where it has none. A strategy halted on its own account therefore reads as halted while the account reads as running.

## Related

- [What settles a request before the first stage](what-settles-a-request-before-the-first-stage.md)
- [The per-strategy caps, trimmed and sealed](the-per-strategy-caps-trimmed-and-sealed.md)
