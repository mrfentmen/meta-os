# BUFFY TASKS — ROUND 8 (Pax, boss order 2026-11-02)

Round 7's face services are MERGED (48 files, tree-verified).
Round 8 builds on what landed this morning: the agent layer is
real code now (agents/), Aegis exists, Hands-Free is greenlit.
Work in order. Branch: buffy/layer1-goose-services (or a fresh
buffy/round8). Records in os-build/layer1/ as always. Call your
checkpoint on room 1 when a section closes — Pax merges code at
checkpoints, records with them.

## A. Harden the agent runtime (agent tasks B3/B4 — yours)
A1 Failure-injection pack against agents/runtime.mjs + watchman:
   kill mid-write, torn ledger line, bad registry entry, STOP
   during spawn, budget race, job file half-written. One report:
   what broke, what held, what needs a fix (Pax fixes runtime).
A2 Restart semantics drill: runtime dies mid-run — runs marked,
   baton records survive, watchman resumes without double-spawn.
   Drill log is the deliverable.
A3 Watchman watchdog (agent task C3): heartbeat file + a checker
   that raises the top-tier alarm line when the beat stops.

## B. Supervisor for real (Round 7 D, now possible)
The supervisor service stops being a simulation: it drives the
agent runtime's spawn/kill for real processes.
B1 Supervisor -> runtime bridge design (one page, in layer1).
B2 Bridge built: boot order starts agents through the runtime;
   STOP windows honoured end to end (your 00d895d bug class).
B3 Drill: three agents up, one budget-killed, one STOP-filed,
   one completes — ledger lines are the proof.

## C. Hands-Free services (new program, greenlit)
Voice later; the service shapes now, text-first:
C1 Order intake: a text inbox file becomes watchman job files
   (one line = one order; agent named in the line).
C2 Brief speaker: run results + ledgers compose into ONE
   speakable brief (short sentences, no jargon, numbers first).
C3 Approval inbox: a yes/no drop lands in the run's ledger as
   the boss's word, timestamped. Nothing acts without it where
   the standing announce-before-send rule applies.

## D. Aegis service pack (new system, named 2026-11-02)
Spec: os-build/AEGIS_SPEC.md. Services only — the data calls are
Pax's lane through the boss's MCP servers.
D1 Manifest collector service: walks a tree, emits every package
   manifest path + ecosystem (data out only, no network).
D2 Findings record service: severity, evidence, source, run id —
   the Aegis report shape, append-only.
D3 Watch-target pack: repo-tip + page-change targets in the
   agent layer's watch shape.

## E. Round 7 remainder (carried, close them)
E1 The 49 limits: close the rest; final count stated in COUNTS.
E2 Deepen x4 on the services still shallow (name which).
E3 Corpus integrity: 25 service READMEs (Round 7 E, carried).

## F. Lobster host pack (C9 — LOBSTER_BINDING says NOT BUILT)
F1 Minimal Lobster host: runs ONE Lobster program against the
   merged services, host log as proof.
F2 Update LOBSTER_BINDING.md from NOT BUILT to exactly what
   exists, nothing more.

## Rules (unchanged)
No boot claims — RUNS means host process, say which surface.
Simulated stays labelled. Records name their evidence. When a
section closes, post the checkpoint on room 1 and stop there
until Pax merges.
