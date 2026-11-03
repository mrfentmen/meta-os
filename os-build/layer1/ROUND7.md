# Round 7 — the face layer, the supervisor under load, and the counts made honest

> Counts in this file are as of the round it records. Live numbers: `COUNTS.md`.

Branch `buffy/layer1-goose-services`, 2026-11-02. This is the report of what this round
changed and what it still cannot claim. The live numbers are in `COUNTS.md`; the submission
page is `SERVICES_FINAL.md`; neither is quoted from memory here.

## What was asked, and what exists now

| Item | Delivered | Evidence |
|---|---|---|
| Supervisor deep dive | failure injection, boundary sweep, restart semantics, contract page | `services/tests/t83_sup_deep.goose`, `contracts/supervisor.md` |
| Session deep dive | same four | `t84_session_deep.goose`, `contracts/session.md` |
| Net deep dive | same four | `t85_net_deep.goose`, `contracts/net.md` |
| Six face services | settings, wallpaper, dock, dashboard feed, updater client, board client — code, tests, contract pages | `services/{settings,wallpaper,dock,dashboard,updater_client,board}/`, `t86`–`t91` |
| Manifest, boot order, matrix | all six registered in `services.json`, in the boot table (orders 23–28), and given matrix ids 25–30 | `gen_services.py`, `bootorder_check.py`, `callmatrix_audit.py` |
| Spawn/kill proposal with numbers | slots 6, 7, 8, 9 with shapes and the cost of each refusal | `PROPOSALS.md` § P3a |
| Face walkthrough | six services driven as one user session, including byte-identical export round trips | `t93_face_walkthrough.goose` (63 checks) |
| Load and cascade | three full boots of 28 services, two drills with a fatal service dead at step 0, a restart budget that runs out | `t92_sup_load.goose` (27 checks) |
| Final state regenerated | `SERVICES_FINAL.md` is now generated from the tree | `gen_services_final.py` |
| Counts reconciled | every live doc checked against the tree, every historical record bannered | `reconcile_counts.py`, `COUNTS.md` |
| Dead-code census | functions, constants and structs nothing reads | `deadcode.py`, `DEADCODE.md` |

## The gate, as it stands

`./os-build/layer1/run_native.sh` — 49 drivers run, 0 fail, 2,235 passing checks, 5 entry
points build-only (they export `svc_entry` and a host has no supervisor to call it).
`./os-build/layer1/check_services.sh` — 54 ok, 0 failed. `bootorder_check.py` — 28 services,
dependency order proven, no cycles. `callmatrix_audit.py` — 0 missing permissions, 91 dormant
rows named. `gen_limits.py` — 71 of 91 limits driven to their edge, 20 explained, 0 open.
`audit_status.py` — 114 status lines, 0 stale. `reconcile_counts.py` — no stale counts in the
live docs, every record bannered.

None of that is a boot. It is service logic against a real clock and real memory, with five
syscalls refused on purpose. The submission page says the same thing in its own words.

## The four defects this round found

1. **A released supervisor slot could never be reused.** `sup_release` cleared the entry and
   left the table length alone, so every stop/start cycle consumed a new slot and the 32-slot
   table filled after 32 restarts. Found by the supervisor drill, not by reading.
2. **`DEP_MAX` was 24 while the boot order is 28.** `deps_stop_plan` would have dropped four
   services from a stop plan and reported success. Raised to 32 with the array it writes into.
3. **The board client parsed its own export format one field off.** `R,<id>,<name>` was read
   with the id starting after the first comma, so every import failed. The round-trip test
   caught it on the first run, which is what a round-trip test is for.
4. **The six face services were outside the manifest, the boot order and the permission
   table.** Three audits caught all three independently (`COVERAGE`, `UNKNOWN`, drift),
   which turns "add a service" from a thing to remember into a thing that fails a check.

## What this round explicitly did not do

- **No kernel work.** `sys_spawn`/`sys_kill` are still proposals. Everything above the
  supervisor is proven as a state machine and as logic; nothing proves a process moved.
- **No persistence.** Settings, dock pins, wallpaper selection and the board log all lose
  their state on `init`. The board is the one with a proven round-trip, and nothing calls it
  on a timer. Each contract page says so in a "restart semantics" section rather than leaving
  it to be discovered.
- **No cleanup of the 144 unreferenced functions.** They are counted and listed in
  `DEADCODE.md`. Deleting them now would be a 144-function change on a branch that is
  waiting on a kernel ruling, and the census is worth more than the deletion.
- **No renumbering.** Matrix ids 1–24 are untouched; the face services took 25–30. A shift
  would rewrite every stored record that named a service.

## The honest summary for the boss

The services layer is done as far as it can be without a kernel that spawns processes. 31
services, 49 drivers, 2,235 checks, every audit green, every number generated from the tree.
The two things that would move it further are both on Pax's desk, not mine: rule P3a (four
reserved slots) so the supervisor can start something, and a K2 boot log so any of this can
be called running rather than passing.
