---
row: P143-02
baseline: 49aa659
created: 2026-11-15 16:00 UTC
modified: 2026-11-15 16:00 UTC
evidence:
  - claim: "What is left to protect is what the entry delivered, less the exit's projected fills with the old pair's own taken back out, less what the venue said that pair filled"
    source: "`execution_manager.py` 9614"
  - claim: "Nothing left to protect drops the bracket and places no replacement"
    source: "`execution_manager.py` 9616 into 9617, then 9624"
  - claim: "The venue's remembered rules give the least amount and the least sum, and nothing for either where no rules are held"
    source: "`execution_manager.py` 9626, then 9627, then 9628"
  - claim: "A remainder below the least amount, or worth less than the least sum at the take-profit price, drops the bracket too and places no replacement"
    source: "`execution_manager.py` 9630 into 9631, then 9640"
  - claim: "Otherwise the replacement is recorded as submitted and the bracket marked so, before any order goes out"
    source: "`execution_manager.py` 9642-9649, then 9650, then 9652"
---
# When an amend places no replacement

An amend that has reconciled its old pair places a replacement only if something is left worth protecting, and it works that remainder out by subtraction.

## The subtraction

What the entry delivered, less what the exit command is projected to have filled with the old pair's own projected fills taken back out, less what the venue said that pair filled.

Taking the old pair's projected fills back out is what keeps them from counting twice — once as the exit's projection and once in the venue's answer.

## The two endings that place nothing

A remainder at or below nothing: the position was closed by a protective fill, so the bracket is dropped and no replacement goes out.

A remainder below the venue's least tradable amount, or worth less than its least sum at the take-profit price: the remainder is treated as closed dust, and again the bracket is dropped with no replacement.

Where the venue's rules are absent, both minimums read as nothing, which closes that second ending off and leaves a remainder of any size protected.

## When it does place one

The replacement is recorded as submitted and the bracket marked so, before any order goes out. So a crash between the record and the send leaves a record saying a replacement was submitted when none was.

## Related

- [How a protection amend is driven to its end](how-a-protection-amend-is-driven-to-its-end.md)
- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
