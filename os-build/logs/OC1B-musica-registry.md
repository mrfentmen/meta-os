# OC1B §15 — Musica real run (OC1B-351..375)

Tree: `94010c76ee095fa6c6bcfa4405cd56a9695f32d3`. Date (UTC): 2026-11-02.
Suite wall-clock: run1 14 s, run2 12 s, run3 13 s (in-suite duration_ms ~14.4 s).

## Basal / install / after (OC1B-351..356, 365..368, 372)

- OC1B-351 basal = Bond's exact command `node --test tests/musica-*.test.mjs`,
  before any change: **39 tests, 39 pass, 0 fail** (full log
  `os-build/logs/OC1B-musica-basal-full.txt`, summary
  `os-build/logs/OC1B-musica-basal.txt`).
- OC1B-352: basal failures = NONE. `pretty_midi` 0.2.11.post0 was already
  installed machine-wide (`/Users/test/Library/Python/3.9/lib/python/site-packages`),
  so Bond's two `ModuleNotFoundError: pretty_midi` failures
  (`os/worlds/musica/runtime/midi.py:39`) could not reproduce here; the MIDI
  test passes: "MIDI export writes the take's own notes via pretty_midi".
- OC1B-353: no install performed (already present). Version: 0.2.11.post0 —
  `os-build/logs/OC1B-musica-install.txt`.
- OC1B-354 after-run: 39/39 pass (`os-build/logs/OC1B-musica-after.txt` +
  `-full.txt`). OC1B-355: no remaining failures. OC1B-368: no other missing
  dependency surfaced (one-dependency scope untriggered).
- OC1B-356: the Node Musica suite IS this 28-file suite
  (`tests/musica-*.test.mjs`); no separate Python Musica suite exists — the
  Python runtime is exercised through these tests (compose/keepers/midi
  subprocesses). Same count, recorded once
  (`os-build/logs/OC1B-musica-node.txt` = run-2 log copy).
- OC1B-365 stability re-run: 39/39 again (`os-build/logs/OC1B-musica-after2.txt`).
- OC1B-367 delta vs Bond 37/2: +2 tests in tree since his run; both old
  failures resolved by the pre-existing pretty_midi install.
- OC1B-366 future-Mac line: `python3 -m pip install pretty_midi==0.2.11.post0`.

## Registry (OC1B-357..361)

- OC1B-357 registered command for `musica-studio` in `agents/registry.json`:
  `"command": ["true"]` (lane "Musica overnight sessions", draft: true,
  draftReason: "Musica lives outside this repo; no real command can be named here").
- OC1B-358 existence check: NO file backs the command — it is a placeholder
  (`["true"]`-style), not a verified entry point.
- OC1B-359/360: NOT RUN — the command does not verify, so no first run and no
  artifact by design (running `true` would prove nothing).
- OC1B-361 verdict: **DRAFT STAYS DRAFT** — placeholder command, no runnable
  entry in `agents/registry.json`; the real runnable entries live in
  `os/worlds/musica/runtime/` (`overnight.py`, `gate_packet.py`, both run for
  real below) but the registry rule upgrades nothing by assertion.

## Gate packet + keeper (OC1B-362/363)

- OC1B-362: `python3 os/worlds/musica/runtime/gate_packet.py os/worlds/musica
  --out /tmp/oc14-gp ...` → exit 0, 19 s, packet built outside the tree
  (`os-build/logs/OC1B-musica-gate.txt`). VERDICT: runnable.
- OC1B-363: keeper short form `python3 os/worlds/musica/runtime/overnight.py
  --session-dir /tmp/oc14-keeper --brief-file .../briefs/chipsynth.md --takes 4
  --seed-base 17000` → exit 0, 7.2 s: takes=4 keepers=4 rejects=0
  reject_rate=0.0 catalogue_delta=4 rights_violations=0. Log:
  `os-build/logs/oc1b-musica/keeper.txt`, report
  copy `os-build/logs/oc1b-musica/keeper-report.json`.

## Face data (OC1B-364)

Present, verified, nothing built: `design/meta-musica-notes.html` (dark studio,
3D notes, Hana's HN-029 lane, placeholder melody honestly labelled) and
`os-build/face/musica.html` (hn029-chipsynth take-006 player).

## Verdict + hygiene (OC1B-369..373)

- OC1B-369 section verdict: suite 39/39 STABLE, registry DRAFT STAYS DRAFT
  (correct per the registry rule), keeper REAL RUN DONE (exit 0).
- OC1B-370 spend: none — no model calls in any Musica run here.
- OC1B-371: `git status` for os/worlds/musica/ clean (runs wrote to /tmp and
  to ` staging/` outside repo... verify at commit). No Musica source edited.
- OC1B-373 defects: no code defects; the only dependency (pretty_midi) was
  pre-satisfied. No-defects line stands for code.
- OC1B-374/375: Musica rows + commit sha in
  `os-build/logs/OC1B-s14-STATUS-SNIPPET.md` (status file owned by coordinator).
