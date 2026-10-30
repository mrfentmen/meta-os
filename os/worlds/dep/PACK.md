# DEP world pack: water and sewer utility

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this document.
No runtime code in this pack runs a real utility, controls real pumps,
or replaces any existing SCADA, compliance, or dispatch system. Del
ordered the NYC institutional pack set on 2026-10-28; this pack is one
of it.

## Purpose

Utility work runs on wet-well levels, lab results, rain gauges, and
overtime calls: which pump station is trending toward an overflow,
which sample came back over limit, which outfall is active, and which
field crew is up. This pack defines the agent crew that carries that
load inside a Meta World installation: a pump station watcher, a water
quality watcher, an overflow watcher, an operations scribe that keeps
and seals the record, and a messenger that publishes advisory state to
other worlds as zone-level counts.

The pack advises and records. Operating decisions stay with the
operator in charge, and every override of a pack alert by a human is
recorded with the operations record. Customer records and individual
sample values are local to the utility, always.

## What it watches

- **Pump station.** Wet-well level trends against overflow risk, pump
  fault codes, and power state, flagged before the wet well is full.
- **Water quality.** Sample results and residuals against limits, any
  exceedance flagged for immediate retest and elevation.
- **Sewer overflow.** Outfall and overflow state against rainfall and
  interceptor levels, kept as the event record.
- **Operations record.** Advisories issued, exceedances retested and
  cleared or escalated, overflows opened and closed, sealed at shift
  end as the verified record.

## Agent roster

| Agent | Job |
|---|---|
| pump-watcher | Runs the pump station board and raises fault alerts. Advises the operator in charge; it never starts or stops a pump. |
| quality-watcher | Watches samples and residuals against limits and elevates exceedances. |
| overflow-watcher | Watches outfall and overflow state against rainfall and interceptor levels. |
| ops-scribe | Keeps the operations record as it happens, sealed at shift end. |
| civics-messenger | The only agent that may post across worlds. Publishes advisory state by zone; receives scene safety and road clearing status. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`, one
line, pointing at a stored record. Only alerts marked summary may
cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| pump-fault | warning | local | no | Station id, pump id, fault class. |
| overflow-active | critical | local | no | Outfall id, active overflow observed, observed start. |
| sample-exceedance | critical | local | no | Site id, analyte, that a limit was exceeded, retest requested. No raw values cross. |
| pressure-drop | warning | local | no | Zone id, observed drop. |
| water-advisory | warning | summary | yes | Zone ids and advisory states (none, watch, boil advisory), counts and states only. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Customer names, addresses, and service records; individual sample results and lab detail; pump station telemetry and SCADA reads; field crew rosters, time entries, and overtime records. |
| bus_summary | Advisory state by zone as counts and states; overflow counts and states without location detail beyond zone; aggregate field service states. |

The rule is structural, not a promise: the validator refuses any
cross-bus line that is not a summary, and every cross-world send
declares what it never carries.

## Cross-world messages

Sends:

- To **doe**: `water-advisory` (zone advisory states affecting school
  building operations). Never carries customer data, raw sample
  values, station internals, or crew records.
- To **mta**: `water-advisory` (same shape, for main breaks flooding
  track beds). Same never-carries.

Receives:

- From **nypd**: `scene-safety-summary` (closures and perimeter state
  affecting main break and hydrant repairs).
- From **dsny**: `road-clearing-status` (storm clearing affecting field
  crew access).

## Firstboot config

Per-installation personalization happens at firstboot, not in a
per-installation image. One DEP image serves every installation; the
box learns which zones and stations it serves during first boot.

| Field | Label | Required |
|---|---|---|
| utility_name | Utility or bureau name | yes |
| zone_map | Pressure and advisory zones this installation serves | yes |
| station_list | Pump stations and outfalls assigned here | yes |
| sample_route_list | Sampling routes and their schedule | yes |
| crew_roster | Field crew roster: crews and on-call rotations | yes |
| operator_contact | Operator in charge or admin contact | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | A confirmed contamination event with immediate health impact. Preempts everything. |
| 2 | urgent | Active overflows, exceedances, pump faults, live advisory state. |
| 3 | routine | Pressure drops inside tolerance, roster state changes. |
| 4 | digest | Sealed operations record, end-of-shift summary. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts, privacy
classes, cross-world messages, firstboot fields, and urgency classes.
It does not contain a working utility system, and nothing in it should
be read as one.
