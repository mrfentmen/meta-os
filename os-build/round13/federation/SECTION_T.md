# Section T — federation drills (R13-476..490)

Run: `node federation/sim.mjs`. Machine record: `F_DRILLS.json`; append-only ledger: `ledger.jsonl`.

Counts: {"drills":15,"records":19,"handoffs":4} · all records labelled SIMULATED: true · handoff pairs linked: true

**There is no federation module in this repo.** `federation/sim.mjs` is a simulator over eleven named worlds; every record it writes carries `label: "SIMULATED"` and `simulated: true`. The drills prove the harness and the labelling, not a single real dispatch.

| task | drill | target | records | correlation |
|---|---|---|---|---|
| R13-476 | routine | nypd | 0 | — |
| R13-477 | routine | fdny | 1 | — |
| R13-478 | routine | ems | 2 | — |
| R13-479 | routine | hospital | 3 | — |
| R13-480 | routine | dsny | 4 | — |
| R13-481 | routine | dep | 5 | — |
| R13-482 | routine | doe | 6 | — |
| R13-483 | routine | mta | 7 | — |
| R13-484 | routine | musica | 8 | — |
| R13-485 | routine | officina | 9 | — |
| R13-486 | routine | science-lab | 10 | — |
| R13-487 | handoff | fdny -> hospital | 11, 12 | corr-11-fdny-hospital |
| R13-488 | handoff | nypd -> fdny | 13, 14 | corr-13-nypd-fdny |
| R13-489 | handoff | dsny -> dep | 15, 16 | corr-15-dsny-dep |
| R13-490 | handoff | mta -> doe | 17, 18 | corr-17-mta-doe |
