# OS-122 eval: who watches the watchman (Milo)

Module: `intel/watchman_watch.py`. Drill:
`intel/drills/watchman_watch.py` (6/6 phases PASS).
Tests: `tests/test_intel_watchman_watch.py` (14 tests).
Threshold: `WATCHMAN_STALE_MINUTES` added to
`intel/thresholds.py` (default 5, env
`WATCHDOG_WATCHMAN_STALE_MINUTES`); the INT-022 locked
values are untouched, because watching the watchman did
not exist at lock time.

What was proven on fixtures:

- A killed watchman is flagged crew-dark within one
  detector cycle: one tick over a dead watchman yields
  a crew-dark record naming the machine, and the
  board's state record for that machine reads
  watchman-dead while the darkness lasts.
- A revivable watchman earns no Dale contact: the
  restart record is journaled, the next tick after
  the simulated restart journals a recovered record,
  and no escalation record and no push payload
  appears anywhere in either tick.
- A watchman killed beyond the restart's power earns
  exactly one blocked push: the tick yields crew-dark,
  a failed restart record, and one escalation whose
  payload validates through `intel/push.py` and whose
  question names the machine. Two further unchanged
  ticks yield zero new records, and the drill's sent
  ledger stays empty: the payload is built, never
  sent, and sending belongs to the Web Push worker
  (Hana OS-097).
- Dedupe is per dark episode, not global: a machine
  that recovers and then dies again earns a fresh
  crew-dark record and a fresh escalation. A global
  key would have silenced the second death.
- A stale bell reads dead even when the alive flag
  says True (bell 301 seconds old at a 5 minute
  window); a fresh bell reads alive. A machine with
  no flag and no bell reads unknown and yields no
  records: missing evidence is never claimed as a
  dead watchman.
- The tick never mutates its snapshot or journal,
  and journal records carry no announcement field.

What is NOT proven here:

- A live watchman actually killed and restarted: the
  restart in the drill is applied by a simulated
  owner, not by systemd on a live machine (the
  OS-034 contract half), and no booted test image
  runs in this repo.
- The resident watchman program actually ringing:
  that mechanical half is Pax OS-118, not this module.
- A phone actually ringing: the escalation here is a
  built payload, and the Web Push worker wiring is
  Hana OS-097.
- The board rendering itself: the board lines and
  state records this module publishes are proven;
  Rowan's dashboard rendering of them is Rowan's
  surface to confirm (the same shape as the WDG-024
  dashboard confirm, still owed).

Related: the ladder this rule extends is OS-095, the
gate it ends at is OS-096, the baton the reassign
rung would have used is OS-125, and the reboot state
it complements is OS-129.
