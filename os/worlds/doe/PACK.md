# DOE world pack: public school

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this document.
No runtime code in this pack runs a real school, assigns real
teachers, or touches any student record. Del ordered the NYC
institutional pack set on 2026-10-28; this pack is one of it.

## Purpose

A school day is decided by coverage: who is out, who covers, and
whether the building opens staffed. Today that lives in call-out
messages, a substitute pool list, and a chapter lead's phone. This
pack defines the agent crew that carries that load inside a Meta World
installation: a shift-board watcher that knows at 6 AM whether the
school opens short-staffed, a coverage scribe that fills and records
every substitute assignment, a compliance watcher on certification and
filing windows, and a messenger that publishes school operating status
to the district world as counts.

The pack advises and records. Assignments and personnel decisions stay
with the principal, the chapter lead, and the union contract. Student
data never appears in any pack record; staff names and records are
local to the school, always.

## What it watches

- **Shift board.** Which classroom and duty posts are staffed today,
  which run short, and how many periods each shortfall touches.
- **Sub assignments.** Every unfilled assignment against its countdown
  to period start, and every offer made but not accepted.
- **Compliance clock.** Certification expiry per staff member and
  filing or report windows per building, reminded before each closes.
- **Duty record.** Assignments offered, filled, and refused per period
  per day, sealed at day end as the verified record.

## Agent roster

| Agent | Job |
|---|---|
| shift-watcher | Runs the shift board and raises coverage shortfalls. Advises the chapter lead and admin; it never assigns a teacher. |
| duty-scribe | Fills assignment tracking and keeps the duty record, sealed at day end. |
| deadline-watcher | Filters and escalates the compliance clock for each staff member and filing. |
| union-messenger | The only agent that may post across worlds. Publishes school status as counts; receives transport, storm, and advisory summaries. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`, one
line, pointing at a stored record. Only alerts marked summary may
cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| assignment-unfilled | warning | local | no | School id, unfilled assignment id, minutes until period start. |
| certification-lapsing | warning | local | no | Teacher id and certification type, days remaining. |
| filing-window-closing | warning | local | no | School id, filing id, days left. |
| coverage-shortfall | warning | local | no | School id, covered versus uncovered periods as counts. |
| school-status-summary | warning | summary | yes | Operating state and head counts by building, counts only. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Teacher and staff names, assignments, and records; certification and filing records; anything identifying a student, including names, grades, or assessments; substitute coverage details before review. |
| bus_summary | School operating states as counts; head counts by building; coverage shortfall counts. |

The rule is structural, not a promise: the validator refuses any
cross-bus line that is not a summary, and every cross-world send
declares what it never carries.

## Cross-world messages

Sends:

- To **dsny**: `school-status-summary` (open, short-staffed, closed,
  head counts by building). Never carries student data, staff names,
  records, or addresses.

Receives:

- From **mta**: `service-diversion` (transport states affecting student
  arrival).
- From **dsny**: `road-clearing-status` (storm clearing affecting
  school opening decisions).
- From **dep**: `water-advisory` (boil or pressure advisories affecting
  building operations).

## Firstboot config

Per-school personalization happens at firstboot, not in a per-school
image. One DOE image serves every school; the box learns which school
it is during first boot.

| Field | Label | Required |
|---|---|---|
| school_name | School or building name | yes |
| district_name | District or community school district | yes |
| staff_roster | Staff roster for this building | yes |
| coverage_window_minutes | Minutes before a period an unfilled assignment is flagged | yes |
| chapter_contact | Chapter leader or union rep contact | yes |
| admin_contact | School admin contact | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | A building emergency affecting students or staff. Preempts everything. |
| 2 | urgent | Unfilled assignments near period start, lapsing certifications, day-of shortfalls. |
| 3 | routine | Filing windows and roster state changes. |
| 4 | digest | Sealed duty record, end-of-day summary. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts, privacy
classes, cross-world messages, firstboot fields, and urgency classes.
It does not contain a working school system, and nothing in it should
be read as one.
