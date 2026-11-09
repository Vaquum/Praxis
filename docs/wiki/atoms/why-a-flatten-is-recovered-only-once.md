---
row: P146-02
baseline: 49aa659
created: 2026-11-15 17:30 UTC
modified: 2026-11-16 13:30 UTC
evidence:
  - claim: "A flatten order already carrying fills is reported and left alone"
    source: "`execution_manager.py` 8018, then 8019 into 8026"
  - claim: "Otherwise the exit command is built from the venue's own amount, installed, given the entry's trade and mapped to that order"
    source: "`execution_manager.py` 8028-8030, then 8031, then 8032, then 8033"
  - claim: "Where no local order stands at all, an intent and a submission are both recorded and applied"
    source: "`execution_manager.py` 8035 into 8036-8045, then 8049, then 8051-8058, then 8059"
  - claim: "The venue's trades for the symbol are then asked for, and every one naming another order is passed over"
    source: "`execution_manager.py` 8061, then 8062, then 8063 into 8064"
  - claim: "Each remaining trade becomes a fill written to the record, and is applied only where the write answered with a place"
    source: "`execution_manager.py` 8066, then 8082, then 8083 into 8084"
  - claim: "The order is read back afterwards, and an outcome built only where it now carries fills"
    source: "`execution_manager.py` 8086, then 8087 into 8088-8090, then 8092"
---
# Why a flatten is recovered only once

Recovering a flatten writes the venue's trades into the record as fills, and it refuses to do that for an order that already carries any.

## The one test that guards it

A flatten order already carrying fills is reported and left alone, for the live reconcile to finish.

The reason is in how fills are projected: a fill adds its amount to the order's total rather than being matched by the trade it came from. Writing the venue's trades again over an order that already recorded some would count those amounts twice.

So a part-recorded flatten is deliberately not completed here. It is left in the one state this routine cannot improve.

## What is written when the test passes

The exit command, built from the venue's own amount rather than from anything local, installed, given the entry's trade and mapped to that order.

Where no local order stands at all, an intent and a submission are both recorded and applied — so the record gains the whole history of an order Praxis never saw go out.

## The fills

The venue's trades for the symbol are asked for, and every one naming another order is passed over. Each remaining trade becomes a fill written to the record, and is applied only where the write answered with a place — a duplicate write answers with none, and nothing is applied.

## The outcome

The order is read back afterwards, and an outcome is built only where it now carries fills. An order the venue reported no trades for is left without one.

## Related

- [How an unfinished close is recovered](how-an-unfinished-close-is-recovered.md)
- [The three kinds of orphan a boot finds](the-three-kinds-of-orphan-a-boot-finds.md)
- [What a fill changes](what-a-fill-changes.md)
