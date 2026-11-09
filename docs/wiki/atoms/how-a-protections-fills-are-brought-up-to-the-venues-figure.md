---
row: P159-01
baseline: 49aa659
created: 2026-11-16 00:00 UTC
modified: 2026-11-16 00:00 UTC
evidence:
  - claim: "Where the venue's figure is at or below what is already counted, the figures agree and nothing is asked"
    source: "`execution_manager.py` 8168, then 8169"
  - claim: "The names of the pair's own legs are taken as the set a trade must match"
    source: "`execution_manager.py` 8171"
  - claim: "The venue's whole trade list for the symbol is asked for, and a failure to answer it holds the change"
    source: "`execution_manager.py` 8172, then 8173, or 8174, then 8181"
  - claim: "A trade whose order name is outside that set is passed over"
    source: "`execution_manager.py` 8184, then 8185 into 8186"
  - claim: "A matching trade is written down against the name the record keeps locally rather than the leg's own, so both legs' fills land under one name"
    source: "`execution_manager.py` 8188-8203, the name set at 8191 against the leg matched at 8185"
  - claim: "Only a fill the record answered with a place is counted towards the running total"
    source: "`execution_manager.py` 8204, then 8205 into 8206, then 8207"
  - claim: "The answer is whether the total now reaches the venue's figure"
    source: "`execution_manager.py` 8183, against 8209"
---
# How a protection's fills are brought up to the venue's figure

When a [protective pair](protection.md) is taken down, the venue may have filled more of it than Praxis has counted, and the gap is closed by reading the venue's own trades.

## When nothing is asked

Where the venue's figure is at or below what is already counted, the figures agree and no question goes out.

## The reading

The names of the pair's own legs are taken as the set a trade has to match, and the venue's whole trade list for the symbol is asked for. A failure to answer holds the change for a later pass rather than guessing.

A trade whose order name falls outside that set is passed over. A matching one is written down — against the name the record keeps locally rather than the leg's own, so the fills of both legs land under a single name.

Only a fill the record answered with a place is counted towards the running total, which starts at what was already counted. So a trade written twice by two passes raises the total once.

## The answer

Whether that total now reaches the venue's figure. Falling short holds the change, exactly as a failed question does: both say the local count cannot yet be trusted to size what replaces the pair.

## Related

- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [What picks a held protection change up again](what-picks-a-held-protection-change-up-again.md)
- [Protection](protection.md)
