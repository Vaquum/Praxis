---
row: P4-32
baseline: 49aa659
created: 2026-10-03 09:57 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "The waiting reports are kept apart from the remembered differences"
    source: "`trading.py` 1290 and 1267, keyed at 1258"
  - claim: "A handover getting through empties the waiting one"
    source: "`trading.py` 1288"
  - claim: "A difference matching one already waiting is passed over too"
    source: "`trading.py` 1267-1269"
  - claim: "One report waits per account and asset, and a fresh report failing its handover takes that place"
    source: "`trading.py` 1290, keyed at 1258"
  - claim: "A difference already remembered makes no fresh report, so the one waiting stays as it is"
    source: "`trading.py` 1264-1265"
  - claim: "A waiting report is tried before the fresh comparison and kept on failure, so one survives its asset recovering"
    source: "`trading.py` 1251 ahead of 1253, retried at 1306-1310 against the clearing at 1260-1262"
  - claim: "A failed handover never leaves the pass"
    source: "`trading.py` 1325-1333"
---
# Reports that do not get through

A [shortfall](when-a-balance-shortfall-is-reported.md) Nexus does not take is kept and tried again. One report waits per account and asset, apart from the differences the comparison remembers.

## What takes that place

A fresh report failing its handover takes the waiting place, replacing whatever was there.

A difference already remembered makes no fresh report at all, so nothing is built to take the place and the report waiting stays as it is. A shortfall that deepened and then eased back to a figure already remembered therefore leaves the deeper report waiting, past the point where the books still show it.

## When it is tried

A waiting report is tried before the fresh comparison runs, and kept where the handover fails again. So one survives its asset recovering: recovery clears the remembered difference, and leaves the waiting report alone.

A handover getting through is what empties the place.

## What a failure costs

A failed handover never leaves the pass. An unreachable Nexus cannot stop Praxis squaring its books; it only delays what Nexus is told about them.

## Related

- [When a balance shortfall is reported](when-a-balance-shortfall-is-reported.md)
- [What a reconciliation tells Nexus](what-a-reconciliation-tells-nexus.md)
