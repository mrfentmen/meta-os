# Demo audio licenses

## WDG-034 — stingers (original works, no third-party material)

| File | Sound | Length | License |
| ---- | ----- | ------ | ------- |
| `wdg034-alert-sting.mp3` | Subtle alert chime for demo transitions: soft A5 (880 Hz) then E5 (659.25 Hz) sine tones, low volume, faded in and out | 1.2 s | Original — synthesized for this demo by Milo's lane from a Python sine generator; no samples, no third-party audio. Free to use in the demo and submission. |
| `wdg034-success-sting.mp3` | Success chime for demo transitions: quiet ascending arpeggio C5 (523.25 Hz), E5 (659.25 Hz), G5 (783.99 Hz) sine tones | 1.4 s | Original — synthesized for this demo by Milo's lane from a Python sine generator; no samples, no third-party audio. Free to use in the demo and submission. |

Both files verified as MP3 with ffprobe on 2026-10-27 and decode cleanly.
No CC0 or other licensed material is used in these two files, so there are
no attribution obligations for them.

## DEM-017 — ambient crew audio bed (original work, no third-party material)

| File | Sound | Length | License |
| ---- | ----- | ------ | ------- |
| `dem017-ambient-bed.mp3` | Very low ambient bed for the fallback video: soft low pad of C3 (130.81 Hz), E3 (164.81 Hz), G3 (196.00 Hz), C4 (261.63 Hz) sine tones with a slow 0.1 Hz swell, 2 s fade in / 2 s fade out, peak ~0.08, meant to loop under narration with a short crossfade in the edit | 60 s | Original — synthesized for this demo by Milo's lane from a Python sine generator; no samples, no third-party audio. Free to use in the demo and submission. |

Verified as MP3 with ffprobe on 2026-10-27 (60.0 s) and decodes
cleanly; volumedetect mean volume -33.4 dB, max -23.7 dB, and the
pinning test in `tests/test_intel_demo_ambient.py` holds its mean volume
below -30 dB, so it sits under narration rather than competing with it.
No CC0 or other licensed material is used in this file, so there are no
attribution obligations for it.

## Narration takes (WDG-030 / WDG-031 / WDG-033)

Synthesized voice takes in Milo's voice lane; see TAKE_LOG.md for voices,
scripts, and lengths. No third-party audio is used in those files either.

## OS-039 — boot audio (original works, no third-party material)

| File | Sound | Length | License |
| ---- | ----- | ------ | ------- |
| `submission-assets/audio/os039-boot-sting.mp3` | Gentle rising arpeggio C4 (261.63 Hz), E4 (329.63 Hz), G4 (392.00 Hz), C5 (523.25 Hz) sine tones, peak 0.15, faded in and out | 2.00 s | Original — synthesized for this demo by Milo's lane from a Python sine generator; no samples, no third-party audio. Free to use in the demo and submission. |
| `submission-assets/audio/os039-boot-voice-line.mp3` | Fresh Helio voice synthesis: "Meta OS is up. The crew is awake, and the watchdog is watching." | 4.03 s | Original — synthesized for this demo by Milo's lane; no samples, no third-party audio. Free to use in the demo and submission. |

Both files verified as MP3 with ffprobe on 2026-10-27 and decode cleanly;
sting peak -16.4 dB sits below the voice peak -7.4 dB, and a sting-then-voice
mix measures max -7.3 dB (no clipping). No CC0 or other licensed material
is used in these files, so there are no attribution obligations for them.
Placement into the DEM-003 fallback cut is still owed (that cut is not
landed); listening check on demo hardware is DEM-018, still open.
