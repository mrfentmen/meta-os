# Musica adoptions — scouted tools (HN-046, HN-047 notes in HN-047)

Scouted 2026-11-01 for the Musica lane. Licence for each candidate
was checked against its repo's licence record (LICENSE file /
package licence metadata), not taken from a blog summary. Verdicts
are Hana's lane call; adoption is wired only where the verdict
says ADOPT (HN-048).

## 1. basic-pitch — spotify/basic-pitch

- What: lightweight audio-to-MIDI transcription (neural model,
  ONNX / TensorFlow Lite / CoreML runtimes).
- Licence: Apache-2.0 (repo LICENSE file; Spotify's licence
  listing shows the Apache 2.0 text).
- Verdict: CONSIDER. Transcribing keeper audio back to MIDI
  would give the loop a round-trip check (render -> transcribe
  -> compare). Not adopted now: the model runtime is heavy for
  this sandbox, and the loop's own note data already gives the
  melody without transcription.

## 2. pretty_midi — craffel/pretty-midi

- What: utility functions for handling MIDI data (read, write,
  manipulate note lists, piano rolls) in pure Python + NumPy.
- Licence: MIT (GitHub licence detection on the repo's LICENSE
  file: key mit; MacPorts lists MIT).
- Verdict: ADOPT (wired at HN-048). Pure Python, no model, no
  heavy runtime beyond NumPy (already in this sandbox). The loop
  can export each keeper's note sequence as a real MIDI file
  alongside its WAV.

## 3. librosa — librosa/librosa

- What: audio and music analysis in Python (chroma, tempo,
  spectral features, beat tracking).
- Licence: ISC for the library code (PyPI classifiers across
  versions: "OSI Approved :: ISC License"). Caveat found in the
  Fedora review: bundled example audio in the package is CC-BY,
  so the library code and its example data carry different
  licences — only the code would ever be used here.
- Verdict: CONSIDER. The strongest analysis library of the five,
  but its dependency stack (scipy, numba, soundfile) is heavy
  for this lane, and the loop's pure-Python measurement already
  covers keeper/variation needs. Revisit if the keeper bar needs
  chroma or tempo analysis it cannot do itself.

## 4. aubio — aubio/aubio

- What: real-time audio labelling (onset, pitch, tempo, MFCC,
  beat tracking) in C with Python bindings.
- Licence: GPL-3.0-or-later (project licence statement: "GNU
  General Public License ... either version 3 ... or any later
  version"; openSUSE spec: GPL-3.0-or-later).
- Verdict: CONSIDER WITH CAUTION. Copyleft: linking it into the
  loop would carry GPL terms into this lane, so it would only
  ever be used as a separate CLI tool, never vendored. Not
  adopted now: no aubio binary in this sandbox, and the loop's
  own measurement covers current needs.

## 5. Magenta — magenta/magenta

- What: Google's music-generation research project (MelodyRNN,
  MusicVAE, Music Transformer, Magenta RT) on TensorFlow.
- Licence: Apache-2.0 for the codebase; model weights under
  Creative Commons Attribution 4.0 (the two are licensed
  separately — the split matters for anything redistributed).
- Verdict: NOT ADOPTED. Model-based generation does not fit
  this lane's deterministic seeded loop, and the TensorFlow
  runtime is far heavier than anything the studio needs. Kept
  on the list as research interest only.

## Adopted (HN-048)

- pretty_midi (MIT): MIDI export of keeper note sequences.
