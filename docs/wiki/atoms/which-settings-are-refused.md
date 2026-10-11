---
row: P4-25
baseline: 49aa659
created: 2026-10-02 08:55 UTC
modified: 2026-10-11 22:51 UTC
evidence:
  - claim: "These are the checks made as the settings are read, before the host is built"
    source: "`launcher.py` 4859-4980 ahead of the build at 4984-4991"
  - claim: "Other settings are checked later, as an account's runtime is put together"
    source: "`launcher.py` 4591-4626"
  - claim: "Any of the five required settings missing or empty refuses the start"
    source: "`launcher.py` 4683-4686, the five listed at 174-180"
  - claim: "A trade mode that is neither of the two refuses it, surrounding space and case making no difference"
    source: "`launcher.py` 4747-4750, the comparison made at 4714 against 181-183"
  - claim: "Live without the arming phrase, matched exactly, refuses it"
    source: "`launcher.py` 4728-4733 against the phrase at 185"
  - claim: "A simulated-venue address together with live refuses it, where the address is more than blank space"
    source: "`launcher.py` 4723-4726, the address read at 4715"
  - claim: "That address is held to http or https"
    source: "`launcher.py` 4766-4768"
  - claim: "It is held to naming a host as well"
    source: "`launcher.py` 4774-4776"
  - claim: "One malformed enough to fail parsing refuses the start before either of those checks"
    source: "`launcher.py` 4764"
  - claim: "An epoch that will not parse as a whole number refuses it"
    source: "`launcher.py` 4867"
  - claim: "An epoch that is not positive refuses it"
    source: "`trading_config.py` 115-117"
  - claim: "A shutdown limit that will not parse as a number refuses it, and so does one at or below nought"
    source: "`launcher.py` 4968 into `trading_config.py` 131-133"
  - claim: "That test lets a limit of infinity through, and one that is not a number at all"
    source: "`trading_config.py` 131-133"
  - claim: "An execution mode named that is not a known one refuses the start"
    source: "`launcher.py` 861-869, called at 4969-4975, with the simulator case at 871-876"
  - claim: "A port given for the endpoint that will not parse as a whole number refuses it, an empty one falling back to the default instead"
    source: "`launcher.py` 4979-4980"
---
# Which settings are refused

These are the checks made on [a host's settings](the-settings-a-host-is-given.md) as they are read, and a check that fails ends the start. All of them run before the host is built, though the manifests have been read and their contents turned into objects by then. Other settings are checked later still, as each account's runtime is put together.

## The required five

Any of the five missing or empty refuses the start. So does a trade mode that is neither of the two allowed, though surrounding space and a difference of case are both forgiven.

## What live asks for

Live refuses without an arming phrase matched exactly — no spare space, no change of case.

It refuses outright where an address for the [simulated venue](binsim.md) is given alongside it, blank space counting as no address at all. And it refuses where any of [the deployment caps](the-deployment-caps.md) is unset.

## The simulated venue's address

The address is held to http or https, and to naming a host. One malformed enough to fail parsing is refused ahead of either of those.

## The numbers

The epoch must parse as a whole number and then be positive. The port for the endpoint, where one is given, must parse as a whole number; an empty one falls back to the default.

The shutdown limit must parse as a number and sit above nought. That last test is a comparison, so a limit of infinity passes it, and so does one that is not a number at all.

## The execution modes

A named mode that is not a known one refuses the start. So does a mode that [only a real venue can take](ways-of-working-a-host-may-drive.md), named while the simulated venue is in use.

## Related

- [The deployment caps](the-deployment-caps.md)
- [Which accounts are refused](which-accounts-are-refused.md)
- [The settings a host is given](the-settings-a-host-is-given.md)
