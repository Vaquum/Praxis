---
row: P4-03
baseline: 49aa659
created: 2026-10-02 08:53 UTC
modified: 2026-10-11 20:39 UTC
evidence:
  - claim: "A host started from its settings reads the environment it was started in, and one manifest for each path it is given, each naming its account"
    source: "`launcher.py` 4858 and 4882-4884"
  - claim: "Five settings must be present and not empty"
    source: "`launcher.py` 174-180, tested at 4683-4686"
  - claim: "Many more are read where they are there, among them a separate base for strategy state and an address for a simulated venue"
    source: "`launcher.py` 4869-4870, 4715, 761-766 and 4968-4980"
  - claim: "The trade mode, and any simulated-venue address beside it, pick which set of three venue addresses is returned"
    source: "`launcher.py` 4714-4750"
  - claim: "Paper returns the test addresses, where no simulated-venue address was given"
    source: "`launcher.py` 4721 into `binance_urls.py` 15-17"
  - claim: "Live returns the real ones, past the refusals it must clear first"
    source: "`launcher.py` 4745 into `binance_urls.py` 12-14"
  - claim: "An address for the simulated venue, given in paper mode, replaces all three"
    source: "`launcher.py` 4717-4719 into 4778-4783"
  - claim: "Everything standing for the host is carried over, the port and any user part included, and anything after it dropped"
    source: "`launcher.py` 4779-4781"
  - claim: "The scheme is kept only for the first address; the two socket addresses take a socket scheme of their own, and the second a fixed path"
    source: "`launcher.py` 4778-4781"
  - claim: "Every direct YAML match in the manifests directory is enumerated in sorted order and loaded in turn"
    source: "`launcher.py` 4825, called at 4872, loaded at 4882-4883"
  - claim: "The account named in a manifest is checked, then used to form a path under the state base with the epoch below it"
    source: "`launcher.py` 4884-4885 ahead of 4928-4933"
  - claim: "In live mode credentials come from a named file of secrets, or the system keyring where none is named"
    source: "`launcher.py` 4946-4950 into `secret_store.py` 291-310 and 331-336"
  - claim: "In paper mode the key and secret are read from the environment, under a suffix made by uppercasing the account's name and replacing anything else with an underscore"
    source: "`launcher.py` 4912-4926, the suffix made at 4815"
---
# The settings a host is given

A [host](starting-a-host.md) started from its settings reads two things: the environment it was started in, and one manifest for each [account](what-an-account-is.md) it is to run.

## What must be set

Five must be present and not empty — the epoch, the trade mode, where the manifests are, where the strategies are, and where state is kept.

Many more are read where they are given. Among them a separate base for strategy state, an address for a [simulated venue](binsim.md), [the deployment caps](the-deployment-caps.md), the shutdown limit and the port for the endpoint.

## The venue's addresses

The trade mode picks which set of three addresses for [the venue](what-a-venue-is.md) is returned: paper the test set, unless a simulated-venue address was given; live the real one, past [its refusals](which-settings-are-refused.md). All are written in the code rather than given as settings.

An address for the simulated venue, given in paper mode, replaces all three. Everything standing for the host is carried over — the port and any user part included — and anything after it dropped. Its scheme is kept only for the first address: the two socket addresses take a socket scheme of their own, and the second a fixed path.

## One manifest per account

Every direct YAML match in the manifests directory is enumerated in sorted order, then loaded in turn. Each names the account it is for; the name is [checked](which-accounts-are-refused.md#the-names), then used to form a path under the state base with the epoch below it.

## Where credentials come from

In live mode, from a named file of secrets, or the system keyring where no file is named.

In paper mode, from the environment, under a suffix made by uppercasing the account's name and replacing anything that is not a letter or digit with an underscore.

## Related

- [Which settings are refused](which-settings-are-refused.md)
- [Where credentials come from](where-credentials-come-from.md)
