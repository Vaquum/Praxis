---
row: P99-02
baseline: 49aa659
created: 2026-11-09 07:50 UTC
modified: 2026-11-09 07:50 UTC
evidence:
  - claim: "The configuration, the spine, the venue and the manager are each handed out exactly as held"
    source: "`praxis/trading.py` 260, and 266, and 272, and 278"
  - claim: "Whether it has started is handed out the same way, as the flag stands"
    source: "`praxis/trading.py` 284"
  - claim: "The loop is the one that refuses: asking before a start has set it raises"
    source: "`praxis/trading.py` 294 into 295-296, else 298"
---
# What the facade hands out

Five things the facade holds are handed out as they stand. The event loop refuses to be asked for too early.

## The five that answer

The configuration, the spine, the venue and the manager, each handed out exactly as held — no copy, so a caller can reach through any of them and change what the facade is using.

Whether it has started is handed out the same way, as the flag stands. A caller reading it gets a report of a moment, and [the setters are already closed](what-the-facade-refuses-once-a-start-has-begun.md) before that flag turns true.

## The one that refuses

The loop. Asking for it before a start has set it raises, rather than answering with nothing.

So the facade distinguishes two kinds of not-yet-ready: the flag says plainly that starting has not finished, and the loop refuses to be used at all. A caller that wants to know can ask the flag; a caller that wants to use it cannot get a broken answer.

## Related

- [What the facade is built with](what-the-facade-is-built-with.md)
- [What the facade refuses once a start has begun](what-the-facade-refuses-once-a-start-has-begun.md)
