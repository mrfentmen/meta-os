# Old-tool instruments

[source: public repo mrfentmen/meta-musica, `presets.json` and
`AGENTS.md`, read 2026-11-01. Paraphrase only; no code and no
audio copied into this corpus.]

## The four newer instruments

- piano — soft piano-like note, stacked harmonics, fast attack,
  long decay.
- flute — breathy wind lead, pure tone plus soft breath noise
  and vibrato.
- organ — organ and choir pad note, drawbar harmonics, steady
  tone.
- synthbass — punchy synth bass, saw plus square sub, short
  plucky shape.

## How the old tool builds sound

No samples. No recordings. No soundfonts. Every sound is built
from sound waves in code. Each instrument gets its own stem
file, all stems line up in time, and a mix is all stems added
together with reverb and limiting. Seeds make renders repeat:
the same seed, style, tempo, key, bars, and name give the same
audio.

## Old-tool QC (for reference)

A track passes when: the file decodes, it is not silent, peak
and loudness are in range, there is no silence gap over 2
seconds, and stems for one track are not copies of each other
(correlation below 0.99). Do not ship, link, or claim a track
that failed QC — that rule carries over to this pack's keeper
bar, even though the checks differ (see
`../theory/keeper-bar.md`).

## What this means for the pack

The pack's loop does not have these four instruments — it has
four voices (pad, bass, melody, hats) built from sine, triangle,
square, and noise. If someone asks for "flute" or "piano", the
honest answer is: the pack cannot render that instrument yet.
Offer the nearest pack voice (triangle melody for flute-like,
soft pad for piano-like) and say what it is — never label a
triangle melody as a flute recording.
