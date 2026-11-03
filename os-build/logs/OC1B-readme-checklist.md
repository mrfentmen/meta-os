# OC1B-426 — README quantitative-claim checklist (tree: 3452d244, baseline clone /tmp/oc500-baseline)

Every number in README.md @ 3452d244, one row per claim. Status filled by
OC1B-427..441: VERIFIED / STALE (new number) / UNVERIFIABLE-ON-MAC (reason).

## Badges (README line 11)
- [x] R-B1: STALE -> FIXED (2071 run, 2015 passing; proof OC1B-readme-node.txt + rerun) node badge "2071 run, 2016 passing" — re-derive OC1B-427 (`npm test`)
- [x] R-B2: STALE -> FIXED (workspace does not build; proof OC1B-readme-rust.txt) rust badge "2186 passing" — re-derive OC1B-428 (`cargo test --workspace`)
- [x] R-B3: VERIFIED (12/12; proof OC1B-readme-worlds.txt) worlds badge "12 of 12 valid" — re-derive OC1B-436 (`python3 os/worlds/validate_pack.py`)

## Test-numbers table (README lines 114–122)
- [x] R-T1: STALE -> FIXED (2015 pass / 56 fail; newcomer R11-282 os-docs index gap) Node: "2071 run, 2016 pass, 55 fail" via `npm test` — OC1B-427
- [x] R-T2: STALE -> FIXED (0 run, E0063; excl-intel 1851/0; proofs OC1B-readme-rust*.txt) Rust workspace: "2186 pass, 0 fail" via `cargo test --workspace` — OC1B-428
- [x] R-T3: STALE -> FIXED (296 pass, 0 skip; proof OC1B-readme-queue.txt) Python job queue: "296 pass, 1 skip" via `python3 -m unittest discover -s tests/queue-python` — OC1B-429
- [x] R-T4: VERIFIED (49; proof OC1B-readme-officina.txt) Python Officina: "49 pass" via `python3 -m unittest discover -s tests/officina` — OC1B-432
- [x] R-T5: VERIFIED (163/163; proof OC1B-readme-science.txt) Python Science Lab: "163 of 163 pass" via `python3 -m unittest discover -s tests/science-lab` — OC1B-430
- [x] R-T6: VERIFIED (14; proof OC1B-readme-hortus.txt) Python Hortus: "14 pass" via `python3 -m unittest discover -s os/tests -p "test_hortus*.py"` — OC1B-431
- [x] R-T7: STALE -> FIXED (does not compile; proof OC1B-readme-intel.txt) Rust intel crate: "186 of 186 lib tests pass; b10_parity 53 of 53" via `cargo test -p intel` — (table row; derived with workspace run)
- [x] R-T8: VERIFIED (12/12) Worlds packs: "12 of 12 valid" via `python3 os/worlds/validate_pack.py` — OC1B-436
- [x] R-T9: VERIFIED (11/12, green cycle fails; proof OC1B-readme-loop.txt) OS loop harness: "11 of 12 pass" via `bash os/os/loop-tests/metaos-loop.test.sh` — OC1B-433
- [x] R-T10: VERIFIED (runs are 2026-11-02 on current main) table header: "measured on the current main on 2026-11-02" (date claim, not a count)

## Built-with row (README line 181)
- [x] R-W1: STALE -> FIXED (see R-T2) "Rust ... 2186 tests green" — same derivation as R-T2

