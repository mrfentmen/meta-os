# OC1B-301 wave-2 gap list (from os-build/logs/wave2-sec5.md, in its order)

Wave-2's three live loops (R5 vigiles, R6 ignis, medicus) all ran on
STAGED fixture cameras (cam-a/b/c) with staged frames, pre-judge-reasons
timeline shape, and the older auto dispatch package (no service block).
Every item below was unproven, partial, or scripted-only in that sense.

| # | Gap | Status after §13 | Closing artifact |
|---|---|---|---|
| G1 | Patrol over the REAL DOT camera list (wave-2: staged cam-a/b/c only) | CLOSED | OC1B-303/304: camera_source nyctmc-live, 975 cameras, 10-check batch |
| G2 | Incident from a NATURAL flag on a live camera, followed end to end | OPEN — 0 flags in 22 production checks; honest zero, not a staged substitute | (no-natural-flag line in OC1B-imperium-live.md) |
| G3 | Judge reasons recorded on the timeline (wave-2 R5/R6 pre-reasons shape) | CLOSED | staged + path timelines carry judge_reasons (e.g. inconclusive-path.json) |
| G4 | Service-routed dispatch package (wave-2 old auto shape, no service block) | CLOSED | sim-8488ea6982679dd0, service_route /police, SIMULATED police endpoint; §9 loopback /fire |
| G5 | BOLO from recorded descriptions + purge-on-false-positive | CLOSED | os-build/logs/oc1b-imperium/bolo-purge.json |
| G6 | Cleared / inconclusive / yellow close paths with no-dispatch proof | CLOSED | cleared-path.json, inconclusive-path.json, yellow-path.json |
| G7 | Per-incident budget governor + patrol pause + supervisor pause | CLOSED | budget-stop.json (stop: max_actions 8); 316/317 heartbeat excerpts |
| G8 | judge_mode "model" on a live incident ruling | OPEN — reasoning-token starvation at the specified default budgets (measured live 1598/1600 + 1198/1200); deterministic fallback PROVEN in its place; defect filed in §9 proof | judge-model-timeline.json (OC1B-215 UNPROVEN) |

## OC1B-323 blockers (one line each)
- G2: no live camera flagged in 22 production checks (10-batch + 3 SAM batch + 8 killed-run checks + 1 once) — a flag cannot be manufactured; staged runs cover the pipeline instead, labelled STAGED.
- G8: crew.py's specified judge call (chat_text defaults, max_tokens 1200) starves on reasoning tokens; raising the budget is the crew lane's call, not this section's.

## OC1B-324 section record (wave-3 §6 task 58 shape)
Gap list above; verdict per gap CLOSED/OPEN as stated. The wave-2 scripted-only core (G1, G3, G4, G5, G6, G7) is now proven against live or production-shaped runs; what remains open (G2, G8) is named with its blocker, not hidden.
