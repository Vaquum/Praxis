---
row: P165-01
baseline: 49aa659
created: 2026-11-16 03:00 UTC
modified: 2026-11-16 03:00 UTC
evidence:
  - claim: "The thread is remembered the first time an account is registered, and only the first time"
    source: "`execution_manager.py` 820 into 821"
  - claim: "Handing news to an account is refused from any other thread"
    source: "`execution_manager.py` 3101-3104, then 3109"
  - claim: "Admitting an event is refused the same way"
    source: "`execution_manager.py` 3168-3171, then 3176"
  - claim: "Before any account is registered the remembered thread is absent and neither refusal can fire"
    source: "`execution_manager.py` 820, against 3102"
  - claim: "An account the manager does not hold is refused on both roads"
    source: "`execution_manager.py` 3111, then 3112 into 3114, and 3178, then 3179 into 3181"
  - claim: "News that passes both readings is put on the account's own queue without waiting"
    source: "`execution_manager.py` 3116"
---
# Which thread the manager will take work from

The manager takes work from one thread, the one its event loop runs on, and it learns which that is by watching who registers the first account.

## How it is learned

The thread is remembered the first time an account is registered, and only the first time. Every account registered after that leaves the remembered thread as it was.

## Where it is read

Two ways in read it: handing news to an account, and admitting an event. Both refuse a call from any thread but the remembered one, and both refuse an account the manager does not hold.

News that passes both readings is put on the account's own queue without waiting — which is the reason for the thread rule, that queue being safe to put to from one thread only.

## The window before it is learned

Until the first account is registered there is no remembered thread, and a reading against nothing refuses nothing. So both ways in are open to any thread in that window, and the first account's registration is what closes them.

## Related

- [What admitting an event refuses](what-admitting-an-event-refuses.md)
- [Which accounts are refused](which-accounts-are-refused.md)
- [What an account is](what-an-account-is.md)
