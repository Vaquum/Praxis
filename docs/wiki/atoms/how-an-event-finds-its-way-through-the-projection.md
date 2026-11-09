---
row: P88-01
baseline: 49aa659
created: 2026-11-09 06:08 UTC
modified: 2026-11-09 06:08 UTC
evidence:
  - claim: "Three kinds of event are each weighed on their own and answer where they match, before any chain is reached"
    source: "`trading_state.py` 189-191, then 193-195, then 197-199"
  - claim: "Every other kind is weighed in one chain of alternatives, so at most one of them is acted on"
    source: "`trading_state.py` 201, or 203, or 205, or 207, or 209, or 211, or 213, or 215, or 217, or 219, or 226"
  - claim: "Each arm calls the handler for its own kind"
    source: "`trading_state.py` 202, or 204, or 208, or 210"
  - claim: "Four kinds go to the one closing routine, each handing it the final standing it means"
    source: "`trading_state.py` 206, or 212, or 214, or 216"
  - claim: "Two of those four hand it the same standing, so a refused send and a refusal from the venue end alike"
    source: "`trading_state.py` 206, against 212"
  - claim: "One kind is noted and nothing else, at the quietest level the log has"
    source: "`trading_state.py` 219"
  - claim: "A listed set of kinds is passed over in silence"
    source: "`trading_state.py` 226-227"
  - claim: "Anything the chain does not name is reported as a warning naming the kind and the account"
    source: "`trading_state.py` 228 into 229-233"
---
# How an event finds its way through the projection

Every event reaching the projection takes one of three roads: an early answer, one arm of a chain, or a complaint.

## The three that leave early

A command being accepted, a scheme being set up, and a scheme's standing changing. Each is weighed on its own and answers where it matches, before any chain is reached.

## The chain

Every other kind is weighed in one chain of alternatives, so at most one arm of it is acted on. The order of the arms is therefore the order the kinds are tried in, and a kind matching two arms would only ever reach the first.

## The four that end an order

Four kinds go to the one closing routine, each handing it the final standing it means. Two of them hand it the same standing — a send that was refused and a refusal from the venue end alike.

So the standing an order finishes in does not say which of the two happened. The name handed alongside it does, and that name reaches the log rather than the order.

## The three kinds of nothing

One kind is noted and nothing else, at the quietest level the log has. A listed set of kinds is passed over in silence. Anything the chain does not name at all is reported as a warning naming the kind and the account.

So an unprojected kind is only silent while it stays on the list; adding a kind anywhere else makes every one of them a warning.

## Related

- [Fills and the order](fills-and-the-order.md)
- [What an account is](what-an-account-is.md)
