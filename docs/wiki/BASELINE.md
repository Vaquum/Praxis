# Covered commits

Every article names the source it was written from. These are the commits this wiki describes.

| Repository | Commit | Read on |
|---|---|---|
| Praxis | `49aa659` | 2026-09-20 |
| Nexus | `953477a` | 2026-09-30 |

These commits are enforced rather than trusted. [`check_wiki.py`](../../scripts/check_wiki.py) reads every cited file at the commit its repository is pinned to here, whatever the working tree holds, and fails a citation to a file absent from that commit or a page whose metadata names a different one.

A repository can be missing from the checkout altogether. Praxis is always there, since the wiki lives in it; Nexus sits beside it or not. Where it does not, a citation into Nexus is reported unread and passed over, and every other check still runs — so a clone of Praxis alone enforces the Praxis half. Such a run says so in a note of its own, so a reader is told which half went unread rather than left to assume both were read.

A later commit in either repository does not make an article wrong. It makes the article unverified until someone checks it.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-10-12 00:18 UTC