## Kernel section (README lines 239, 248–253, 301–315)
- [x] R-K1: STALE -> FIXED (13 files VERIFIED, 5984 lines -> "about 6,000"; proof OC1B-readme-repo-lines.txt) "about 5,800 lines across 13 files" (`kernel/`, .rs) — OC1B-434 (`wc -l kernel/src/*.rs`)
- [x] R-K2: VERIFIED (19 crates) "19 crates" (Rust OS layer) — count `crates/*` + kernel
- [x] R-K3: UNVERIFIABLE-AS-STATED (method unstated; 119k-139k reconstructions) "roughly 122,000 lines, tests excluded" (whole OS side) — OC1B-435 (README's stated method reproduced)
- [x] R-K4: VERIFIED (GREEN 8/8 twice; §1 gate logs) gate "GREEN 7/7" + serial at `os-build/logs/WAVE3-combined-serial.txt` — §1 baseline re-proof (OC1B-003 gate log)
- [x] R-K5: VERIFIED (record exists: OPENCODE_ROUND5_REPORT.md R5-5 73 min) "standing soak record is 73 minutes with 0 panics (R5-5)" — record lookup, no re-run in §18
- [x] R-K6: VERIFIED (no final/main 2-hour verdict file exists; still PENDING) "2-hour soak verdict is still PENDING" — status lookup
- [x] R-K7: VERIFIED (576 lines) "framebuffer.rs, 576 lines" — `wc -l kernel/src/framebuffer.rs`
- [x] R-K8: VERIFIED (kernel/Cargo.lock 0.9.35) "bootloader 0.9.35" pin — `kernel/Cargo.toml` pin line
- [x] R-K9: VERIFIED (three programs in gate serial) "three userspace programs" run at boot (claim sentence) — gate serial
- [x] R-K10: VERIFIED (K1-boot.txt + runs 1-3 present) "four committed QEMU boot logs (K1-boot.txt and runs 1–3)" — file existence

## Goose services (README lines 339–351, 590–597)
- [x] R-G1: SPLIT: libs 18 VERIFIED; services count STALE-NAMED (24 manifest rows vs 37 source dirs vs 25 claimed; no fix, needs §16/Pax) "25 services over 18 shared libraries" — OC1B-436-adjacent (inventory count)
- [x] R-G2: STALE-NAMED-NOT-FIXED (cited record now 59 drivers/2715 assertions; quoted receipt needs §16 re-run) "33 programs, 1,253 checks, 0 failed" (`os-build/layer1/SERVICE_RUNS.md`) — record lookup, not re-run in §18 (Goose runs are §16)
- [x] R-G3: STALE-NAMED-NOT-FIXED (same receipt quote as R-G2) run_native.sh receipt "33 programs RUNS=33 FAILS=0" — record lookup

## Agent layer (README lines 355–357)
- [x] R-A1: VERIFIED (28 agents in registry) "registry of 28 agents" — `agents/registry.json` count — OC1B-437-adjacent

## Imperium numbers (README lines 56, 58)
- [x] R-I1: UNVERIFIABLE (no eval log in repo; in-repo audit README_AUDIT_BOND.md agrees) eval batch: "100 frames ... 42 matched ... 46 held ... 0 real misses ... 11 scored misses ... before event ... 100 of 100 ... 6.4 seconds" — eval-record lookup (`os-build/demo/EVAL4.md` + cited records), not re-run in §18
- [x] R-I2: VERIFIED (EVAL4: 80/20/0, 5/5, 0/8) "EVAL4.md (80% match, 20% held, 0% miss; emergencies 5 of 5; false flags 0 of 8)" — file lookup
- [x] R-I3: STALE -> FIXED (see R-T3) "296-test Python queue suite" — same as R-T3
- [x] R-I4: VERIFIED (TEST_BUDGET_USD = 75.00) "$75" spend guardrail — code constant lookup (`server/queue/`)

## Model layer table (README lines 520–526)
- [x] R-M1: VERIFIED at code-surface level (4 surfaces present; endpoint history re-proven live in §9) four models + voice UNRESOLVED row — status-word check, OC1B-438

## Per-program status words (README lines 288–549) — OC1B-437/438
- [x] R-P1: VERIFIED with note (7 products.js ids all in README; other README names are not products.js products) product list vs `js/products.js` two-way check — OC1B-437
- [x] R-P2: VERIFIED (spot-checked vs suites run here + status files) status words vs status files (Imperium, Science Lab, Officina, Musica, Aegis, Nervus, Hands-Free) — OC1B-438
- [x] R-P3: UNVERIFIABLE-AS-STATED (no 4-test suite in tree; actual node musica suite 39/39 pass) Musica "test suite passes 4 of 4 on the Mac" — suite lookup (§15 re-proves)
- [x] R-P4: VERIFIED (49 + gate 14/14 re-ran GREEN here) Officina "49-test suite ... 14 of 14" gate — R-T4 + gate file lookup
- [x] R-P5: VERIFIED (see R-T5/R-T6) Science Lab "163-test suite ... 14 Hortus tests" — R-T5/R-T6
- [x] R-P6: VERIFIED (PACK.md: thirteen agents) "13-agent research team" — status-file lookup
- [x] R-P7: VERIFIED (STATUS: ladder 0-6, cap L3, step 8 unimplemented) "evidence ladder (levels 0–6)" / "capped at level 3" / "step 8 ... UNIMPLEMENTED" — status-file lookup
- [x] R-P8: VERIFIED (17 categories in products.js) "17 scene categories" (Ignis) — code/enum lookup
- [x] R-P9: VERIFIED (relay default 8787) relay "port 8787" — code lookup

## Links (README lines 9, 551–578) — OC1B-439
- [x] R-L1: VERIFIED (all live links 200; localhost + api.meta.ai excepted with reason; proof OC1B-readme-links.txt) every live link resolves (repo link, site link, 16-link v5 set) — HTTP status per link

## Freshness / methods — OC1B-440
- [x] R-F1: VERIFIED (all 9 table commands run as printed; rust/intel fail-as-printed with E0063 recorded) every test-table command runs as printed (verbatim copy) — per-command results

## Site + face cross-checks — OC1B-447/448
- [x] R-S1: listed for Pax (site/index.html:158 carries old 33/1253 Goose numbers) `site/index.html` numbers vs derived set
- [x] R-S2: no contradicting suite numbers in face seed/status (checked) face seed/status numbers vs derived set

## Verdict — OC1B-441 (filled last)
- [ ] mark every row VERIFIED / STALE / UNVERIFIABLE-ON-MAC
