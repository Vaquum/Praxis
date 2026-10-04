---
row: P4-26
baseline: 49aa659
created: 2026-10-02 09:06 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A manifests directory that is not one refuses the start"
    source: "`launcher.py` 4821-4823"
  - claim: "A directory with no direct YAML match refuses it"
    source: "`launcher.py` 4826-4828, the patterns at 4825"
  - claim: "An account name is held to letters, digits, dots, dashes and underscores, beginning with a letter or digit"
    source: "`launcher.py` 4800-4805, the rule written at 4786"
  - claim: "The name checked is the one the loader has already trimmed"
    source: "Nexus `manifest.py` 398, read at `launcher.py` 4884"
  - claim: "Two manifests naming the same account refuse the start"
    source: "`launcher.py` 4894-4899"
  - claim: "Two names that flatten to the same suffix refuse it, in either mode"
    source: "`launcher.py` 4901-4907, the suffix made at 4892 into 4815"
  - claim: "In paper mode such names would read the same pair of settings"
    source: "`launcher.py` 4913-4914"
  - claim: "In live mode the lookup uses the account's own name instead"
    source: "`launcher.py` 4957 into `secret_store.py` 204 and 331-333"
  - claim: "In live mode a manifest without a daily-loss limit, or without either drawdown limit, refuses the start"
    source: "`launcher.py` 4887-4888 into 806-818"
  - claim: "In paper mode a key or secret missing or empty for any account refuses it"
    source: "`launcher.py` 4916-4921"
  - claim: "Credentials that cannot be found, or whose store will not answer, refuse it"
    source: "`launcher.py` 4956-4960"
  - claim: "A secrets file that will not decode refuses it elsewhere, past that catch"
    source: "`secret_store.py` 291-295 against the catch at `launcher.py` 4958, ending at 5003-5008"
  - claim: "A secrets file is validated whole, so a bad record for an account no manifest names refuses it too"
    source: "`secret_store.py` 307-310"
---
# Which accounts are refused

Every [account](what-an-account-is.md) a [host](the-settings-a-host-is-given.md) is to run is checked as its manifest is read, and a check that fails ends the start. These are the checks the launcher makes; a manifest's own contents are checked by the loader that reads it, which is a subject of its own.

## Where the manifests are

A manifests directory that is not a directory refuses the start, and so does one with no direct YAML match in it.

## The names

An account's name becomes part of a path, so it is held to letters, digits, dots, dashes and underscores, and to beginning with a letter or digit. The name checked is the one the loader has already trimmed, so surrounding space alone does not refuse it.

Two manifests naming the same account refuse the start. So do two names that flatten to the same suffix once uppercased — in either mode, though it is only paper mode where such names would read the same pair of settings. A live lookup uses the account's own name.

## The risk limits

In live mode each manifest must arm the breakers: a daily-loss limit, and at least one of the two drawdown limits. A manifest short of either refuses the start.

## The credentials

In paper mode a key or secret missing or empty for any account refuses the start.

In both modes, credentials that cannot be found, or whose store will not answer, refuse it. A secrets file that will not decode refuses it as well, by a route that passes outside the catch meant for credentials. And such a file is validated whole, so a bad record for an account no manifest names refuses the start too.

## Related

- [Which settings are refused](which-settings-are-refused.md)
- [Where credentials come from](where-credentials-come-from.md)
