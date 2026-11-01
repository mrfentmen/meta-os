# The keeper bar

[source: pack `runtime/keepers.py` and `runtime/audit.py`.]

## Keeper rules (a take passes or fails measurably)

A take is a keeper when it passes ALL four checks. The verdict
wording on a pass is "passes length, loudness, silence,
repetition". On a fail, the reason names the check that failed.

- Length: duration 5..12 seconds (from the WAV header).
- Loudness: RMS -24..-8 dBFS.
- Silence: silence ratio below 0.25 — the fraction of 50 ms
  windows below -50 dBFS.
- Repetition: repetition score below 0.75.

## Silence audit (HN-052)

For every catalogue track, the audit checks the file on disk:

- it exists,
- its duration matches the logged duration within 0.05 s
  (a shorter file is truncated),
- its RMS is above -50 dBFS (a quieter file is silent),
- its sha256 matches the catalogue entry,
- no two tracks share a file hash.

It writes `audit.json` in the session dir and exits 0 when clean,
1 when any issue is found. In a fresh checkout, take audio that
was never rendered reports as "missing file" — replay it from
the take log first (sessions README), then re-run the audit.

## What this means for composing

The bar is lenient on length, loudness, and silence: in the
measured history every reject was a repetition reject (see
`../lessons/keeper-history.md`). If keeper rate falls, look at
melody repetition first — wider melody steps, more rests, or a
different seed range — before touching tempo or key.
