---
row: N15-06
baseline: 49aa659
created: 2026-11-08 10:13 UTC
modified: 2026-11-08 10:13 UTC
evidence:
  - claim: "Where no controller was supplied the answer goes down a direct write, which does nothing at all where the mode is unchanged"
    source: "`nexus/core/health_loop.py` 179-180 into 201-202"
  - claim: "Otherwise that write puts a whole new mode state in place, naming health as the driver, with a fresh moment carrying the UTC marker"
    source: "`nexus/core/health_loop.py` 204-207, reached rather than 202"
  - claim: "Where a controller was supplied the answer goes through it instead"
    source: "`nexus/core/health_loop.py` 176-177, reached rather than 180"
  - claim: "That road stores the answer, then weighs the two risk breakers, then settles the mode again"
    source: "`nexus/core/mode_controller.py` 120-123"
  - claim: "The settling takes the halted mode where any halt hold is standing, whatever the answer was"
    source: "`nexus/core/mode_controller.py` 488-489"
  - claim: "The pending halt is told after the lock is let go"
    source: "`nexus/core/health_loop.py` 185-186, outside the lock opened at 169"
  - claim: "The mode and the driver are read before the write and again after, and a turn that changed neither answers without telling anyone"
    source: "`nexus/core/health_loop.py` 173-174 and 182-183 into 188-189"
---
# The two roads a turn's answer takes

A turn of the health loop writes its answer by one of two roads, and which one was fixed when the loop was made.

## The direct road

Where no controller was supplied, the answer goes to a direct write. That write does nothing at all where the mode already stands where the answer says. Otherwise it puts a whole new mode state in place, naming health as the driver, with a fresh moment carrying the UTC marker.

What the turn asked for is what the mode becomes.

## The road through the controller

Where a controller was supplied, the answer goes through it instead. That road stores the answer, then weighs the two risk breakers and settles the mode again over everything holding it.

So this road can leave a mode the turn did not ask for: an answer of active that meets a standing hold comes out halted.

## What is read either side

The mode and the driver are read before the write and again after. A turn that changed neither answers without telling anyone; one that changed either tells of the move.

That reading either side is what makes the two roads comparable, since only the second can answer with something other than what was asked.

## What waits for the lock to go

The pending halt is told after the lock is let go, so whatever that telling runs is not holding the mode.

## Related

- [What stops a health turn](what-stops-a-health-turn.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
- [How the mode is settled](how-the-mode-is-settled.md)
