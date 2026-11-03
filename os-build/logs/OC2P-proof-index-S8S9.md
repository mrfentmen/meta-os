# OC2P proof index — S8+S9 appendix (2026-11-03, tip 78185175, no VM)

S6 index (`OC2P-proof-index-S6.md`, rows 20-28) stands. This
appendix tables S8 (`f55822d9`, 24 tasks) and S9 (`78185175`,
10 tasks) additions only. Method: `git show --stat` per commit;
shas live via `shasum -a 256` (S8 MANIFEST from its commit blob).

| # | Artifact | sha256 (short) | Status |
|---|---|---|---|
| 29 | `agent-layer/desktop-entries/INSTALL-OC1.md` | `a0a69fa4…8b06dbe9` | EXISTS (S8 doc, OC1 copy commands) |
| 30 | `os-build/logs/OC2P-H44-gap.md` | `b1d2f8ec…f7c0d44f` | EXISTS (S8 doc, gap closed 3/3) |
| 31 | `os-build/logs/OC2P-greeter-conflict.md` | `8174eb1f…0d4ca347` | EXISTS (S8 doc, OC1 ships theme) |
| 32 | `os-build/logs/OC2P-keep-matrix.md` | `aa02ae70…5224084c` | EXISTS (S8 doc) |
| 33 | `os-build/logs/OC2P-shotmap.md` | `0579f4c0…915b3b2a` | EXISTS (S8 doc, gap named for OC1) |
| 34 | `os-build/logs/OC2P-fallback-parts.md` | `70a6b9dd…83ad6e24` | EXISTS (S8 doc, VERIFIED vs CODE-INSPECTED) |
| 35 | `agent-layer/verify-dropin-desktop.sh` | `3f503e1d…1513a4aa` | EXISTS (S8 script, exits 0/1/3) |
| 36 | `agent-layer/check-keep-mime.sh` | `78b664d0…34fd54ac` | EXISTS (S8 script, exit 0) |
| 37 | `agent-layer/check-manifest-targets.sh` | `ec3d9ed2…198d8248` | EXISTS (S8 script, 0 ghosts/orphans) |
| 38 | `tests/agent-layer/test_verify_dropin_desktop.py` | `5b964ed8…3cc626fa` | EXISTS (S8 test, 3 tests) |
| 39 | `os-build/logs/OC2P-install-desktop-proposal.md` | `9cbd665f…8d3a79ff` | EXISTS (S8 proposal only, installer untouched) |
| 40 | `os-build/logs/OC2P-WATCH.md` | `2afa0adb…2ece7820` | EXISTS (S8 doc, 4 watches + S9 link fix) |
| 41 | `os-build/logs/OC2P-kf02-static.md` | `a0eabead…01145df4` | EXISTS (S8 doc, 10/10 mapped) |
| 42 | `os-build/logs/OC2P-BLOCKERS.md` | `6d32db20…b0ff6664` | EXISTS (S8 doc + S9 link fix) |
| 43 | `agent-layer/MANIFEST.md` (S8: 16 paths) | `12ed11ca…dc2941c7` | EXISTS (S8 regen, INSTALL-OC1 added) |
| 44 | `tests/agent-layer/test_check_keep_mime.py` | `93b4aebc…04e1c493` | EXISTS (S9 test, 4 tests) |
| 45 | `tests/agent-layer/test_check_manifest_targets.py` | `3dc52d61…bd44f9d4` | EXISTS (S9 test, 3 tests) |
| 46 | `agent-layer/verify-dropin.sh` (backend fix) | `4a4e0d7e…fc371011` | EXISTS (S9 fix, sha guard + 64-hex regex) |
| 47 | Link fixes: `desktop-entries/README.md` `8e91e295…039096d6`, `OC123_DEMO_4H.md` `a177235a…712ce606` (+WATCH/BLOCKERS above) | — (qualified paths) | EXISTS (S9, 5 bare links qualified) |
| 48 | `agent-layer/MANIFEST.md` (S9: 16 paths, README sha) | `25ed1465…c8dbc8ff` | EXISTS (S9 regen) |

## UNPROVEN-carry (unchanged: no VM per lane rule)

- KF-02 battery 010-012, k4 IPC 020-021 (fires on Pax F1 ruling only) — wait on OC1 furnace.
- Dashboard-forwarded 040, GUI-base spike 041 (one attempt max) — wait on OC1 furnace.
- Agent re-proof on Hana base (no *.iso/*.qcow2 on main) — waits on OC1 furnace.
- Evince/atril KEEP ack — proposal only, Hana's file untouched.

## S8+S9 sweeps (read-only)

- Fences: `kernel/src`, `server/queue`, `agents/registry.json` — 0 branch diffs. Secrets over branch diff: 0 hits.
- Size: no branch-added file >1MB. Byte-copy: Bond `meta-agent-status.desktop` diff clean. `sh -n` OK all scripts.
- Suites: `tests/agent-layer/` 30/30 OK (23 S8 + 7 S9); `check_iso_config.py` 101 passed; `metaos1-base/validate.py` OK; `make_wallpaper.py --check` current.
