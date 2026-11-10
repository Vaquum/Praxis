---
row: P117-02
baseline: 49aa659
created: 2026-11-09 09:12 UTC
modified: 2026-11-09 09:12 UTC
evidence:
  - claim: "Every strategy the manifest declares is walked, each naming a series and a bar width, and the width kept under the series' name"
    source: "`launcher.py` 2369, then 2370, then 2381"
  - claim: "A series declared twice with widths that disagree refuses the start, both widths named in the refusal"
    source: "`launcher.py` 2371, then 2373 into 2374-2379"
  - claim: "A series named in the environment is used with the width the manifest gave it, where the manifest declares it"
    source: "`launcher.py` 2383, then 2385, then 2386 into 2387"
  - claim: "Where the manifest does not declare it, a second setting must give the width, and its absence refuses the start"
    source: "`launcher.py` 2389, then 2390 into 2391-2396"
  - claim: "That width is refused for not reading as a whole number, or for standing at or below nought, and used otherwise"
    source: "`launcher.py` 2398-2399 into 2400, then 2401-2405, or 2407 into 2408-2412, or 2414"
  - claim: "The three tests are written out here rather than taken from the reader that already makes them, which refuses with a failure of another kind"
    source: "`launcher.py` 2390-2412, against 696-707"
  - claim: "With nothing named in the environment, a single gathered series is used with its width"
    source: "`launcher.py` 2416 into 2417-2418"
  - claim: "Several refuse the start, named in order, with the setting that chooses between them given"
    source: "`launcher.py` 2420 into 2421-2426"
  - claim: "None at all refuses the start too"
    source: "`launcher.py` 2428-2432"
  - claim: "The pair settled is what a reference price and a marking price are both read from, once for each account's manifest and once for the live run"
    source: "`launcher.py` 3318 into 3319-3325, and 4154 into 4174"
---
# How the mark-price series is settled

The host prices against one series of bars at one width, and that pair is settled once from the manifest and the environment together.

## What the manifest gives

Every strategy it declares is walked. Each names a series and a bar width, and the width is kept under the series' name. A series declared twice with widths that disagree refuses the start, both widths named.

## When the environment names a series

Named and declared by the manifest, and the manifest's width for it is used. Named and not declared, and a second setting must give the width: absent, it refuses; not a whole number, it refuses; at or below nought, it refuses; otherwise the named series is used with it.

Nothing on that road checks the given width against anything, so a series the manifest never mentions is priced at whatever width the setting holds.

The three tests on that width are written out here rather than taken from [the reader that already makes them](the-deployment-caps.md), which refuses with a failure of another kind.

## When it names none

One gathered series, and it is used with its width. Several, and the start is refused with them named in order and the setting that chooses between them given. None at all, and the start is refused too.

So the setting is needed exactly when the manifest is ambiguous, and ignored when it is not.

## What the pair is for

A reference price and a marking price are both read from it — settled once for each account's manifest, and once for the live run.

## Related

- [The deployment caps](the-deployment-caps.md)
- [What a replay is given](what-a-replay-is-given.md)
