# crates/ — Rust ports of the Meta OS host programs (Lane D, 2026-11-04, R5)

20 crates, 304 `.rs` files, 102,323 lines
(`find crates -name '*.rs' | wc -l`; `find crates -name '*.rs' -exec cat {} + | wc -l`).
Workspace root: `Cargo.toml` (members = all 20 crates below).

Blanket finding, verified 2026-11-04: **none of these crates ships in the
product image.** `grep -rni "crates/|cargo|rustc|bootimage" os-build/iso/merge-layers.sh
os-build/face/provision.sh` returns empty (rc=1); the image installs `nodejs` +
`python3-gi` (`os-build/iso/merge-layers.sh:70`) and runs Node `.mjs` + Python3.
Every crate below is a behavior port whose Python/Node original stays the live
fallback. Layer column uses `os-build/LAYERS.md` numbers: all crates are
**Layer 7 (Programs)** ports — never the kernel (layers 1–3, `kernel/`) nor
Goose services (layer 4, `services/`) nor Lobster scripts (layers 5–6, `lobster/`).

Per-crate release build logs: `crates/build-logs/<name>.log` (`EXIT=0` = COMPILED).
Per-crate Rust test counts: `crates/TEST_RESULTS.md` (Lane D, this round).

| Crate | Batch / owner | What it is (ports, behavior not redesign) | Layer | In shipped image? |
|---|---|---|---|---|
| `agent-ops` | — / — (operator subsystems) | Pure-logic operator-side agent subsystems: TF-IDF vector memory, workspace snapshots/rollback, PoW execution throttle, allowlist egress guard, local/cloud tier router, token-budget simulator. No identified single-file original; no execution backends. | 7 | NO |
| `agent-runtime` | B04 / Rowan | Trio agent runtime. Source: `server/queue/trio_agent.py` (poll open jobs, idempotency-first, atomic claim + lease, frame SHA-256 check, one bounded self-correction retry, single result-envelope write, fire-and-forget relay NOTIFY). | 7 | NO |
| `assess-server` | B05 / Rowan | HTTP service (`std` TcpListener, thread/connection). Sources: `server/README.md`, `server/assess.mjs`, `server/model.mjs`, `server/queue.mjs`, `server/server.mjs`. Serves POST /api/assess, GET /api/health + static frontend. Explicitly partial: does NOT serve crew/cameras/fires/radar routes the Node original serves — not a drop-in. | 7 | NO |
| `dashboard` | B15 / Hana | Dashboard backend contract. Sources: `os/docs/DASHBOARD_SMOKE_CHECKLIST.md`, `os/docs/DASHBOARD_SPEC.md`, `os/tests/test_crewboard_*.py`, `os/tests/test_dashboard_*.py`. | 7 | NO |
| `guardrail` | B03 / Rowan | Guardrail + Spark transport (DIRECT `SPARK_API_KEY` path). Sources: `server/queue/spark_gen.py`, `server/queue/spark_guardrail.py`. | 7 | NO |
| `intel` | B09–B14 / Hana | Relay Intelligence: `os/intel/` package. B09 core/registry (`os/intel.py`, capability, explanations); B10 briefings/dispatch (`alerts/baton/brief/dispatch/...`); B11 Spark client + mind images; B12a evals/drills (39 check files + 21 drill modules); B13 devpack panel shaping; B14 trust gate + timer sweep + launch-run. | 7 | NO |
| `os-boot` | B23 / Milo | Boot glue & deployment. Sources: `os/mos.py`, `os/mos/cli.py`, `os/os/README*.md`, `os/os/bin/metaos-*`, `os/os/build-*.sh`. | 7 | NO |
| `os-budget` | B20 / Milo | Budget & resource policy. Sources: `os/intel/brief_cost_check.py`, `os/intel/budgets.py`, `os/intel/cost_check.py`, `os/intel/drills/budget_*.py`, `os/intel/drills/cgroup_limits.py`, `os/mos/disk_audit.py` + intel cost/budget tests. | 7 | NO |
| `os-identity` | B18 / Milo | Identity & capability registry. Source: `os/mos/capabilities.py` (register/heartbeat, overseer assigns only to fresh agents with capacity). | 7 | NO |
| `os-jobs` | B16 / Milo | Jobs service. Sources: `os/jobs.py` + claims/jobs unit tests. Header status: PORTED. `JobStore` + `Clock` seams, no dependencies. | 7 | NO |
| `os-memory` | B17 / Milo | Memory service. Sources: `os/mos/memory.py` (journaled versioned store, per-agent + shared namespaces) + memory-depth tests; `memory_depth_lines` slice lives in B10 (`os/intel/brief.py`). | 7 | NO |
| `os-misc` | B24–B30 / Buffy | Catch-all: B24 bus core (`os/poll.py`, `presence.py`, `send.py`, `store.py`, `watch*.py`); B25 bus extras (`announce/clipboard/edits/forward/paste/saved.py`); B26 bridges/digest/admin (`admin/digest/export/health/timecapsule/webhook.py`); B27 world-pack validation (`os/worlds/validate_pack.py`; packs carried as data); B28 docs/roles carried, not ported; B29 crew/demo assets carried; B30 lane plans carried. | 7 | NO |
| `os-supervisor` | B21 / Milo | Supervisor & watchdog. Sources: `os/intel/drills/watchman_*.py`, `kill_worker.py`, `os/intel/watchdog*.py`, `thresholds.py`, `e2e_watchdog_surfaces.py`. | 7 | NO |
| `os-worker` | B22 / Milo | Worker runtime & drivers. Sources: `os/mos/worker.py`, `os/os/drivers/{muse,run,stub}_driver.py` + CONTRACT/CONFORMANCE, `os/os/uplink/relay_uplink.py`, driver drill/TDD tests. | 7 | NO |
| `os-workspace` | B19 / Milo | Workspace & artifact store. Sources: `os/mos/artifact_store.py` (OS-083 deposit/list/read/history/attach) + `os/mos/gitops.py` (review/approve/merge/reject/worktrees); CLI is library fn `run_cli`, no `[[bin]]`. | 7 | NO |
| `parity-tests` | B31 / Buffy | Parity test harness (`support::fake_redis`, `helpers`, `acceptance`) + case ports (`test_os_*.rs`, `test_bustools_parity`, `test_fdny_par_clock`, `test_pomodoro`, `test_worlds_pack`, …). Harness, no live counterpart by design. | 7 | NO |
| `queue-core` | B01 / Rowan | Trio queue core (pure logic). Sources: `server/queue/queue_service.py` (`validate_envelope`) + store-agnostic core. Transport backends NOT in this crate. | 7 | NO |
| `queue-store` | B02 / Rowan | Queue store (Upstash store + repo layer). Sources: `server/queue/trio_repo.py`, `server/queue/trio_store.py`. | 7 | NO |
| `relay` | B08 / Hana | Meta Nuntius relay. Source: `relay/relay.mjs` + README (stdlib-only Node). Routes, validation refusals, watermark polling, room caps, file store — header status PORTED. Only crate (with `assess-server`) shipping a runnable binary (`src/main.rs`: `RELAY_PORT` default 8787, `RELAY_STORE_FILE` unset = memory-only). | 7 | NO |
| `stack` | B06 / Rowan | Demo-stack wiring planner. Source: `run-stack.sh` (start order, ports, env contract, health-check shape, transport decision, summary lines). Computes the plan; does NOT spawn processes. | 7 | NO |

Binaries in `crates/`: exactly two — `relay` (`crates/relay/src/main.rs`,
implicit binary target) and `assess-server` (`[[bin]]` in
`crates/assess-server/Cargo.toml`). Everything else is `rlib` logic + tests.
