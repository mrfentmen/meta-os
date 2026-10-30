# OS-036 watchdog boot self-check — eval

Drill: `intel/drills/boot_selfcheck.py` (exit 0, 7 PASS lines).
Transcript: `intel/evals/boot_selfcheck.log`.
Module: `intel/boot_selfcheck.py` (fixture + `run_self_check`).
Store record: `intel.store.put_selfcheck` / `get_selfcheck`,
key `muse-bus:intel:wd:selfcheck:<room>:<ts>`.
Pinning tests: `tests/test_os_boot_selfcheck.py` (6 tests).

## Result: green record on the seeded fixture, red on breakage

The self-check ticks the seeded fixture once through
`intel.watchdog.tick` — one pass over the DETECTORS list, so
every detector runs exactly once — and compares per-kind
counts against EXPECTED. All 10 expected alerts fire, one per
kind:

| Kind | Count | Fixture trigger |
| --- | --- | --- |
| presence-stall | 1 | nick in caps, absent, last progress 20 min ago, lease expired (the one stale lease) |
| progress-stall | 1 | nick present, last progress 20 min ago |
| lease-risk | 1 | lease expires in 3 min, heartbeat quiet 3 min, progress fresh |
| dead-dep | 1 | open job 21 deps on blocked job 20, note verbatim |
| missing-dep | 1 | open job 22 deps on id 999, which exists nowhere |
| file-collision | 1 | claimed jobs 4/5 share `intel/store.py` |
| attempt-warning | 1 | open job 23, attempts 2 of max 3 |
| attempt-exhaustion | 1 | open job 24, attempts 3 of max 3 |
| silent-room | 1 | claimed jobs live, latest timestamped message 70 min old |
| rejected-dispatch | 1 | `REJECTED:42 BAD` line in messages |

Failure modes verified, not just asserted: removing
`detect_dead_dep` from DETECTORS turns the record red naming
only `dead-dep`; replacing `detect_lease_risk` with a raising
function turns it red naming only `lease-risk` (tick swallows
the crash, the self-check catches the missing count). A
second tick on the same fixture is green again, so the record
exists after every boot test, not just the first. The record
round-trips through the store seat unchanged.

Ages derive from `intel/thresholds.py`, never hardcoded, so a
threshold retune retunes the fixture. The fixture is built to
the OS-026 spec (jobs in 4 states — open, claimed, blocked,
done; presence for 4 nicks; one stale lease), not loaded from
it: see the honest gaps below.

## NOT proven here (honest gaps, owed on the test image)

- The fixture is hand-built to the OS-026 spec because
  OS-026 (Buffy's boot fixture pack, `os/fixtures/`) has not
  landed. When it lands, `seeded_fixture` should be replaced
  by a loader over that pack and the expected counts
  re-pinned; until then a drift between this fixture and the
  real seed pack would not be caught here.
- A green record on a booted image: there is no test image in
  this repo, so the self-check running at relay-ready
  (inside `relay-watchdog.service`, OS-033) is not exercised,
  only the record, verdict, and fail modes.
- The boot checklist rendering the self-check record (Rowan's
  OS-043 surface) — the record exists and round-trips, but no
  dashboard read of it is proven here.
- Live ingest does not yet stamp `server_time` (FND-014), so
  a live tick runs on the wall-clock fallback; the fixture
  tick uses an explicit fake clock and proves nothing about
  live clock behaviour.
