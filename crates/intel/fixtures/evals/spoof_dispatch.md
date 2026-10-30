# Spoofed-dispatch drill: INT-010 (Pax, 2026-10-27)

Script: `intel/spoof_dispatch_drill.py`. Transcript:
`intel/evals/spoof_dispatch.log`. Tests:
`tests/test_intel_spoof_dispatch.py`, plus the
rejected-dispatch cases in `tests/test_intel_watchdog.py`
(registry count, coverage, severity mapping).

Run it (from the repo root):

```
python3 intel/spoof_dispatch_drill.py
```

The drill, in order: the overseer posts a job signed
with the shipped HMAC signer (v2) on the suite's
in-memory fake store, an attacker rewrites the spec in
the store directly, a worker claims with the crew
keyring and is refused, and a watchdog tick on a
snapshot carrying the refusal line yields the alert.
The keyring file holds a drill-only dummy secret and
is removed when the drill finishes. No network, no live
Redis, no bus posts, no Spark calls.

## Results from the landing run

| Stage | What the drill shows | Engaged |
| --- | --- | --- |
| fixture | Signed job 1 posted (v2, overseer), verify OK before tamper | Yes, shipped signer |
| tamper | Spec rewritten in store, shipped verifier says BAD | Yes, shipped verifier |
| claim-refused | Claim refused (exit 1, signature BAD), job stays open, bus line worker: REJECTED:1 BAD signed_by=overseer rejected_by=worker | Yes, already in jobs.py |
| watchdog | One critical rejected-dispatch alert (dedupe key rejected-dispatch:1:BAD), emit received, ALERT line formed, WDG-010 record valid (id = dedupe key, subjects = job, open) | Yes, INT-010 detector |
| negatives | Clean snapshot: none; malformed REJECTED lines: none; duplicate lines: one; dict-shaped EXPIRED line: one EXPIRED alert | Yes, INT-010 detector |
| unsigned-allowed | Unsigned job claims with a warning, no rejected alert | Correct, allowed by design |

## What changed to make the drill pass

Nothing in jobs.py needed changing: claim refusal and
the REJECTED announce already existed and were already
tested. What was missing was the watchdog half: no
detector turned a refusal into an alert record, so a
refused dispatch was visible only while the chat line
scrolled past. INT-010 adds detect_rejected_dispatch
to intel/watchdog.py (registered as the ninth
detector, severity critical in SEVERITY_BY_KIND), plus
its explanation template in intel/explanations.py. The
detector verifies nothing itself: the watchdog holds
no crew secret, so it reports the refusal the worker
computed and must not invent a verdict for a job no
worker refused. One alert per (job, verdict) per tick,
in both snapshot message shapes (raw bus strings and
brief-shaped dicts).

An unsigned job still claims fine with the keyring
(warning only) and fires no rejected alert. Unsigned
is allowed by design, and alerting on it would
contradict that rule; the drill asserts the allowed
path so a future change that blocks it fails loudly.

## Proved and not proved

- Proved: the full refusal chain on the fake store,
  from signing through tamper, refusal, REJECTED line,
  alert record, and announcement line, plus the
  negative cases and the unsigned allowed path.
- Not proved: a live-room refusal. The drill runs on
  the fake store, so the REJECTED line reaching a real
  room, and the dashboard rendering the alert record in
  a browser, are both still unproved. The detector
  also reads only the snapshot window: a refusal line
  older than the tick cap is not re-reported by a
  capped tick, though the record written from the first
  tick persists in the store.
- Fixture note: Buffy's FND-027 spoof fixture (a job
  with a BAD HMAC in a dump) is still unlanded, so the
  drill builds its spoof job with the shipped signer
  plus a real tamper instead of a static dump. The BAD
  verdict comes from the shipped verifier recomputing
  the HMAC, which is stronger evidence than a
  pre-written bad string.
