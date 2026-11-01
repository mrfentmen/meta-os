# Old-tool styles

[source: public repo mrfentmen/meta-musica, `presets.json` and
`AGENTS.md`, read 2026-11-01. These are the OLD tool's presets,
NOT pack briefs. Use them as reference when writing a NEW pack
brief — never present an old-tool preset as a pack brief, and
never claim a pack take was rendered from one.]

## The four demos

| Name | Style | Tempo | Key | Sections |
|---|---|---|---|---|
| rainy-window | lo-fi / chill | 72 | A minor | piano chords, mellow synth bass, soft drums, wind bed |
| neon-drive | synthwave | 100 | C minor | driving bass arpeggio, pads, lead melody, four-on-the-floor drums |
| porch-light | folk / acoustic | 90 | G major | finger-picked pluck, flute melody, soft bass, brush hats |
| hollow-house | dark ambient / horror | 60 | D minor | organ drone, choir pad, sparse drums, wind and low drone |

Moods, as the presets state them: rainy-window calm, warm, late
night; neon-drive driving, neon, night road; porch-light warm,
gentle, outdoors; hollow-house tense, empty, unsettling.

## The six original game tracks

| Name | Style | Tempo | Key | Sections |
|---|---|---|---|---|
| loading-theme | epic game music | 92 | D minor | intro pads, build, main melody, outro |
| battle-theme | epic game music | 140 | E minor | drum build, main riff, outro hits |
| ambient-exploration | epic game music | 60 | A minor | pads, sparse pluck, wind bed |
| menu-theme | epic game music | 80 | D dorian | chord cycle, melody |
| victory-fanfare | epic game music | 120 | D major | snare build, fanfare hits, final hit |
| defeat | epic game music | 60 | D minor | pads, descending lead, tolling drums |

## Old-tool command shapes (for reference only)

- `make NAME --style lofi|synthwave|folk|dark|epic --tempo N
  --key "C minor" --bars N --seed N` — one structured track
  per call. Modes default by style: minor for lofi, synthwave,
  dark, epic; major for folk. Tempo range 40..200, bars 1..32.
- `qc` — file decodes, not silent, peak and loudness in range,
  no silence gap over 2 seconds, stems for one track not copies
  of each other (correlation below 0.99).
- The old tool does not write lyrics, sing, or copy a real
  song. Neither does this pack.

## What carries over, what does not

- Carries over: style names, moods, tempo/key starting points,
  section shapes — all usable as brief-writing reference.
- Does NOT carry over: the stem method (old tool renders one
  stem file per instrument, then mixes with reverb and
  limiting). This pack renders one mixed file directly (see
  `../theory/voices-and-waves.md`). Do not promise stems from
  a pack session.
- Old game music mixes live in the old repo's
  `old-game-music/` as finished mixes, not stems; their stems
  (~1 GB) are not in that repo. No audio from the old repo is
  copied into this corpus.
