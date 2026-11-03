# ISO lane handoff — Bond, 2026-11-03

Written while the boss was away. Everything below was run on this Mac; the
numbers are command output, not estimates. No VM was started and none exists
here.

## Commits

| Branch | Commit | What it does |
|---|---|---|
| `bond/12h` | `105de05f` | fifth frozen app (agent-status), checker walks the frozen app set, `apply.sh` |
| `bond/rk007` | `d4adc367` | untrack 1,092 build-output files, ignore them from here |
| `bond/rk007` | builder fix | `create_disk_image` used correctly; image now builds |
| `bond/round13-records` | `de25c6eb` | 37 Round 13 IDs named; three false counts fixed |

All four are pushed. None is in `main`; only Pax merges.

## What works, with proof

- `python3 iso/tools/check_iso_config.py` → **54 passed, 0 failed**. It was 33
  before this pass; the new rules walk the frozen app table and fail when an id
  has no launcher.
- `python3 tests/test_iso_agent_status.py` → **9 passed**.
- `python3 tests/test_iso_apply.py` → **6 passed**.
- `iso/tools/apply.sh --root <dir>` installs the whole lane; `--dry-run`
  writes nothing; a second run is byte-identical.
- RK-007 image: **6,784,000 bytes**, boot signature `55aa` at offset 510.

## What is still blocked, and only by this

| Item | Blocker |
|---|---|
| RK-007 boot proof | no QEMU on this machine |
| Plymouth seen on screen | needs the base VM |
| Clean Calamares install → login | needs the VM |
| Apps opened from the dock | needs the VM session |
| `supervise` on a cadence | nothing calls it; needs a scheduling decision |

## If you pick this up next

1. Merge `bond/12h`, then `bond/rk007`, then `bond/round13-records`.
2. Ask OC2 where the agent layer installs and set `METAOS_ROOT` to match. The
   status app defaults to `/opt/metaos`; that default is the one guess in the
   app, and it is documented in `iso/apps/README.md`.
3. Run one boot on any machine that has QEMU: the commands are above.
