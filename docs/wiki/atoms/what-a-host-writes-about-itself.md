---
row: P4-14
baseline: 49aa659
created: 2026-10-03 20:04 UTC
modified: 2026-10-03 20:21 UTC
evidence:
  - claim: "Lines written through the arrangement itself go to standard output as JSON"
    source: "`observability.py` 59 and 62"
  - claim: "Lines written through Python's own logging are rendered as JSON too, onto standard output"
    source: "`observability.py` 66-75 and 77-78"
  - claim: "Every line carries its level and a moment in UTC"
    source: "`observability.py` 49-50"
  - claim: "A name absent from the logging module falls back to the level called INFO"
    source: "`observability.py` 45"
  - claim: "A name present there is taken whatever it means, so one naming no level at all is taken and fails later"
    source: "`observability.py` 45 reaching 61"
  - claim: "Context is bound once the settings have been read, the manifests loaded and the credentials fetched"
    source: "`launcher.py` 4982 into `observability.py` 98, the epoch read at `launcher.py` 4867"
  - claim: "Bound context fills in fields a line left out, and loses to any the line names itself"
    source: "`observability.py` 48"
  - claim: "Each of the host's own threads is started without the context being carried to it"
    source: "`launcher.py` 2848-2853 and 3895-3902"
  - claim: "Work handed to the loop from a thread carries the context of whoever handed it over"
    source: "`launcher.py` 3042 and 3702"
  - claim: "A setting can turn JSON off, leaving plain text"
    source: "`launcher.py` 4850-4856"
---
# What a host writes about itself

A [host](starting-a-host.md) writes JSON to standard output, one piece per line. Each line carries its level and the moment it was written in UTC.

Two routes reach that output. Lines written through the arrangement go straight there. Lines written through Python's own logging — by libraries knowing nothing of the arrangement — are [put through the same shape](what-the-logging-arrangement-misses.md) on the way.

## The level

A level is named in the settings, uppercased, and looked for among the names the logging module carries.

A name it does not carry falls back to the one called INFO. A name it does carry is taken for whatever it means — so a shorthand resolves to the level it is short for, and a name that stands for something other than a level is taken all the same, and fails later when the arrangement tries to use it.

## The context

Context is bound once: after the settings have been read, the manifests loaded and the credentials fetched. Every line written afterwards is filled in from it.

Filled in, rather than stamped. A field the line names itself is kept, and the bound value for that field is dropped.

The binding belongs to the task that made it. Each of the host's own threads is started without it being carried across, so a line written directly on one of those threads carries none of it. Work those threads hand to the loop is different: it carries the context of whoever handed it over.

## Plain text instead

One setting takes a value other than JSON and asks for plain lines through Python's own arrangement. [What that leaves in place](what-the-logging-arrangement-misses.md) is not what it appears to be.

## Related

- [What the logging arrangement misses](what-the-logging-arrangement-misses.md)
- [Starting a host](starting-a-host.md)
