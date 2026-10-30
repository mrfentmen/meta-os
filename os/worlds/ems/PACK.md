# EMS world pack: EMT and ambulance

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this
document. No runtime code in this pack rides in a real ambulance,
records a real patient, or replaces any EMS documentation or
dispatch system. Del ordered this pack on 2026-10-27, in the same
batch as the FDNY, NYPD, and hospital packs.

## Purpose

An ambulance ride produces the most consequential record in
emergency care and the least reliable one: vitals and treatments
called out in a moving vehicle, written up from memory at the
hospital, and handed over verbally at the door. At the same time,
the crew often learns that their destination hospital went on
diversion only when they arrive. This pack defines the agent
crew that fixes both ends inside a Meta World installation: a
scribe that keeps the ride timeline as it happens, a matcher
that checks the destination against live hospital capacity on
the bus, and a messenger that delivers the handoff record, and
warns the destination, before arrival.

The pack advises and records. Care and destination decisions
stay with the crew and their protocols, and every override of a
pack alert by a human is recorded.

## What it watches

- **Ride timeline.** Vitals sets and treatments captured en
  route, in time order, so nothing about the ride depends on
  memory afterward.
- **Destination check.** Whether the hospital this unit is
  heading to can still take the patient, checked against the
  live capacity and diversion status that hospital worlds
  publish, with a re-match when a destination goes on diversion.
- **Handoff record.** Assembled from the ride timeline before
  arrival, so the receiving hospital gets the full structured
  record at the door instead of a verbal summary.

## Agent roster

| Agent | Job |
|---|---|
| ride-scribe | Keeps the en-route timeline: vitals, treatments, times, as the crew reports them. |
| destination-matcher | Matches the patient to a destination using live capacity and diversion status; flags a destination that goes on diversion mid-ride. |
| handoff-messenger | Builds the handoff record before arrival. The only agent that may post across worlds: incoming patient summaries and incident summaries, counts and categories only. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`,
one line, pointing at a stored record. A pack alert adds a privacy
class and an urgency class (see `worlds/README.md`); only alerts
marked summary may cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| destination-diverted | warning | local | no | Hospital id, its new diversion state, the unit id that must pick a new destination. No patient information. |
| critical-eta | warning | summary | yes | Destination hospital id, patient severity class, estimated arrival window. No name or identifiers. |
| multi-casualty-declared | critical | summary | yes | Incident id, casualty counts by severity, transport units committed. Counts only. |
| ride-record-gap | warning | local | no | Unit id and which expected timeline entries are missing. Contents never ride the line. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Patient names and identifiers, the full vitals record and treatment notes, ride audio and scribe working notes, the complete handoff record until it is delivered to the receiving hospital system. |
| bus_summary | Incoming patient severity class and complaint category (no identifiers), casualty counts by severity on multi-casualty incidents, transport unit counts and destinations. |

Patient data stays in the vehicle and the fleet system. What
crosses the bus is what another world needs to prepare: how many,
how severe, how soon. Never who.

## Cross-world messages

Sends:

- To **hospital**: `incoming-patient-summary` (severity class,
  chief complaint category, treatments given in category form,
  arrival window). Never carries patient names, patient
  identifiers, dates of birth, addresses, or images or video.
- To **fdny**: `multi-casualty-summary` (incident id, casualty
  counts by severity, transport units committed). Same
  never-carries list.
- To **hospital**: `multi-casualty-summary` (incident id, counts
  by severity, destination hospitals, transport units still
  needed). Same never-carries list.

Receives:

- From **hospital**: `capacity-status` (capacity state, staffed
  bed counts, diversion changes as they happen).
- From **nypd**: `road-closure-summary` (closure segments and
  states affecting the route).
- From **fdny**: `incoming-casualty-summary` (incident id and
  casualty counts by severity on a shared incident).

## Firstboot config

Per-vehicle personalization happens at firstboot, not in a
per-vehicle image. One EMS image serves the whole fleet; each box
learns which unit it is during first boot.

| Field | Label | Required |
|---|---|---|
| agency_name | Agency or service name | yes |
| unit_id | Unit id for this vehicle or fleet installation | yes |
| crew_roster | Crew roster for this unit | yes |
| medical_director_contact | Medical director or admin contact | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | Multi-casualty declarations. Preempts everything else on the bus. |
| 2 | urgent | Destination diversions, critical patient arrival warnings. |
| 3 | routine | Capacity checks, ride record completeness. |
| 4 | digest | Delivered handoff records, end-of-shift summaries. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts,
privacy classes, cross-world messages, firstboot fields, and
urgency classes. It does not contain a working EMS system, and
nothing in it should be read as one.
