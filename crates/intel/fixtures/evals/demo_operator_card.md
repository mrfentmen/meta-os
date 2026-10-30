# Watchdog operator failover card (Milo, DEM-016)

The card Milo holds on demo day. If the Shot 8 alert does not
fire on the dashboard when the staged worker goes silent, work
this card top to bottom. Every command below was run and
verified in the repo before this card was written; expected
outputs are the outputs those runs produced.

## The operator's job

- Milo is the watchdog operator: cue the staged silence
  (DEM-011), watch for the Shot 8 STALL alert, and hold this
  card. Dale presents; Pax holds the overall failover card
  and is the only one who touches a terminal if Layer 1
  wobbles. Milo runs only the commands on this card.
- Never post to the bus from this card. The watchdog CLI's
  announcement lines print to stdout only; they are held,
  not posted, per Dale's posting rule.

## Step 1 — prove the detector still works (fixture, no network)

Run the staged-silent-failure drill:

```
python3 intel/drills/demo_silent_failure.py
```

Expected: exit 0, ending `demo_silent_failure drill: PASS`.
Phase 4 must name the presence-stall alert for milo/7 with
last progress 601s ago under production thresholds. If this
fails, the detector itself is broken: stop here, tell Pax,
and fall back to the recorded demo (DEM-003 fallback cut) —
do not improvise a live alert.

## Step 2 — prove the catch lands in demo time

Run the catch measurement under the demo profile:

```
python3 intel/drills/demo_catch_time.py
```

Expected: exit 0, ending
`demo_catch_time measurement: PASS — 3/3 rehearsals under 90s`.
The demo profile is `intel/metaos-demo.env` (stall windows
1 minute, not the production 10); production
`intel/thresholds.py` is untouched by it. If Step 1 passes
and this fails, the detector works but demo timing does not:
same fallback as Step 1.

## Step 3 — single-tick sanity check

```
python3 intel/watchdog.py --once
```

Expected on an empty snapshot: `watchdog: 0 alert(s)` and
exit 0. Add `--announce` to print the WDG-015 announcement
line for any critical alert (stdout only, never a bus post).
A snapshot file can be supplied with `--snapshot <file>`;
a bad snapshot file exits 1 with `watchdog: cannot load
snapshot` on stderr.

## What this card cannot do (honest limit)

The watchdog CLI ticks a snapshot file (or an empty
snapshot). It does not yet read the live room: live reading
waits on FND-014. So if Steps 1–3 pass but the live
dashboard still shows no alert, no command on this card
forces a live alert into existence. In that case the
operator's move is the recorded fallback, not a manual
alert: tell Pax, who owns the failover decision.

## Demo-day standby (not yet performed)

Standing by during the live demo — watching the alert fire
and running this card if automation hiccups — happens on
demo day itself. This card is the preparation for it; the
live standby is not claimed here.
