# AGENT LAYER TASKS — build-out (from AGENT_LAYER_SPEC.md)

Order matters inside each section. Pax merges; Milo gates.
Status words: TODO / DOING / DONE / BLOCKED (name the blocker).

## A. Foundations (Pax + Milo)
A1 DONE — Spec on main (AGENT_LAYER_SPEC.md).
A2 DONE — Registry format + crew entries drafted (agents/registry.json).
A3 Milo: gate-1 the spec against MILO_OS_BUILDOUT C1–C22 — every C
   answered or named open, in one table.
A4 Milo: scoreboard rows for each spec section with its proof
   obligation (spec §14) — UNIMPLEMENTED until a drill exists.

## B. Host runtime v1 (Pax builds, Buffy hardens)
B1 DONE — Runtime slice 1 (agents/runtime.mjs): registry load,
   real spawn, graceful->hard kill, STOP file, ledger JSONL,
   budget caps (actions + wall-clock), watch poll/compare.
B2 DONE — Runtime tests 6/6 on a fresh tree copy (Pax, 2026-11-02).
B3 Buffy: failure injection on the runtime — kill mid-write, ledger
   torn line, registry with a bad entry, budget race. Report format.
B4 Buffy: restart semantics — runtime dies, runs marked, baton
   records survive (spec §12 drill).
B5 Pax: job records — spawn writes the assembled brief (orders,
   skills, budget, deadline) into the run dir before start (spec §4).

## C. Wake layer (Pax + Rowan)
C1 Pax: relay-watchman v1 — polls room 1 + the job board file; on a
   named job, spawns the agent with its brief (spec §4).
C2 Pax: timer sweep fallback — agents wake on cadence to sweep.
C3 Pax: watchman watchdog — a missed heartbeat is a top-tier alarm.
C4 Rowan: image lane — agent programs pre-installed in the carrier
   image at bake/firstboot; nothing installs mid-job (spec §4).
C5 Fleet: Tailscale join in the image; bell rings across machines
   (version two — after C1 proves on one machine).

## D. Baton pass (Milo + Pax)
D1 Milo: baton record format (state, artifacts, next step) — spec.
D2 Pax: watchman composes the continuation brief from the record.
D3 Drill: same-program continuation in-window; zero duplicated file
   changes (spec §5 proof). Cross-program pass is the stretch line.

## E. Host the proven loops (owners keep their lanes)
E1 Imperium patrol becomes a registry agent (manifest + budget +
   ledger) — behaviour unchanged, receipts now layer-shaped.
E2 Musica studio session loop as a registry agent (Hana's records).
E3 Officina faber loop as a registry agent (STOP file already fits).
E4 The cadence watches (bus/hourly/gateway) expressed as watch
   targets on one registry agent — Custos's rounds, layer-shaped.

## F. Kernel road (Rowan, post-demo, no claims until booted)
F1 Spec the agent syscalls beyond the F1 table (Milo C10 feeds this).
F2 Kernel spawn/kill for agent tasks behind the gate + boot log.
F3 Registry/ledger contracts move down unchanged (spec §2).

## G. Proof pack (Milo, for the submission + beyond)
G1 Hands-free drill: dark machine lights up and starts work
   unprompted — filmed (the boss's demo beat from 2026-10-23).
G2 Budget drill: a run hits its cap, stops, receipt shows why.
G3 Watch drill: one change wakes; one quiet hour does not.
G4 AGENTIC_PROOF.md updated from the drill logs, nothing else.
