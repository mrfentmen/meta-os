# DSNY world pack: sanitation department

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this document.
No runtime code in this pack runs a real sanitation department,
directs real collection routes, or replaces any existing operations
or dispatch system. Del ordered the NYC institutional pack set on
2026-10-28; this pack is one of it.

## Purpose

Sanitation work today runs on a dispatch board, radio chatter, and
memory: which routes are done, which truck died mid-route, how much
salt is left, and how long the crew has been out in the storm. This
pack defines the agent crew that carries that load inside a Meta World
installation: a watcher on the route board, a fleet health watcher, a
storm scribe that keeps the record as it happens, and a messenger that
publishes storm clearing status to other worlds as counts only.

The pack advises and records. Dispatch decisions stay with the
dispatcher and the supervisors, and every override of a pack alert by
a human is recorded with the shift record. Crew names and time
entries are local to the depot, always.

## What it watches

- **Route board.** Which sections are serviced, partial, or missed,
  and which routes are late against the service window.
- **Fleet health.** Truck fault codes, spreader attachment state, and
  which trucks are out of service, so a truck that dies mid-route is
  known before the crew is stranded.
- **Storm board.** Plow and spreader assignment per gate, pass counts
  against the plow interval, salt estimates, and worker hours on shift.
- **Collection record.** Sections serviced and missed per route per
  day and storm passes per sector, sealed at shift end as the verified
  operations record.

## Agent roster

| Agent | Job |
|---|---|
| route-watcher | Runs the route board and raises late-route alerts. Advises the dispatcher; it never orders a crew. |
| fleet-watcher | Keeps truck health and the out-of-service list current. |
| storm-scribe | Keeps the storm operations record and the collection record as it happens, and seals each at shift end. |
| civics-messenger | The only agent that may post across worlds. Sends storm clearing status by sector as counts; receives road closure and service diversion summaries. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`, one
line, pointing at a stored record. A pack alert adds a privacy class
and an urgency class (see `worlds/README.md`); only alerts marked
summary may cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| route-serviced-late | warning | local | no | Route or section id, minutes past the service window. |
| truck-down | warning | local | no | Truck id, fault class, affected route id. |
| worker-stranded | critical | local | no | Truck id, route id, last crew check-in time. Crew names never ride any line. |
| salt-low-estimate | warning | local | no | Sector id and estimated spreader passes remaining, marked as an estimate. |
| shift-hours-flag | warning | local | no | Worker id and hours on shift; local to the depot. |
| storm-status-summary | warning | summary | yes | Sector pass counts and service state, counts only. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Worker names, crew assignments, and time entries; truck fault codes, locations, and spreader rate logs; individual complaint details before review; full records before they are sealed. |
| bus_summary | Sector plow and spreader pass counts; service state by sector as counts; storm status summaries for mutual aid. |

The rule is structural, not a promise: the validator refuses any alert
that crosses the bus without the summary class, and every cross-world
send in `pack.json` declares what it never carries.

## Cross-world messages

Sends:

- To **nypd**: `road-clearing-status` (sector pass counts and service
  state). Never carries worker names, crew time entries, truck fault
  details, or addresses.
- To **mta**: `road-clearing-status` (same shape, same never-carries).

Receives:

- From **nypd**: `scene-safety-summary` (closures and perimeter state
  affecting plow routes).
- From **mta**: `service-diversion` (reroutes that change collection
  schedules or gate access).

## Firstboot config

Per-depot personalization happens at firstboot, not in a per-depot
image. One DSNY image serves every depot; the box learns which depot
it is during first boot.

| Field | Label | Required |
|---|---|---|
| depot_name | Depot or garage name | yes |
| sector_name | Borough or sector this depot serves | yes |
| route_roster | Route roster: routes and the crews riding them | yes |
| plow_interval_minutes | Storm plow pass interval in minutes | yes |
| supervisor_contact | Depot supervisor or admin contact | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | A crew unreachable or stranded during storm operations. Preempts everything. |
| 2 | urgent | Late routes, trucks down mid-route, low salt, live storm status. |
| 3 | routine | Hours-on-shift flags and roster state changes. |
| 4 | digest | Sealed collection record, end-of-shift storm summary. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts, privacy
classes, cross-world messages, firstboot fields, and urgency classes.
It does not contain a working sanitation system, and nothing in it
should be read as one.
