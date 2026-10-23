---
row: N1-05
baseline: 49aa659
created: 2026-10-18 08:20 UTC
modified: 2026-10-23 09:00 UTC
reviewed: 2026-10-23 09:00 UTC
evidence:
  - claim: "An outcome is matched to a strategy by name, and one that cannot be is parked under its command's name"
    source: "`nexus/core/outcome_loop.py` 396-399, parked at 230-231 into 246-248"
  - claim: "The first retry is due a twentieth of a second later"
    source: "`nexus/core/outcome_loop.py` 247, the schedule at 58-66"
  - claim: "A later outcome for a command already parked queues behind it rather than being tried"
    source: "`nexus/core/outcome_loop.py` 216-228"
  - claim: "A queue not yet due is passed over for that pass"
    source: "`nexus/core/outcome_loop.py` 281-282"
  - claim: "Only the head is tried, and the rest drain behind it in order once it resolves"
    source: "`nexus/core/outcome_loop.py` 284-288 into 327-328"
  - claim: "A sibling that will not resolve mid-drain becomes the new head"
    source: "`nexus/core/outcome_loop.py` 331-334"
  - claim: "The waits lengthen and then level off"
    source: "`nexus/core/outcome_loop.py` 58-68, taken at 304"
  - claim: "A sibling counts as taken even where handing it over failed, so the queue moves on"
    source: "`nexus/core/outcome_loop.py` 412-417 and 426-431"
  - claim: "A head outstanding past the last wait has the whole queue dropped, and only logged"
    source: "`nexus/core/outcome_loop.py` 295-301"
---
# An outcome waiting on a strategy

A waiting outcome is a report back from Praxis that matches no strategy yet. It is set aside under its command's name and tried again, and every later report for that command waits behind it.

## Set aside, and queued behind

The first unmatched report is parked, with its first retry due a twentieth of a second later.

Every later report for that command joins the queue behind it rather than being tried on its own. That is what keeps them in the order they arrived: an acknowledgement and [the fill](what-a-fill-is.md) after it would otherwise reach the strategy the wrong way round, because the second might match while the first still does not.

## Only the head moves

A queue whose moment has not come is passed over entirely for that pass, so nothing behind the head advances while the head waits.

When the moment comes, the head alone is tried. Where it matches, the rest are taken in order behind it — taken, rather than certainly delivered, since a failure in the handing over counts as taken and the queue moves on regardless. Where one of them matches no strategy after all, it becomes the new head with the rest still behind it, so the order survives a second failure as it survived the first.

## When it never matches

The waits lengthen and then level off. A head still unmatched past the last of them has the whole queue dropped — the head and everything queued behind it — and the dropping is written to the log rather than reported to anyone.

So a strategy that never resolves costs its command every report, not only the first.

## Related

- [How an outcome crosses back](how-an-outcome-crosses-back.md)
- [What an outcome is](what-an-outcome-is.md)

---

Created 2026-10-18 08:20 UTC · Last modified 2026-10-23 09:00 UTC
