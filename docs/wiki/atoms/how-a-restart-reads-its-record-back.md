---
row: P134-01
baseline: 49aa659
created: 2026-11-15 11:30 UTC
modified: 2026-11-15 11:30 UTC
evidence:
  - claim: "Reading the record back refuses where the account is not registered"
    source: "`execution_manager.py` 1108, then 1109 into 1110-1111"
  - claim: "An older shape of registration is bridged first, and the scheme history folded before any event is walked"
    source: "`execution_manager.py` 1113, then 1115, then 1116"
  - claim: "Every event is then walked in order and projected onto the account's state"
    source: "`execution_manager.py` 1118, then 1119"
  - claim: "A flatten record adds its order's name to the account's own set of them"
    source: "`execution_manager.py` 1121 into 1126"
  - claim: "A scheme start and a submitted intent each record what was asked for, by amount for the one and by amount and money for the other"
    source: "`execution_manager.py` 1128 into 1129-1131, and 1155, then 1158-1160"
  - claim: "An accepted command is noted against this account, and an outcome whose status is terminal marks the command terminal and drops it"
    source: "`execution_manager.py` 1133 into 1134, and 1136 into 1137-1138"
  - claim: "A submitted intent records the trade's name and maps the command to its order"
    source: "`execution_manager.py` 1156, then 1157"
  - claim: "A command is rebuilt from that intent only where it stands unmarked as terminal, began no scheme, and has nothing held for it already"
    source: "`execution_manager.py` 1162-1166 into 1167-1187"
  - claim: "Whatever it was, it is rebuilt as a single order with a replay timeout, no reference price, no maker preference and no self-trade handling"
    source: "`execution_manager.py` 1176, then 1182, the timeout at 178, then 1183, then 1184, then 1185"
  - claim: "Four resumes then run in a fixed order: the schemes, the ladders, the brackets, and the protection whose fate is unknown"
    source: "`execution_manager.py` 1189, then 1190, then 1191, then 1192"
---
# How a restart reads its record back

Reading the record back is how an account's live work is rebuilt after a restart, and it walks every event once before rebuilding anything that spans several of them.

## Before the walk

The account must be registered, or the reading refuses. An older shape of registration is bridged, and the scheme history folded — so the names of the commands that began a scheme are known before any event is read.

## What the walk does with each kind

Every event is projected onto the account's state. Beyond that: a flatten record adds its order's name to the account's own set of them, which outlives the bracket that ordered it. A scheme start and a submitted intent each record what was asked for — by amount for the one, by amount and money for the other. An accepted command is noted against this account. An outcome whose status is terminal marks the command terminal and drops it.

A submitted intent also records the trade's name and maps the command to its order.

## What is rebuilt as a single order

A command is rebuilt from its intent only where it stands unmarked as terminal, began no scheme, and has nothing held for it already. Whatever it was, it comes back as a single order — with a replay timeout, no reference price, no maker preference and no self-trade handling.

So the modes that span several events are not rebuilt here at all. They are rebuilt by the four resumes that run after the walk, in a fixed order: the schemes, the ladders, the brackets, and the protection whose fate is unknown.

## Related

- [What a restart puts back](what-a-restart-puts-back.md)
- [How a price change is carried out](how-a-price-change-is-carried-out.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)
