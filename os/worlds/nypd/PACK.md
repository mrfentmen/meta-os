# NYPD world pack: police department

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this
document. No runtime code in this pack runs a real police
department, dispatches a real unit, or holds a real case record.
Del ordered this pack on 2026-10-27 as one of the first two
institutional world packs for Meta World.

## Purpose

A precinct runs on state that lives in too many places at once:
which units are available, who is on tour, and the timeline of
each incident, reconstructed afterward from logs and memory. This
pack defines the agent crew that keeps that state in one place
inside a Meta World installation: a board keeper for unit status,
a roster keeper for roll call, a scribe that keeps the incident
timeline as a verified record while the incident is live, and a
liaison that shares responder-safety summaries with the fire and
EMS worlds.

The pack advises and records. Decisions stay with supervisors and
command, and every override of a pack alert by a human is
recorded with the incident timeline.

## What it watches

- **Precinct board.** Unit status and availability: available,
  assigned, on a scene, or out of service, kept current as status
  reports arrive.
- **Roll call.** Who is on tour, which units checked in, and
  which checks are missed.
- **Verified record.** The incident timeline (calls, assignments,
  arrivals, clearances) kept in order, with gaps flagged while
  they can still be corrected.

## Agent roster

| Agent | Job |
|---|---|
| board-keeper | Keeps the precinct board current: unit status and availability. |
| roster-keeper | Runs roll call against the roster; tracks missed checks and unit status changes. |
| record-scribe | Keeps the incident timeline and the verified record; flags gaps in the record. |
| liaison-messenger | The only agent that may post across worlds. Sends road closure and scene safety summaries (never case details); receives fire, EMS, and hospital summaries. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`,
one line, pointing at a stored record. A pack alert adds a privacy
class and an urgency class (see `worlds/README.md`). Every alert
in this pack is local: none crosses the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| unit-check-missed | warning | local | no | Unit id and the missed check time. |
| unit-unresponsive | critical | local | no | Unit id and minutes since last confirmed contact. A supervisor decides what happens next. |
| roll-call-missed | warning | local | no | Roster entry id and tour. The roster itself never leaves the precinct system. |
| record-gap | warning | local | no | Incident id and which expected record entries are missing. Record contents never ride the line. |

## Privacy classes

Police records law governs everything in this pack. Case records
are the most restricted data a Meta World installation can hold,
and the pack is designed so they never move.

| Class | Contents |
|---|---|
| local_only | Case records and the verified incident record contents, unit assignments tied to named officers, the roll-call roster with officer names, radio transcripts and scribe notes, anything identifying a victim, suspect, or witness. |
| bus_summary | Road closure segments and states for responder routing, scene perimeter and hazard summaries for shared incidents, incident id and type on shared incidents. |

Data minimization is the design rule: a cross-world message
carries the least a receiving crew needs to act (a road is
closed, a perimeter moved), and never the case information
behind it.

## Cross-world messages

Sends:

- To **fdny**: `road-closure-summary` (affected road segments,
  closure state, estimated duration) and `scene-safety-summary`
  (perimeter state and hazards for other responders). Never
  carries case details, suspect or victim names, any personal
  identifiers, or record contents.
- To **ems**: `road-closure-summary` (same shape, same
  never-carries list).

Receives:

- From **fdny**: `incoming-casualty-summary` (incident id, type,
  casualty counts by severity).
- From **ems**: `transport-status` (transport counts and
  destination hospitals, counts only).
- From **hospital**: `capacity-status` (diversion state changes
  that affect where a scene clears to).

## Firstboot config

Per-building personalization happens at firstboot, not in a
per-building image. One NYPD image serves every precinct; the box
learns which precinct it is during first boot.

| Field | Label | Required |
|---|---|---|
| precinct_name | Precinct or command name | yes |
| unit_roster | Unit roster: units and their assignments | yes |
| tour_schedule | Tour or shift schedule used by roll call | no |
| unit_check_interval_minutes | Unit status check interval in minutes | yes |
| command_contact | Command or admin contact for this installation | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | A unit unresponsive past its threshold. Preempts everything else on the bus. |
| 2 | urgent | Missed unit checks, scene safety changes at a live incident. |
| 3 | routine | Board state, roll-call results, record completeness notes. |
| 4 | digest | Sealed incident record, end-of-tour summary. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts,
privacy classes, cross-world messages, firstboot fields, and
urgency classes. It does not contain a working police system, and
nothing in it should be read as one.
