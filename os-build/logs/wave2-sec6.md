# Wave2 Section 6 (tasks 51-60) — recon ONLY (2026-11-02 UTC)

Source: OPENCODE1_TASKS_WAVE2.md Sec 6 (lines 157-180). Rule: do NOT edit agents/registry.json (read-only here).

## services/ dir
- 42 subdirs under services/ (incl. common, build, tests, callmatrix + 24 MANIFEST services + extras: board, dashboard, devices, dock, echo, hello, heartbeat, mcp-host, net, notify, settings, socket, updater_client, wallpaper).
- MANIFEST.md: 21 WRITTEN + 3 NOT BUILT (registry, devmgr, sockets = README-only contracts). BUILD.md: status DESIGNED, `goose toolchain: NOT FOUND`, nothing COMPILED, nothing run.
- Goose tests present (t45-t99) + run-goose-tests.sh (hardcodes GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose); smoke not executed here.

## Health endpoints
- Goose services: NO HTTP /health. Health = in-Goosе: sup_beat/sup_ms_since_beat + wd_check_one (WD_FINE/SILENT/DEAD/STILL_DEAD), wd_count numbers for health line. Only 3 READMEs mention health: supervisor, watchdog, devices.
- HTTP health lives outside services/: relay GET /health {ok,rooms,store}; queue :8935/health; app :8080/api/health (all per run-stack.sh).
- Live now: NONE. curl 8787/health, 8935/health, 8080/api/health all refused.

## agents/registry.json (EXISTS, not edited)
- Exists, 25 agents, ALL 25 command==["true"] = placeholder. Zero judge-ready real commands.
- Per loop: rowan, hana, milo, buffy, bond, pax, imperium-patrol, musica-studio, officina-faber, watch (+gym 3/3), aegis, nervus, research-director/literature/scientific-analyst/mathematics/chemistry/biology/physics/hypothesis/computational/statistician/critic/verifier/archivist — every one placeholder.
- Task 51 verdict: NOTHING hosted with real command; Buffy R11 landing not visible in registry. List-all-placeholder, no workaround.

## In-repo relay :8787 (relay/ dir)
- relay/ = relay.mjs (279 lines, stdlib only), relay.test.mjs, viewer.html, README.md.
- Default port 8787 (RELAY_PORT), store memory unless RELAY_STORE_FILE set. Endpoints: POST /rooms/<room>/messages, POST /rooms/<room>/notify, GET /rooms/<room>/messages?since=n, GET /health, GET / viewer.
- Tests: node --test relay/relay.test.mjs = 7/7 pass (offline, ephemeral port). Not currently listening.
- run-stack.sh: relay 8787 + queue 8935 + trio_agent (TRIO_RELAY_URL) + app 8080 — full stack starter, none running now.

## Supervisor units
- services/supervisor/: bootorder.goose, deps.goose, supervisor.goose + README. Table MAX_SERVICES=32, 6-state machine, default RP_ON_FAIL backoff 100ms-30s. Records belief only — no spawn (needs K6 fork/exec, absent).
- services/supervisor.sh: shell wrapper `supervisor.sh <name> <dir> [--once]`, hardcoded GOOSE binary, logs records.log/service.out, STOP-file ordered-stop. No systemd/launchd units found.
- Task 57 drill (kill + restart matches record): no log found — UNPROVEN.

## Tasks 52-60 quick mapping
- 52 watchman-on-Nuntius: agents/watchman.mjs v1 DONE (polls jobs dir, claimed set, receipt) tests 3/3 per TASKS C1; Room-1/Nuntius polling = next step, no drill log.
- 53 timer sweep: TASKS C2 TODO (agents/runtime.mjs has watch poll/compare, unproven as fallback drill).
- 54 baton: baton.mjs + continuation brief DONE host-only (test agents-baton), zero-duplication cross-program = stretch, no real run log.
- 55 budget-kill / 56 STOP-file: runtime supports both; proof drills are G2/G1 TODO. No receipts.
- 58 Goose smoke (start/health/stop table): BLOCKED — no toolchain, nothing runnable; honest answer = table of NOT-RUN with reason.
- 59 ledger audit: only agents/gym-ledger.jsonl (4 lines, watch gym-drill-1 3/3). No day of per-run brief/outcome/receipt ledgers.
- 60 status verdicts: os-build/OPENCODE1_WAVE2_STATUS.md exists (940B) but covers only Sec1-2 OPEN + Sec3-9 dispatched note; Sec6 verdicts NOT yet written.
