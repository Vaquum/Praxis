---
row: P130-01
baseline: 49aa659
created: 2026-11-15 09:30 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "A caller from any address but the two loopback ones is refused as forbidden"
    source: "`launcher.py` 3416 into 3417, the two at 195"
  - claim: "Where no token is set in the environment the roads answer as not configured"
    source: "`launcher.py` 3419, then 3421 into 3422"
  - claim: "The header must carry that token after the word Bearer, compared in a way whose timing does not vary with the answer"
    source: "`launcher.py` 3424, then 3426 into 3427"
  - claim: "Only past all three does the weighing answer with nothing, which is what lets a road go on"
    source: "`launcher.py` 3429"
  - claim: "The read-only status road weighs the same three, then resolves its account and answers with whatever refusal that gives"
    source: "`launcher.py` 3498, then 3500 into 3501, or 3503, then 3505 into 3506, or 3508"
  - claim: "The account is resolved from a copy of the published runtimes taken under their lock"
    source: "`launcher.py` 3443 into 3444, then 3446"
  - claim: "Where no account is named, a single running one is used, several are refused as needing a name with the known ones listed, and none at all is refused as unknown"
    source: "`launcher.py` 3448, then 3450 into 3451, or 3453 into 3454-3456, or 3458"
  - claim: "Where one is named and is not among them, the same unknown refusal answers"
    source: "`launcher.py` 3460, then 3462 into 3463, or 3465"
---
# What every operator road weighs first

Every road an operator can take weighs three things about the caller before it reads anything about the account, and the read-only one weighs them too.

## The three

The caller must come from one of the two loopback addresses, or it is refused as forbidden. A token must be set in the environment, or the road answers that it is not configured. The header must carry that token after the word Bearer, compared in a way whose timing does not vary with the answer.

Only past all three does the weighing answer with nothing at all, and that nothing is what lets a road go on. The read-only status road weighs them too, and then resolves its account under the same rules as the rest.

So the roads are off entirely until a token is set, and a caller reaching them from elsewhere on the network is turned away before the token is even looked up.

## Which account

Resolved from a copy of [the published runtimes](when-an-account-can-be-delivered-to.md), taken under their lock, so the resolving reads a still picture.

Where no account is named: a single running one is used, several are refused as needing a name with the known ones listed, and none at all is refused as unknown.

Where one is named and is not among them, that same unknown refusal answers.

So an operator gets the unknown answer both for naming an account that is absent and for naming none while none runs — and the one case that tells them what they could have named is the ambiguous one.

## Related

- [When an account can be delivered to](when-an-account-can-be-delivered-to.md)
- [What the one listener serves](what-the-one-listener-serves.md)
- [What an operator's halt and resume do](what-an-operators-halt-and-resume-do.md)
