---
row: P114-01
baseline: 49aa659
created: 2026-11-09 08:44 UTC
modified: 2026-11-09 08:44 UTC
evidence:
  - claim: "The asking takes a session, waits for its turn against a budget, and sends the symbol as its only parameter"
    source: "`binance_adapter.py` 2170, then 2173, then 2174-2178"
  - claim: "The weight headers are read before the answer is weighed for failure, and the body only after both"
    source: "`binance_adapter.py` 2179, then 2180, then 2181"
  - claim: "An order refused becomes a plainer venue failure, a venue failure passes as it is, and a transport failure becomes a passing one"
    source: "`binance_adapter.py` 2182 into 2183-2184, or 2185 into 2186, or 2187 into 2188-2189"
  - claim: "The venue's own limits are read out of the same answer before anything else is looked at"
    source: "`binance_adapter.py` 2191"
  - claim: "A body carrying no list of symbols, or an empty one, is refused"
    source: "`binance_adapter.py` 2193, then 2195 into 2196-2197"
  - claim: "Only the first symbol of that list is read, whatever else it holds"
    source: "`binance_adapter.py` 2199"
  - claim: "A symbol carrying no list of rules, or an empty one, is refused the same way"
    source: "`binance_adapter.py` 2200, then 2202 into 2203-2204"
  - claim: "A caller handing in one symbol as text rather than a sequence is refused outright"
    source: "`binance_adapter.py` 2131 into 2132-2133"
---
# What the trading rules asking insists on

Asking the venue for a symbol's trading rules sends one parameter and insists on four things in the answer.

## The order of the asking

A session is taken, a turn waited for against a budget, and the symbol sent as the only parameter. The weight headers are read before the answer is weighed for failure, and the body only after both.

So the allowance is recorded even from an answer that turns out to be a failure, which is what keeps a run of failures from hiding how much allowance they spent.

## The three ways a failure is turned

An order refused becomes a plainer venue failure. A venue failure passes as it is. A transport failure becomes a passing one.

## What the body must have

The venue's own limits are read out of it first. Then a list of symbols, which must be there and must not be empty. Then the first symbol's list of rules, under the same demand.

Only the first symbol of the list is read, whatever else it holds — so an answer about several symbols is read as an answer about one.

## The caller's own mistake

Handing in one symbol as text rather than a sequence is refused outright. Text is itself a sequence of letters, so the refusal exists to stop a symbol being read letter by letter.

## Related

- [What the rules are read as](what-the-rules-are-read-as.md)
