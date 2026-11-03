# OC2P proof index — branch `opencode2/landwalls` (S5, 2026-11-03 UTC)

Method: every path below was `ls`'d on this branch tip `68e56c3e`.
Origin branch = branch of the introducing commit (`git log -- <path>` + `git branch --contains`).
`git log --oneline -n 25` + `git show --stat` used to attribute; full shas listed.

## Proven artifacts present on this branch

| # | Artifact path(s) | Origin branch | Introducing commit | Status | ls |
|---|---|---|---|---|---|
| 1 | `os-build/logs/OC2P-kf01-corrected/VERDICT.md` | `opencode2/proof` | `e39ab52e` | proven (BOOT) | EXISTS |
| 2 | `os-build/logs/OC2P-kf01-corrected/OC2P-kf01-corrected-build.txt` | `opencode2/proof` | `e39ab52e` | proven (BUILD PASS, kernel ELF 14720088 B, `.bootloader-config` 133 B) | EXISTS |
| 3 | `os-build/logs/OC2P-kf01-corrected/OC2P-kf01-image.txt` | `opencode2/proof` | `e39ab52e` | proven (IMAGE PASS, 17269760 B, MBR 0x55AA) | EXISTS |
| 4 | `os-build/logs/OC2P-kf01-corrected/OC2P-kf01-boot.txt` | `opencode2/proof` | `e39ab52e` | proven (alive line, STATUS tasks=8 ticks=5507) | EXISTS |
| 5 | `os-build/logs/OC2P-kf01-corrected/serial.log`, `serial2.log`, `qemu-err.txt` | `opencode2/proof` | `e39ab52e` | proven (full init, 0 panics) | EXISTS x3 |
| 6 | `os-build/captures/OC2P-kf01-fb0.png`, `fb1.png` (120485 B each) | `opencode2/proof` | `e39ab52e` | proven (handoff log frozen at kernel entry; KF-03 gap noted, not boot failure) | EXISTS x2 |
| 7 | `os-build/logs/OC2-proof-journal.txt`, `OC2-proof-crew-status.json` (Phase D) | `opencode2/500` | `3cb1046d` | proven (fresh boot, no hand-holding, 7/7 baselines, $0.155) | EXISTS x2 |
| 8 | `os-build/logs/OC2-appliance-proof-journal.txt` (59 lines) | `opencode2/proof` | `3987b936` | proven (autostart, no-key 20/20 loud, assessed run) | EXISTS |
| 9 | `os-build/logs/OC2-appliance-crew-status.json` (20/20, $0.434292) | `opencode2/proof` | `3987b936` | proven (20 checks / 20 baseline, reboot survival) | EXISTS |
| 10 | `os-build/logs/OC2-appliance-events.jsonl` | `opencode2/proof` | `3987b936` | proven (sample events) | EXISTS |
| 11 | `agent-layer/units/oc2-queue.service`, `oc2-patrol.service`, `oc2-patrol.timer`, `install.sh`, `env.example`, `tests/agent-layer/test_units.py` | `opencode2/500` | `cb110ff7` / `c75e21e6` (+ trio fixes) | proven (10/10 unit tests OK today) | EXISTS x6 |
| 12 | `os-build/logs/OC2B-gateway-setup.md` + `mcp-gateway/lab-backends.json` | `opencode2/500` | `fefd9e15` | proven (gateway RUNNING, smoke 9/9) | EXISTS x2 |
| 13 | `labs/cycles/cycle-006/` (record+prereg+raw+verify+figure, 14 files) | `opencode2/500` | `206adc79` (prereg) / `1cae8b1c` (results) | proven (MATCH, L3, RMSE 1.0994 in [1.049,1.149], live OpenAlex pin W2076498053) | EXISTS |
| 14 | `labs/cycles/cycle-007/` (record+prereg+raw+verify+figure, 14 files) | `opencode2/500` | `206adc79` (prereg) / `1cae8b1c` (results) | proven (MATCH, L3, gc 0.5166666667 vs 31/60 ±1e-9, live GBIF pin usageKey 5219404) | EXISTS |
| 15 | `os-build/demo/demo-3min.mp4` (180.000000s EXACT, sha `a29bc47d…3ae13f0` MATCH) + `CAPTURE_NOTES.md` + `oc1b-cut.txt` (film cross-check inputs) | OC1 lane (read-only witness) | `fefd9e15` (AGREE verdict block) | proven (AGREE — every checked CAPTURE_NOTES line holds) | EXISTS x3 |
| 16 | `os-build/logs/OC2B_PROOF_INDEX.md` (Sec 20 index of the 500 lane) | `opencode2/500` | `e8c1dde3` | proven (reference index, all paths exist) | EXISTS |
| 17 | `os-build/OPENCODE2_500_STATUS.md` (Phase D + appliance + KF-01 + follow-up blocks) | `opencode2/500` → `opencode2/proof` → this branch | `3cb1046d` / `e39ab52e` / `3987b936` | proven (record, not a boot artifact) | EXISTS |
| 18 | `os-build/OPENCODE2_LAND_WALLS.md` (lane task list S1–S5) | `opencode2/landwalls` (branch-unique) | `68e56c3e` | process doc (not a proof) | EXISTS |
| 19 | `os-build/metaos1-base/packages.txt` (KEEP list: xfce4, lightdm, mousepad, ristretto, **evince**) | Hana lane (read-only) | n/a (not OC2) | reference for (f) proposal wording | EXISTS |

