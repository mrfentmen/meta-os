# DEM-018 local pre-check: all demo audio assets decode clean (2026-10-28)

DEM-018's acceptance is a listening check logged with the demo machine
named — speakers and headphones on the actual demo hardware. That check
is still OPEN: no demo machine is named, and this VM has no
speakers/headphones to listen on, so no one has heard these files on
demo hardware. This note records the local pre-check only; it does not
close DEM-018.

## Check

`python3 intel/dem018_local_check.py` — 49/49 PASS: all 12 assets
present as MP3, decoding cleanly through ffmpeg, with sane durations
and peaks below 0 dB (no clipping).

| Asset | Duration | Peak |
| --- | --- | --- |
| demo-assets/audio/wdg030-watchdog-segment-take1.mp3 | 48.07 s | -7.9 dB |
| demo-assets/audio/wdg030-watchdog-segment-take2.mp3 | 44.64 s | -7.2 dB |
| demo-assets/audio/wdg031-opening-framing-take1.mp3 | 19.92 s | -6.1 dB |
| demo-assets/audio/wdg031-opening-framing-take2.mp3 | 17.69 s | -6.6 dB |
| demo-assets/audio/dem014-final-mix.mp3 | 68.49 s | -6.7 dB |
| demo-assets/audio/wdg033-fallback-full-demo.mp3 | 324.38 s | -5.5 dB |
| demo-assets/audio/dem015-caption-watchdog-moment.mp3 | 14.52 s | -7.7 dB |
| demo-assets/audio/dem017-ambient-bed.mp3 | 60.00 s | -23.7 dB |
| demo-assets/audio/wdg034-alert-sting.mp3 | 1.20 s | -12.5 dB |
| demo-assets/audio/wdg034-success-sting.mp3 | 1.40 s | -12.5 dB |
| submission-assets/audio/os039-boot-sting.mp3 | 2.00 s | -16.4 dB |
| submission-assets/audio/os039-boot-voice-line.mp3 | 4.03 s | -7.4 dB |

## Reading

- Narration assets cluster tightly (-5.5 to -7.9 dB peak), so no level
  jump is expected when the mix, fallback track, and caption cut
  against each other.
- Quiet assets are quiet by design: the ambient bed (-23.7 dB) and the
  stingers (-12.5 dB, boot sting -16.4 dB) sit under narration, as
  their own checks already required.
- Peak spread across all assets is 18.2 dB, reported not gated — the
  bed and stingers are meant to be quiet.

## Still owed (DEM-018 proper)

Play every asset on the named demo machine, on its speakers and on
headphones, and log the machine name plus any level or intelligibility
issue found there. Until that session happens, DEM-018 stays open and
this pre-check is the record the session starts from.
