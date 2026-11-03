# OC2B §19 — Musica real runs on the Mac (OC2B-451–456, 468, 472)

Branch: `opencode2/500`. Runner: this subagent. No goose runner files touched.
`tests/` additions: none (existing suite covered everything; no new test file written).
Musica artifacts (small): the four `.mid` files named below, committed alongside this log.

## OC2B-451 — pretty_midi install (route + version)

- Route: `pip3 install pretty_midi` (`/usr/bin/pip3`, `python3` = Python 3.9.6, `/usr/bin/python3`).
  `pip` alone is NOT on PATH on this Mac; `pip3` is the working route.
- Result: `Requirement already satisfied` — pretty_midi **0.2.11.post0** already present at
  `/Users/test/Library/Python/3.9/lib/python/site-packages` (deps: mido, importlib_resources, numpy, six).
- Version proof: `python3 -c "from importlib.metadata import version; print(version('pretty_midi'))"` → `0.2.11.post0`.

## OC2B-452 — full Musica suite on the Mac

Command: `node --test tests/musica-*.test.mjs` (29 test files, repo root `/Users/test/meta-os-500`).

Tail (verbatim):
```
✔ loop with --spark-assist records an attempt per take (1886.661834ms)
✔ take-log schema accepts good takes and rejects broken ones (55.239667ms)
✔ variation pass rejects a near-identical clone (1298.607667ms)
ℹ tests 39
ℹ suites 0
ℹ pass 39
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 11826.900708
```

Counts: **39 pass / 0 fail** (prior Bond run: 37 pass / 2 fail, both missing pretty_midi —
now resolved by the installed 0.2.11.post0; see OC2B-453).

## OC2B-453 — re-run of the two previously-failing tests

The two tests that need pretty_midi (`midi.py` stage): `tests/musica-midi.test.mjs`,
`tests/musica-export.test.mjs` (both invoke `runtime/midi.py`, which fails loudly without the package).

- `node --test tests/musica-midi.test.mjs` → **PASS** (tests 1, pass 1, fail 0):
  `✔ MIDI export writes the take's own notes via pretty_midi (2910.96925ms)`.
- `node --test tests/musica-export.test.mjs` → **PASS** (tests 2, pass 2, fail 0):
  `✔ one command bundles tracks, catalogue, and rights …`,
  `✔ bundle lists missing files instead of hiding them …`.

Note (own-instrumentation artifact, NOT a product failure): one parallel run of
`musica-midi.test.mjs` executed concurrently with a full-suite run failed with
`FileNotFoundError: .../staging/musica-midi-test/midi/take-002.mid` — both processes share the
staging dir `/Users/test/staging/musica-midi-test` and one `rmSync` raced the other's `midi.write`.
Sequential rerun is green (see above). No product code changed.

## OC2B-454 — generation path 1 end to end (pack runtime entry)

Runtime entry the pack names: `os/worlds/musica/runtime/compose.py` (composition loop CLI) →
`keepers.py` → `midi.py` (`python3 midi.py SESSION_DIR` per its docstring; MIDI export via pretty_midi).

```
python3 os/worlds/musica/runtime/compose.py --session-dir /tmp/oc2b-musica-path1-chipsynth \
  --brief-id chipsynth --takes 2 --seed-base 45100
  take-001 seed=45101 duration=7.273 sha256=92bb25c97b27
  take-002 seed=45102 duration=7.273 sha256=3c6153f3b873
python3 os/worlds/musica/runtime/keepers.py /tmp/oc2b-musica-path1-chipsynth
  keepers=2 rejects=0 takes=2
python3 os/worlds/musica/runtime/midi.py /tmp/oc2b-musica-path1-chipsynth
  midi exported takes=2 tool=pretty_midi
```

Artifacts saved:
- `os-build/logs/OC2B-musica-path1-chipsynth-take-001.mid` — 259 bytes
- `os-build/logs/OC2B-musica-path1-chipsynth-take-002.mid` — 279 bytes

## OC2B-455 — generation path 2 (a brief from os/worlds/musica/briefs)

Brief: `os/worlds/musica/briefs/ambient.md` (72 BPM, F major, triangle, 2 bars), same loop→keeper→MIDI path:

```
python3 os/worlds/musica/runtime/compose.py --session-dir /tmp/oc2b-musica-path2-ambient \
  --brief-id ambient --tempo 72 --key F --mode major --waveform triangle --bars 2 \
  --takes 2 --seed-base 45200
  take-001 seed=45201 duration=6.667 sha256=f3ae993954db
  take-002 seed=45202 duration=6.667 sha256=7c817e2841c3b873
python3 os/worlds/musica/runtime/keepers.py /tmp/oc2b-musica-path2-ambient
  keepers=2 rejects=0 takes=2
python3 os/worlds/musica/runtime/midi.py /tmp/oc2b-musica-path2-ambient
  midi exported takes=2 tool=pretty_midi
```

Artifacts saved:
- `os-build/logs/OC2B-musica-path2-ambient-take-001.mid` — 178 bytes
- `os-build/logs/OC2B-musica-path2-ambient-take-002.mid` — 178 bytes

## OC2B-456 — parse-check (pretty_midi loads every output)

```
.../OC2B-musica-path1-chipsynth-take-001.mid OK instruments=2 notes=26
.../OC2B-musica-path1-chipsynth-take-002.mid OK instruments=2 notes=29
.../OC2B-musica-path2-ambient-take-001.mid OK instruments=2 notes=15
.../OC2B-musica-path2-ambient-take-002.mid OK instruments=2 notes=15
```
All four files parse via `pretty_midi.PrettyMIDI`: 2 instruments each (Lead 1 square program 80 + Synth Bass program 38), notes > 0.

## OC2B-472 — artifact size verification (each ≤ 1 MB or justified)

| Artifact | Bytes | ≤ 1 MB? |
|---|---|---|
| OC2B-musica-path1-chipsynth-take-001.mid | 259 | yes |
| OC2B-musica-path1-chipsynth-take-002.mid | 279 | yes |
| OC2B-musica-path2-ambient-take-001.mid | 178 | yes |
| OC2B-musica-path2-ambient-take-002.mid | 178 | yes |

All four ≤ 1 MB by three orders of magnitude; no justification needed. (Working WAVs under
`/tmp/oc2b-musica-path*/takes/` are ~320 KB each and were NOT committed — MIDI only, per repo-lean rule.)

## OC2B-468 — MAC-ONLY failures (Musica half)

- MAC-ONLY: none. No Musica failure on this Mac lacks a sandbox reproduction; the one transient
  (`staging/musica-midi-test` race) was this runner's own parallel execution, clean on sequential rerun.

## Proposed §19 status sub-block — Musica (NOT applied; status file untouched per spawn rules)

```
### §19 Musica (OC2B-451–456, 468, 472) — DONE on the Mac, status file edit pending owner
- pretty_midi 0.2.11.post0 via `pip3 install pretty_midi` (`pip` absent on this Mac).
- Full suite: 39 pass / 0 fail (prior 37/2 both missing pretty_midi, now green).
- Re-runs: musica-midi 1/1 PASS; musica-export 2/2 PASS.
- Path 1 (compose→keepers→midi, chipsynth): 2 keepers, 2 .mid (259/279 B).
- Path 2 (ambient brief): 2 keepers, 2 .mid (178/178 B); all 4 parse via pretty_midi.
- Artifacts ≤ 1 MB, no justification needed. MAC-ONLY: none. tests/ additions: none.
```

Musica truth line: Musica renders real takes and keeper MIDI end to end on the Mac with the full suite green at 39/39.
