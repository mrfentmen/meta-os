# Musica reference corpus

Short notes the composing agent reads BEFORE it composes. Every note
is labelled with its source. Nothing here is a copyrighted lyric or
melody: this is music theory, pack briefs, measured keeper history,
and paraphrased public docs from the old tool.

## How to use it

1. Someone asks for a style: find the genre note first
   (`genres/`). If no genre note matches, read the theory notes
   and write a new brief from them — do not invent a style history.
2. Before a session, read `lessons/keeper-history.md` for what
   actually produced keepers, and the keeper bar in
   `theory/keeper-bar.md` for what a take must pass.
3. After a session, write the measured results back (see
   `lessons/how-to-add-a-lesson.md`). That write-back is the
   improve-over-time loop: every session's keeper history becomes
   tomorrow's reference.

## Index

- `theory/scales-chords.md` — scales, keys, chord progressions
  [source: pack `runtime/compose.py`]
- `theory/voices-and-waves.md` — the four voices, wave shapes,
  gains, envelopes, output format [source: pack `runtime/compose.py`]
- `theory/keeper-bar.md` — keeper rules and the silence audit
  [source: pack `runtime/keepers.py`, `runtime/audit.py`]
- `genres/chipsynth.md` — chipsynth brief + keeper record
  [source: pack `briefs/chipsynth.md` + session take logs]
- `genres/ambient.md` — ambient brief + keeper record
  [source: pack `briefs/ambient.md` + session take logs]
- `genres/boom-bap.md` — boom-bap brief + keeper record
  [source: pack `briefs/boom-bap.md` + session take logs]
- `genres/old-tool-styles.md` — styles the old tool shipped
  [source: public repo mrfentmen/meta-musica, `presets.json`]
- `genres/old-tool-instruments.md` — old-tool instruments, stem
  method, QC list [source: public repo mrfentmen/meta-musica,
  `presets.json` + `AGENTS.md`]
- `lessons/keeper-history.md` — measured keeper history, real
  numbers only [source: session `take_log.jsonl` files]
- `lessons/how-to-add-a-lesson.md` — the write-back procedure
  [source: written note]
- `sources.md` — source register

## Source labels

- `pack` — a file inside `os/worlds/musica` in this repo.
- `keeper history` — measured from session `take_log.jsonl` files.
- `old tool` — public repo mrfentmen/meta-musica (paraphrase only;
  no code and no audio copied into this corpus).
- `written theory` — a note written for this corpus from the
  sources named on it.

## Merge note (read this)

This directory is written to merge on top of the `hana/musica`
pack branch. The pack paths named above (briefs, runtime, sessions)
do not exist on this branch until that pack lands; the notes
describe the pack as it stands on `hana/musica` @ 941134f.