## UNPROVEN-carry (ordered, not attempted — no VM per lane rule)

- KF-02 gate battery OC2P-010–012 on `717e7ffb` (triple-boot, bad-syscall-99, isolation) — NOT RUN.
- k4 IPC OC2P-020–021 — waiting on Pax F1 ruling, never invent numbers.
- Agent re-proof on Hana base (T2 never fired — no `*.iso`/`*.qcow2` on main/base seen this session).
- Dashboard host-forwarded check OC2P-040 — UNPROVEN-carry.
- GUI-base spike OC2P-041 (Xubuntu 24.04.5 base ISO 5.2G, evince→atril mismatch noted) — UNPROVEN-carry.
- Evince/atril KEEP ack — PROPOSAL text in S5 block only (Hana's file untouched).

## Not branch artifacts (excluded from table, noted for honesty)

- `mcp-gateway/lab-servers/` — UNTRACKED runtime installs (35M, intentionally NOT committed per gateway record). Present on disk, absent from git.
- `os-build/logs/OC2P-crosscheck-agent-status.md` — UNTRACKED, another agent's in-progress cross-check file (00:31 UTC). Not read, not touched, not claimed.

No MISSING paths: every tabled path above `ls`-verified EXISTS on this branch.

## No-VM sweeps (this session, read-only)

- Fence log `git log --oneline main..HEAD -- kernel/src server/queue agents/registry.json` → EMPTY (MUST-be-empty met; no branch-authored changes to fenced paths).
- Fence diff `git diff main --stat -- kernel/src server/queue agents/registry.json` → EMPTY. (`git diff main --stat` overall shows only 5 files: LAND_WALLS.md + 3 appliance logs + status block; everything else arrived via main merges — base drift, not branch authorship.)
- Secrets grep over branch diff (sk-/AKIA/ghp_/AIza/SPARK_API_KEY= patterns) → ZERO hits.
- >1MB check on branch-new files (`git diff main --name-only --diff-filter=A`, 4 files) → none over 1 MB (largest: appliance journal, byte-scale).

## Suite re-runs (read-only `python3 -m unittest discover`, this session)

- `tests/science-lab`: 374 tests, OK.
- `tests/agent-layer`: 10 tests, OK.
- `tests/officina`: 126 tests, OK.
- All green. Nothing to fix (and per lane rules, fixes would be parent's call anyway).
