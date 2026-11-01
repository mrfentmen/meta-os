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

## Keyless music APIs/MCPs beyond Audius (HN-047)

Scouted 2026-11-01. One smoke call each, from the sandbox.
"Keyless" means no API key for the endpoint called. Audius is
excluded by the task (beyond Audius).

### 1. MusicBrainz API — VERIFIED

- Endpoint: musicbrainz.org/ws/2 (artist search, fmt=json).
- Keyless, with a required User-Agent and 1 req/sec courtesy
  limit. Smoke call: artist search for Radiohead returned 200
  with count 7 and the artist record. Use: metadata lookup for
  catalogue enrichment (never for track audio).
- Verdict: USABLE, with rate-limit respect.

### 2. iTunes Search API — VERIFIED

- Endpoint: itunes.apple.com/search (media=music).
- Keyless, no registration. Smoke call: search for Radiohead
  returned resultCount 1 with a real track record (Let Down, OK
  Computer). Use: metadata lookup only.
- Verdict: USABLE.

### 3. Openverse Audio API — UNVERIFIED (bot check)

- Endpoint: api.openverse.org/v1/audio.
- Keyless in principle for anonymous search, but the smoke call
  from this sandbox was blocked by a Cloudflare bot check (403,
  "Just a moment..." challenge page; healthcheck also 403).
  That is a sandbox egress block, not a key requirement, but it
  means the endpoint is NOT verified from here.
- Verdict: NOT ADOPTED until verified from an unblocked host.

### 4. Deezer public API — VERIFIED

- Endpoint: api.deezer.com/search.
- Keyless for basic search. Smoke call: search for Radiohead
  returned a real track record (Creep) with a 30-second preview
  URL. Previews are Deezer-hosted; they are never catalogue
  audio, only reference listening.
- Verdict: USABLE for reference search.

### 5. Wikimedia Commons API — VERIFIED

- Endpoint: commons.wikimedia.org/w/api.php (file search).
- Keyless for search. Smoke call: file search for piano audio
  returned 11,354 hits with a real file record (a 1916 Scott
  Joplin piano-roll recording). Files carry their own licences
  per file; any reuse must check the file's licence, not assume
  public domain.
- Verdict: USABLE for CC-licensed reference audio discovery.

