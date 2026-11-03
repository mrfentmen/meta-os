# OC2P proof index — S6 appendix (2026-11-03, tip a012558f, no VM)

S5 index (`OC2P-proof-index.md`, 19 artifacts, tip 68e56c3e) stands. This
appendix tables S6 additions only. Method: `ls` on branch tip a012558f;
origin = introducing commit via `git log -- <path>`. Fences/secrets/size/
suites re-verified this session (read-only, zero QEMU).

## S6 additions (all EXISTS, branch-unique to opencode2/landwalls @ a012558f)

| # | Artifact | sha256 (short) | Status |
|---|---|---|---|
| 20 | `agent-layer/desktop-entries/README.md` | `0d69d215…16b53b84` | T1 provenance (Hana/Bond files untouched) |
| 21 | `agent-layer/desktop-entries/atril.desktop` | `0990716e…711f92` | T1 active launcher |
| 22 | `agent-layer/desktop-entries/evince.desktop` | `a7ae673c…39fcb69` | T1 degraded-off (NoDisplay=true, pending Hana KEEP ack) |
| 23 | `agent-layer/desktop-entries/meta-agent-status.desktop` | `68a373a0…17a3d1c` | T1 byte-copy of Bond `iso/apps/desktop/` (diff clean) |
| 24 | `agent-layer/desktop-entries/mimeapps.list` | `2d35dc75…581f5369a6` | T1 drop-in proposal (PDF→atril; canonical is Hana's) |
| 25 | `agent-layer/desktop-entries/mousepad.desktop` | `11e146a7…3652b025fd0` | T1 active launcher |
| 26 | `agent-layer/desktop-entries/ristretto.desktop` | `95b85d2a…bac49895` | T1 active launcher |
| 27 | `agent-layer/desktop-entries/thunar.desktop` | `2ae2d8c3…85e262c` | T1 launcher (Exec mirrors Bond meta-files) |
| 28 | `os-build/OC123_DEMO_4H.md` (OC1-sole-boot fix) | — (doc) | Iron rules + OC1 sole furnace, OC2/OC3 ZERO QEMU |

MANIFEST: `agent-layer/MANIFEST.md` 15 paths, regenerated from
`manifest.py`, `test_manifest_fresh` green.

## UNPROVEN-carry (not attempted, no VM per lane rule)

- KF-02 battery 010-012 (triple-boot, bad-syscall, isolation) — waits on OC1 furnace.
- k4 IPC 020-021 — waits on Pax F1 ruling.
- Dashboard-forwarded 040, GUI-base spike 041 — wait on OC1 furnace.
- Agent re-proof on Hana base (no *.iso/*.qcow2 on main) — waits on OC1 furnace.
- Evince/atril KEEP ack — proposal only, Hana's file untouched.

## S6 sweeps (read-only)

- Fences: `kernel/src`, `server/queue`, `agents/registry.json` — no branch diffs.
- Secrets over `git diff main`: 0 hits.
- Size: no branch-added file >1MB (`agent-layer/` zero >1M).
- Suites: `tests/agent-layer/` 20/20 OK; `check_iso_config.py` 101 passed;
  `make_wallpaper.py --check` current; `metaos1-base/validate.py` OK 0 failures.
- Byte-copy: `diff Bond meta-agent-status.desktop` clean.
