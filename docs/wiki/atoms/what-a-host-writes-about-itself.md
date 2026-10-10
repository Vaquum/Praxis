---
row: P4-14
baseline: 49aa659
created: 2026-10-03 20:04 UTC
modified: 2026-10-10 12:13 UTC
evidence:
  - claim: "A line written through the arrangement itself is rendered as JSON and handed to a writer the library makes"
    source: "`praxis/infrastructure/observability.py` 59 and 62"
  - claim: "Lines written through Python's own logging are rendered as JSON too, onto standard output"
    source: "`praxis/infrastructure/observability.py` 66-75 and 77-78"
  - claim: "Every line carries its level and a moment in UTC"
    source: "`praxis/infrastructure/observability.py` 49-50"
  - claim: "A name absent from the logging module falls back to the level called INFO"
    source: "`praxis/infrastructure/observability.py` 45"
  - claim: "A name the module carries is taken whatever it stands for, and handed to the library as it is"
    source: "`praxis/infrastructure/observability.py` 45 reaching 61"
  - claim: "Context is bound once the settings have been read, the manifests loaded and the credentials fetched"
    source: "`launcher.py` 4982 into `praxis/infrastructure/observability.py` 98, the epoch read at `launcher.py` 4867"
  - claim: "Merging the bound context into a line is asked for among the steps a line goes through"
    source: "`praxis/infrastructure/observability.py` 48"
  - claim: "Each of the host's own threads is started without the context being carried to it"
    source: "`launcher.py` 2848-2853 and 3895-3902"
  - claim: "Work is handed from a thread to the loop by asking the loop to run it"
    source: "`launcher.py` 3042 and 3702"
  - claim: "A setting can turn JSON off, leaving plain text"
    source: "`launcher.py` 4850-4856"
---
# What a host writes about itself

A [host](starting-a-host.md) writes JSON, one piece per line, each carrying its level and the moment it was written in UTC.

Two routes reach the output. A line written through the arrangement is handed to a writer the library makes. Lines written through Python's own logging — by libraries knowing nothing of the arrangement — are [put through the same shape](what-the-logging-arrangement-misses.md) and handed to a stream on standard output.

## The level

A level is named in the settings, uppercased, and looked for among the names the logging module carries.

A name it does not carry falls back to the one called INFO. A name it does carry is taken for whatever it stands for and handed to the library as it is, nothing in between asking whether a level is what came back.

## The context

Context is bound once: after the settings have been read, the manifests loaded and the credentials fetched. Merging it into each line is asked for among the steps a line goes through; which value stands where a line names that field itself is the library's rule.

The binding belongs to the task that made it. Each of the host's own threads is started without it carried across, so a line written directly on one of those threads carries none of it. Work handed from a thread to the loop is handed over by asking the loop to run it, and what context it then sees is the library's affair.

## Plain text instead

One setting takes a value other than JSON and asks for plain lines through Python's own arrangement. [What that leaves in place](what-the-logging-arrangement-misses.md) is not what it appears to be.

## Related

- [What the logging arrangement misses](what-the-logging-arrangement-misses.md)
- [Starting a host](starting-a-host.md)
