# OS-039 — boot audio (Milo, 2026-10-27)

## Assets

| File | Content | Length | Peak |
| ---- | ------- | ------ | ---- |
| `submission-assets/audio/os039-boot-sting.mp3` | Gentle rising arpeggio C4-E4-G4-C5, synthesized sine tones, peak 0.15, faded | 2.00 s | -16.4 dB |
| `submission-assets/audio/os039-boot-voice-line.mp3` | Helio voice (same voice as WDG-030/031 take 1 and the WDG-033 fallback track): "Meta OS is up. The crew is awake, and the watchdog is watching." | 4.03 s | -7.4 dB |

## Check

`python3 intel/boot_audio_check.py` — 10/10 PASS on 2026-10-27: both files MP3
(ID3) and decode clean; sting 2.00 s; voice line 4.03 s; sting peak below
voice peak (so it sits under narration); sting mean -24.6 dB; a
sting-then-voice concat renders with mix max -7.3 dB, i.e. no clipping.

Pinning tests: `tests/test_intel_os039_boot_audio.py` (5 tests).

## What is NOT proven here

- The audio playing over the boot shot in the DEM-003 fallback cut: that cut
  is Pax's task and is not landed, so placement into the edit is still owed.
  What this task proves is the assets the cut consumes — short, clean,
  unclipped, and mixed without clipping — the same boundary as DEM-015 and
  DEM-017 drew.
- Playback on the demo machine speakers/headphones: that is DEM-018, still
  open; these files were verified by measurement only, not played on demo
  hardware.
- No third-party or CC0 audio is used: the sting is synthesized from scratch
  and the voice line is a fresh synthesis, so there are no attribution
  obligations; see `demo-assets/audio/LICENSES.md`.
