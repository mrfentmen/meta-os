# MTA world pack: transit authority

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this document.
No runtime code in this pack runs a real transit system, controls real
signals or trains, or replaces any existing control center or
dispatch system. Del ordered the NYC institutional pack set on
2026-10-28; this pack is one of it.

## Purpose

Transit operations run on a control desk, radio channels, and
experience: how far the gap on every line segment has drifted, which
car just went out of service, how thin the platform crowd is getting,
and what the record of the last incident actually says. This pack
defines the agent crew that carries that load inside a Meta World
installation: a headway watcher, a fleet health watcher, a platform
crowd watcher where feeds exist, an incident scribe that seals the
verified record, and a messenger that publishes service state and
casualty counts to police, EMS, and civic worlds.

The pack advises and records. Dispatch and control decisions stay with
the control center, and every override of a pack alert by a human is
recorded with the incident timeline. Crew rosters and overtime records
are local to the agency, always; rider imagery never leaves the
system, ever.

## What it watches

- **Headway board.** Bunching and gaps on every line segment against
  the schedule, flagged while the gap can still be recovered.
- **Fleet health.** Car and bus fault codes, out-of-service state, and
  what is available for the dispatch board.
- **Platform crowd.** Crowd states where feeds exist, flagged against
  safe-density thresholds before they become crush conditions.
- **Incident timeline.** Suspensions, rescues, casualty counts, and
  clearance, kept in order and sealed at the end of each event.

## Agent roster

| Agent | Job |
|---|---|
| headway-watcher | Runs the headway board and raises gap alerts. Advises the control center; it never orders a train or a run. |
| fleet-watcher | Keeps car and bus health and the availability list current. |
| platform-watcher | Watches platform and station crowd states and flags density. |
| inc-timeline | Keeps the verified incident record as it happens, sealed at clearance. |
| transit-messenger | The only agent that may post across worlds. Sends casualty counts and service summaries; receives scene safety and road clearing status. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`, one
line, pointing at a stored record. Only alerts marked summary may
cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| headway-gap | warning | local | no | Line id, observed gap in minutes. |
| car-down | warning | local | no | Car or bus id, fault class, line id. |
| platform-overcrowd | critical | local | no | Station id, crowd state against thresholds. No imagery leaves. |
| service-suspended | critical | local | no | Line id, suspension state, estimated delay. |
| incident-casualty-summary | critical | summary | yes | Incident id, casualty counts by severity, service state. No names. |
| service-status-summary | warning | summary | yes | Line ids, service states, delay counts. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Rider observation feeds and platform imagery; worker names, crew rosters, and overtime records; car and bus fault details and maintenance records; the full incident timeline before review. |
| bus_summary | Service states by line with delay counts; casualty counts by severity; crowd-state counts by station where feeds exist. |

The rule is structural, not a promise: the validator refuses any
cross-bus line that is not a summary, and every cross-world send
declares what it never carries.

## Cross-world messages

Sends:

- To **ems**: `incident-casualty-summary` (incident id, casualty counts
  by severity, service state). Never carries rider or worker names,
  rosters, images, or individual medical details.
- To **nypd**: `incident-casualty-summary` (same shape, plus perimeter
  support needs). Same never-carries.
- To **dsny**: `service-status-summary` (line states and delay counts,
  for mobility during storms). Never carries individual incident
  details, rosters, or imagery.

Receives:

- From **nypd**: `scene-safety-summary` (closures and perimeter state
  affecting surface access and track right-of-way).
- From **dsny**: `road-clearing-status` (storm clearing affecting
  surface transit).
- From **dep**: `water-advisory` (main breaks flooding track beds,
  advisory state by zone).

## Firstboot config

Per-division personalization happens at firstboot, not in a
per-division image. One MTA image serves every division; the box
learns which lines it serves during first boot.

| Field | Label | Required |
|---|---|---|
| agency_name | Agency or operating division name | yes |
| line_group | Lines or divisions this installation serves | yes |
| crew_roster | Crew roster: runs and the workers riding them this week | yes |
| headway_tolerance_minutes | Headway gap threshold before a flag fires | yes |
| dispatch_contact | Dispatch or control center contact | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | Platform overcrowd toward crush conditions and any casualty event. Preempts everything. |
| 2 | urgent | Service suspensions, bad headway gaps, casualty summaries. |
| 3 | routine | Cars pulled from service, headway drift inside tolerance. |
| 4 | digest | Sealed incident timelines, end-of-shift summaries. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts, privacy
classes, cross-world messages, firstboot fields, and urgency classes.
It does not contain a working transit system, and nothing in it should
be read as one.
