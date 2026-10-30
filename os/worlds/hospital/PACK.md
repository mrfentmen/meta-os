# Hospital world pack

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this
document. No runtime code in this pack watches a real patient,
counts a real drip, or replaces any hospital system or clinical
judgment. Del ordered this pack on 2026-10-27, in the same batch
as the FDNY, NYPD, and EMS packs.

## Purpose

A hospital floor runs on checks that happen by eye, on rounds,
when someone has time: is the IV bag about to run dry, did the
patient actually get turned, has anyone re-checked the waiting
room since the door. This pack defines the agent crew that
carries those watches inside a Meta World installation, so the
nurse hears about the bag before the pump alarm, the turn is
verified instead of trusted, and the waiting room is re-triaged
continuously instead of once at the door.

The lead watcher is the IV guardian. The pack advises and
records. Clinical decisions stay with the care team, and every
override or dismissal of a pack alert by a human is recorded.

## What it watches

- **IV guardian (lead watcher).** The IV pole, from a camera that
  stays in the building: drip chamber rate counted from the feed,
  bag level tracked against the set rate, the insertion site
  watched for swelling that suggests infiltration, and a
  projected empty time, so the nurse gets a pre-alarm (bag empty
  in about 20 minutes) instead of a pump alarm after the fact.
- **Turn watcher.** Patient turning for pressure injury
  prevention: whether a real turn happened inside each two hour
  window, verified from the bed watch, with a reminder before the
  window closes.
- **Waiting room watcher.** The emergency department waiting
  room: continuous re-triage of people waiting, flagging anyone
  whose visible condition worsens (slumping, distress, no
  response when called) between triage at the door and being
  seen.
- **Code recorder.** Code events: the timeline of a
  resuscitation as it happens, times of drugs given, shocks
  delivered, and interventions, kept in order as the verified
  record of the event.

## Agent roster

| Agent | Job |
|---|---|
| iv-watcher | Runs the IV guardian: drip counts, bag projections, insertion site watch. Raises the pack's IV alerts for the nurse. |
| turn-watcher | Verifies patient turns and reminds the care team before the two hour window closes. |
| waiting-room-watcher | Re-triages the waiting room continuously and flags visible deterioration. |
| code-scribe | Keeps the code event timeline: times, drugs, shocks, interventions, in order. |
| capacity-messenger | The only agent that may post across worlds. Publishes capacity and diversion status; receives incoming patient summaries. Never sends patient information. |

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`,
one line, pointing at a stored record. A pack alert adds a privacy
class and an urgency class (see `worlds/README.md`); only alerts
marked summary may cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| iv-bag-running-dry | warning | local | no | Pole id and projected minutes until the bag is empty, marked as a projection. |
| iv-infiltration-suspected | critical | local | no | Pole id and the observed change behind the flag. A nurse confirms or dismisses it in person; the dismissal is recorded. |
| iv-rate-anomaly | warning | local | no | Pole id, set rate, counted rate. |
| turn-window-closing | warning | local | no | Bed id and minutes left in the turn window. |
| turn-missed | critical | local | no | Bed id and the time the window closed without a verified turn. |
| waiting-room-deterioration | critical | local | no | Waiting area zone and the observed change. No identity; no image leaves the building. |
| diversion-status-change | warning | summary | yes | Capacity state (open, busy, diverting) and staffed bed counts. No patient information of any kind. |

## Privacy classes

Health data rules this pack. The classes are the strictest in
the registry, and they are structural: the validator refuses any
alert that crosses the bus without the summary class.

| Class | Contents |
|---|---|
| local_only | Raw camera video of poles, beds, and the waiting room; vitals and any measurement tied to a patient; insertion site observations; turn verification evidence; code event timelines until reviewed and sealed; anything that identifies a patient. |
| bus_summary | Emergency department capacity state and staffed bed counts, diversion status changes, aggregate counts (patients waiting, codes this shift) with no identifiers. |

Patient identifiers never appear in a bus message from this
pack: not in alerts, not in cross-world sends, not in digests.
The capacity messages other worlds depend on carry states and
counts, and nothing else.

## Cross-world messages

Sends:

- To **ems**: `capacity-status` (capacity state and staffed bed
  counts). Never carries patient names, patient identifiers,
  diagnoses of any individual, or images or video.
- To **fdny**: `capacity-status` (same shape, for incident
  planning). Same never-carries list.

Receives:

- From **ems**: `incoming-patient-summary` (severity counts, a
  chief complaint category, arrival window; no name, no date of
  birth, no identifiers).
- From **fdny**: `incoming-casualty-summary` (incident id and
  casualty counts by severity).

## Firstboot config

Per-building personalization happens at firstboot, not in a
per-building image. One hospital image serves every facility; the
box learns which facility and ward it is during first boot.

| Field | Label | Required |
|---|---|---|
| facility_name | Facility name | yes |
| unit_ward | Unit or ward this installation serves | yes |
| pole_assignments | Camera and pole assignments: which camera watches which IV pole and beds | yes |
| turn_window_minutes | Patient turn window in minutes (standard is 120) | yes |
| charge_nurse_contact | Charge nurse or admin contact for this installation | yes |
| room_name | Bus room this installation joins | yes |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | Code events, suspected infiltration, waiting room deterioration. Preempts everything else on the bus. |
| 2 | urgent | Turn windows closing, diversion changes, bags about to run dry. |
| 3 | routine | Rate anomalies, capacity updates. |
| 4 | digest | Sealed code timelines, end-of-shift summaries. |

## Honesty label

SPEC / NOT BUILT. This pack defines watchers, agents, alerts,
privacy classes, cross-world messages, firstboot fields, and
urgency classes. It does not contain a working hospital system,
and nothing in it should be read as one.
