# Meta Musica eval — first slice

Musica-studio was already hosted on main (registry `musica-studio`,
`os/worlds/musica/hosted.mjs`) but eval/ had no musica harness, so
there was no Musica baseline for "whatever raises eval scores" to be
measured against. This is Musica's first: a small offline replay of
committed records.

## What it scores

Ten scenarios, all from records already in the repo:

| id | what it replays | recorded value it must match |
|---|---|---|
| MUS-KEEP-01 | keeper bar on hn029 take-001's measurement | keeper: 7.273 s, -13.8 dBFS, silence 0.0, repetition 0.5 |
| MUS-KEEP-02 | keeper bar on hn029 take-004's measurement | reject: repetition 1.000 >= 0.75 (the session's only reject) |
| MUS-SESS-01 | hn029-chipsynth session counts | 12 takes, 11 keepers, 1 reject, 0 clones |
| MUS-SESS-02 | overnight-001 session + overnight report | 100 takes, 85 keepers, 15 rejects, 0 clones, 76.6 s, reject rate 0.15 |
| MUS-SESS-03 | hn038 brief sessions (chipsynth, ambient, boom-bap) | 4 takes, 4 keepers, 0 rejects, 0 clones each |
| MUS-VAR-01 | variation calibration from similarity.py | 0.9242 not a clone, 0.9997 a clone, threshold 0.98 (strictly greater) |
| MUS-RIGHTS-01 | hn029 rights log + rights rule | 11 checked, 11 passed, 0 rejected; an empty rights line fails |
| MUS-NORM-01 | hn029 normalisation | target -16 LUFS, tolerance 1.0, all 11 tracks within tolerance (recomputed, not just trusted) |
| MUS-CAT-01 | hn029 catalogue | 11 tracks, every track with licence, provenance, file, sha256 |
| MUS-CAT-02 | overnight-001 catalogue | 85 tracks, same per-track fields |

No audio is rendered, no model is called, no live key is read, no
take is invented. The bar, threshold, and rights rule are copied
from `runtime/keepers.py`, `runtime/similarity.py`, and
`runtime/rights.py`; the adapter tests pin them to the real hn029
measurements, so a drift in any of those files shows up here.

## What the numbers mean

A passing replay means the code still reads its own records the same
way. It does not rate live composition, and it does not claim any
take beyond the committed sessions (hn029, hn038 x3, overnight-001).
Sessions after hn029 keep audio as reproducible working output, not
committed audio — the replay reads their logs and catalogues, never
their audio, so that policy is untouched.

## Run it

```
node eval/musica/run.mjs              # real records, exits 1 on any replay miss
node eval/musica/run.mjs --baseline   # always-reject fixture; sets the bar
node --test eval/musica/adapter.test.mjs
```

The baseline passes exactly one scenario (MUS-KEEP-02, the recorded
reject) and fails the other nine. That gap is the bar: a real run
must beat 1/10 by replaying all ten.
