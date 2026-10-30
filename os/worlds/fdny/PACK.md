# FDNY world pack: fire departmentStatus: **PARTIAL.** The PAR clock runtime is built and pinning-tested; every other declared watcher remains definition only. This pack was SPEC (NOT BUILT) until 2026-10-28, when Del ordered the first real runtime built; the runtime record below says exactly what runs and what does not. The manifest (`pack.json`, checked by `worlds/validate_pack.py`) and this document are the definitions; no runtime code in this pack runs a real fire department, directs real crews, or replaces any existing accountability system.

## Runtime status (what runs, honestly)

| Part | Status | Proven | Not proven |
|---|---|---|---|
| `worlds/fdny/runtime/par_clock.py`: the PAR clock | BUILT, pinning-tested (18 tests) | Pure core on fixtures: per-crew interval countdown, `par-check-due` warning once per cycle, `crew-unaccounted` critical escalation past the grace window, dedupe per cycle-due moment, timeline sealed on disk, FND-020 alert lines `ALERT:<id> <severity> <kind>` | Not yet run on a booted Meta OS image, not a systemd unit, never exercised in a real station; the interval/grace values are configuration, not doctrine |
| Accountability board watcher, air estimates, roster board, incident scribe | SPEC only | Nothing | No runtime exists |

The clock is an accountability aid, not a commander: the human accountability officer feeds it (enter, complete, exit) and acts on its alerts. It completes a PAR only when a human says so; an unanswered radio is never mistaken for an answer. It never orders, never dispatches, never invents a location.

## Purpose

Fireground accountability today is a board, tags, and memory: the
accountability officer tracks who is inside a structure, and PAR
(personnel accountability report) checks run on a clock the
officer keeps in his head while everything else is happening.
This pack defines the agent crew that carries that load inside a
Meta World installation: a watcher on the accountability board, a
PAR timer that never gets distracted, a scribe that keeps the
incident timeline as it happens, and a messenger that warns the
hospital and EMS worlds when casualties are coming, in counts
only.

The pack advises and records. Command decisions stay with the
incident commander, and every override of a pack alert by a human
is recorded with the incident timeline.

## What it watches

- **Accountability board.** Which members are inside the
  structure, entry time, elapsed interior time, and estimated
  remaining air, against the incident clock.
- **PAR timer.** When the next PAR check falls due for each
  interior crew, and whether it completed.
- **Roster board.** Apparatus and crew roster state: on scene,
  committed, available, out of service, and who is riding each
  unit.
- **Incident timeline.** Dispatch, arrival, entry, PAR results,
  mayday events, and all-clear, kept in order as the verified
  record of the incident.

## Agent roster

| Agent | Job |
|---|---|
| accountability-watcher | Runs the accountability board and the PAR timer. Raises the pack's alerts. Advises the incident commander; it never orders a crew. |
| incident-scribe | Keeps the incident timeline as it happens and seals it at all-clear. |
| roster-keeper | Keeps apparatus and crew roster state current across the incident. |
| handoff-messenger | The only agent that may post across worlds. Sends casualty counts (never names) to hospital and EMS worlds; receives capacity and scene summaries. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`,
one line, pointing at a stored record. A pack alert adds a privacy
class and an urgency class (see `worlds/README.md`); only alerts
marked summary may cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| par-check-due | warning | local | no | Crew id and the PAR due time. |
| air-low-estimate | warning | local | no | Crew id and estimated minutes of air remaining, marked as an estimate. |
| crew-unaccounted | critical | local | no | Crew id and last known location. Member names never ride any line. |
| mayday-declared | critical | summary | yes | Incident id, mayday declared, casualty counts by severity. No names. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Member names and assignments, interior positions, per-member air estimates, the full incident timeline before review, radio transcripts and scribe notes. |
| bus_summary | Casualty counts by severity on a mayday or multi-casualty incident, unit availability counts for mutual aid, incident id and type. |

The rule is structural, not a promise: the validator refuses any
alert that crosses the bus without the summary class, and every
cross-world send in `pack.json` declares what it never carries.

## Cross-world messages

Sends:

- To **hospital**: `incoming-casualty-summary` (incident id,
  casualty counts by severity, arrival window estimate). Never
  carries patient names, patient identifiers, member names, or
  medical details of any individual.
- To **ems**: `incoming-casualty-summary` (incident id, counts by
  severity, staging location). Same never-carries list.

Receives:

- From **hospital**: `capacity-status` (emergency department
  capacity and diversion status, counts and states).
- From **nypd**: `scene-safety-summary` (road closures and
  perimeter state affecting apparatus access).
- From **ems**: `transport-status` (transport units committed and
  destination hospitals, as counts).

## Firstboot config

Per-building personalization happens at firstboot, not in a
per-building image. One FDNY image serves every firehouse; the
box learns which house it is during first boot.

| Field | Label | Required |
|---|---|---|
| department_name | Department name | yes |
| station_name | Station or house name | yes |
| battalion | Battalion or division | no |
| unit_roster | Unit roster: apparatus and the members riding each unit | yes |
| par_interval_minutes | PAR check interval in minutes | yes |
| command_contact | Chief or admin contact for this installation | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | Mayday and crew-unaccounted events. Preempts everything else on the bus. |
| 2 | urgent | PAR checks due, air estimates running low. |
| 3 | routine | Roster and unit state changes. |
| 4 | digest | Sealed incident timeline, end-of-incident summary. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts,
privacy classes, cross-world messages, firstboot fields, and
urgency classes. It does not contain a working fire department
system, and nothing in it should be read as one.
