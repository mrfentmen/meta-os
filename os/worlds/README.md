# World packs

Meta World is one small core plus loadable world packs. The core
is what already lives in this repo: the bus, the job board, the
watcher pattern, memory, identity and badges, and budget. A world
pack adapts that core to one kind of institution: a fire
department, a police department, a hospital, an ambulance
service, the coding crew itself. Each institution type gets one
bootable image built from the same core image with its pack baked
in; each building personalizes its own box at firstboot. The
structure was locked by Del on 2026-10-27 and is recorded in
`plan/META_WORLD.md`.

A pack is a definition, not a running system, until its status
says otherwise. Statuses are honest and are enforced in the
manifest: `spec` means definition only, `partial` means some
runtime exists and the pack doc says which parts, `built` means
the runtime exists and is tested.

## The pack contract

Every pack lives in `worlds/<pack>/` and must contain:

1. **PACK.md**: the human-readable definition: purpose, what it
   watches, agent roster, alerts, privacy classes, cross-world
   messages, firstboot fields, urgency classes, and an honesty
   label.
2. **pack.json**: the machine-checkable manifest with the same
   content in structured form. `python3 worlds/validate_pack.py`
   must pass on it.

And every pack must satisfy these rules:

- **Watchers, agents, alerts are declared.** Watchers say what
  they watch and what feeds them. Agents have a nick and a role;
  an agent's `serves` list may only name watchers in the same
  pack. Exactly one agent in a pack is the cross-world messenger;
  the rest never post outside their own world.
- **Alerts speak the shared alert language.** Alert lines follow
  the FND-020 freeze in `intel/README.md`
  (`ALERT:<id> <severity> <kind>`, extended here, not replaced):
  each alert adds a privacy class and an urgency class. Kinds are
  single lowercase tokens.
- **Privacy classes are structural.** Every data type in a pack
  is `local_only` or `bus_summary`. Only summaries cross the bus.
  An alert may cross only if its class is summary, and every
  cross-world send declares a non-empty `never_carries` list.
  The validator refuses manifests that break this; it is not a
  promise in prose.
- **Cross-world messages are declared both ways.** What the pack
  sends (to whom, what it carries, what it never carries) and
  what it receives (from whom, what it carries).
- **Firstboot fields are declared.** Department or facility
  name, the building or unit identity, the roster, the admin
  contact, the bus room. No per-building images; firstboot is
  where a box learns which building it is.
- **Urgency classes come from the shared set**, so one world's
  life-safety message outranks every world's routine traffic on
  the shared bus:

| Rank | Class | Meaning |
|---|---|---|
| 1 | life-safety | Someone may die or is unaccounted for. Preempts everything. |
| 2 | urgent | Act in minutes: checks due, windows closing, diversions. |
| 3 | routine | State changes and completeness notes. |
| 4 | digest | Sealed records and end-of-shift summaries. |

- **Plain English on every surface.** Every alert and brief a
  pack produces is written for the nurse, the officer, the
  driver, not for an engineer. No pack ships a surface that
  needs a manual to read at 3 AM.

## Federation rules (all packs)

- Institutions join the same bus room; their agents communicate
  across institutions through it. Machines never connect directly
  to each other.
- Raw data stays inside the institution that made it. Only
  summaries and alerts cross the bus, under the privacy rules
  above.
- Every world runs offline first: if the connection dies, the
  world keeps working on its own box and syncs when the line
  comes back.
- A human can always override a pack alert, and the override is
  recorded with the record it overrode.
- Jobs and messages between worlds are signed, and every foreign
  agent arrives wearing its capability badge. The default posture
  is closed.

## Registry

| Pack | Institution | Status | Notes |
|---|---|---|---|
| crew | The Meta World coding crew (Pax, Rowan, Hana, Milo, Buffy) | BUILT | The original build in this repo: intel layer, job queue, watchdog, dashboard, world view. The reference implementation every other pack is modeled on. |
| fdny | Fire department | PARTIAL (PAR clock runtime), landed 2026-10-27 | Fireground accountability, PAR timing, incident timeline. The PAR clock runtime (`worlds/fdny/runtime/par_clock.py`) is built and pinning-tested: per-crew PAR countdown, overdue escalation to a life-safety alert in the frozen wire format, human-fed state on disk. It is an accountability aid, not a commander. Everything else remains definition only; no runtime runs a real fire department. |
| nypd | Police department | SPEC, landed 2026-10-27 | Precinct board, roll call, verified incident record. Definition only; no runtime. |
| hospital | Hospital | SPEC, landed 2026-10-27 | Lead watcher is the IV guardian (drip rate, bag level, insertion site, empty-bag pre-alarm), plus the turn watcher, waiting room watcher, and code recorder. Definition only; no runtime. |
| ems | EMT and ambulance service | SPEC, landed 2026-10-27 | Ride timeline, destination matching against live hospital capacity, handoff record before arrival. Definition only; no runtime. |
| dsny | Sanitation department | SPEC, landed 2026-10-28 | Route completion and missed-collection watch, truck health and stranded-crew watch, storm plow and spreader operations with hours-on-shift flags, sealed collection and storm records; storm status crosses to nypd and mta as counts. Definition only; no runtime. |
| doe | Public school | SPEC, landed 2026-10-28 | Staffing and substitute coverage watch, certification and filing compliance clock, sealed duty record; school operating status crosses to civic worlds as counts, student data never leaves the building. Definition only; no runtime. |
| mta | Transit authority | SPEC, landed 2026-10-28 | Headway gap watch, rolling stock health, platform crowd states where feeds exist, sealed incident timeline; casualty counts cross to ems and nypd, service state to civic worlds, imagery and rosters local only. Definition only; no runtime. |
| dep | Water and sewer utility | SPEC, landed 2026-10-28 | Pump station overflow-risk watch, water quality exceedance elevation, outfall and overflow watch against rainfall, sealed operations record; advisory state crosses to doe and mta as zone counts, customer records never leave the utility. Definition only; no runtime. |

## Checking a pack

```
python3 worlds/validate_pack.py
```

validates every `worlds/*/pack.json` against this contract, and
`tests/test_worlds_pack.py` holds it to that in the suite.
