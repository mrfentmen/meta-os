# Demo audio take log

## WDG-031 — opening product framing (added 2026-10-27)

Task: WDG-031 — opening 20-second product framing voiceover, two takes.
Demo placement: the opening framing, ahead of DEMO.md shot 1 (the cold open);
wording builds on Dale's framing from DEMO.md ("My bus moves messages and
jobs between agents well. What it cannot do yet is understand them. This is
the layer that understands."). Path note: same as WDG-030 — the plan's
`hackathon/relay-intelligence/demo-assets/audio/` path is stale for this
repo, so takes live at repo-root `demo-assets/audio/`. Pick at rehearsal:
Dale picks the take; no take is marked final here.

| Take | File | Voice | Length |
| ---- | ---- | ----- | ------ |
| 1 | `wdg031-opening-framing-take1.mp3` | Helio (default production voice) | 19.9 s |
| 2 | `wdg031-opening-framing-take2.mp3` | Aria | 17.7 s |

Both takes read the same script below, so the choice at rehearsal is voice
and pacing only, not wording. Both files verified as MP3 (ID3 2.3, MPEG
layer III) with the durations above measured by ffprobe on 2026-10-27.
Take 1 lands essentially on the 20-second target; take 2 runs a little
faster, which is a pacing choice, not a wording difference.

### Script (both takes, verbatim)

> My crew talks on a bus that moves messages and jobs between agents well.
> What it cannot do yet is understand them. This is the layer that
> understands. Relay Intelligence reads the room, writes the brief, takes
> orders in plain English, and catches the failure nobody announced. One
> order, and the crew works until it is done and checked.

### What is NOT claimed here

- Timing sync to the shot list is WDG-032 (a separate timing sheet), not done
  in this log.
- Listening check on the demo machine speakers/headphones is DEM-018, still
  open; these takes were verified as files only, not played on demo hardware.
- No live narration was recorded from a human voice; these are synthesized
  takes in Milo's voice lane, to be replaced or approved at rehearsal.

---

## WDG-030 (watchdog segment)

Task: WDG-030 — watchdog segment voiceover, the "silent failure" story, two takes.
Demo shots covered: DEMO.md shot 7 (the silent failure) and shot 8 (the catch).
Path note: the plan names `hackathon/relay-intelligence/demo-assets/audio/`;
that path is stale for this repo, so takes live at repo-root `demo-assets/audio/`
(the same layout the rest of the repo uses). Pick at rehearsal: Dale picks the
take; no take is marked final here.

## Takes

| Take | File | Voice | Length |
| ---- | ---- | ----- | ------ |
| 1 | `wdg030-watchdog-segment-take1.mp3` | Helio (default production voice) | 48.1 s |
| 2 | `wdg030-watchdog-segment-take2.mp3` | Aria | 44.6 s |

Both takes read the same script below, so the choice at rehearsal is voice and
pacing only, not wording. Both files verified as MP3 (ID3 2.3, MPEG layer III)
with the durations above measured by ffprobe on 2026-10-27.

## Script (both takes, verbatim)

> Here is the failure nobody sees. A worker picks up a job, posts one progress
> note, and then goes quiet. No error. No crash message. The room looks calm,
> the job looks claimed, and nothing is actually moving. This is how agent work
> usually dies, quietly, while everyone assumes someone else is handling it.
> The watchdog does not assume. It watches every claim, every lease, and every
> heartbeat. Ninety seconds after the last progress note, with no heartbeat
> and no movement, it fires. One red stall alert: the worker, the job, and
> exactly how long it has been silent, in plain English, with a fix. The lease
> is expiring soon, so requeue the job to another worker, or nudge the first
> one. The silent failure stops being silent.

## What is NOT claimed here

- Timing sync to the shot list is WDG-032 (a separate timing sheet), not done
  in this log.
- Listening check on the demo machine speakers/headphones is DEM-018, still
  open; these takes were verified as files only, not played on demo hardware.
- No live narration was recorded from a human voice; these are synthesized
  takes in Milo's voice lane, to be replaced or approved at rehearsal.

## WDG-033 — fallback narration, full demo (added 2026-10-27)

Task: WDG-033 — fallback narration: full-demo voiceover track in case live
narration fails on the day.
File: `wdg033-fallback-full-demo.mp3`, single mixed track, Helio voice
(same voice as the WDG-030/WDG-031 take-1 clips), 324.4 s (5:24) measured
by ffprobe on 2026-10-27. That is inside the DEMO.md ~6-minute story arc,
so the track fits the demo slot with room for the live beats and pauses.
Script saved alongside as `wdg033-fallback-script.txt` (17 turns, one voice).
Coverage: opening framing (WDG-031 wording reused), cold open, brief, crew
board, dispatch and phone-down, five-job plan, crew moves, OS-run tools
(shot 6b), mind images (shot 6c), silent failure and catch (WDG-030 wording
reused), capability refusal (shot 8b), recovery, collision, honest-limits
note, close and end card. The gated second-machine beat (shot 6d) is not
narrated, since it runs only if OS-115 approves it.

### What is NOT claimed here

- Final-mix take selection is DEM-014, still open; this track is the
  fallback, not the picked final mix.
- Listening check on the demo machine speakers/headphones is DEM-018,
  still open; this track was verified as a file only, not played on demo
  hardware.
- Mixing into the DEM-003 fallback video is a later step; this is the
  standalone narration track.
- No live narration was recorded from a human voice; this is a synthesized
  track in Milo's voice lane, to be replaced or approved at rehearsal.

## WDG-034 — demo stingers (added 2026-10-27)

Task: WDG-034 — audio stingers: subtle alert sound + success sound for demo
transitions, original or CC0 only, license noted.

| File | Sound | Length |
| ---- | ----- | ------ |
| `wdg034-alert-sting.mp3` | Soft two-tone chime, A5 then E5 sine tones, low volume, faded | 1.2 s |
| `wdg034-success-sting.mp3` | Quiet ascending arpeggio, C5-E5-G5 sine tones | 1.4 s |

Both synthesized from scratch with a Python sine generator (no samples, no
third-party audio); license note in `demo-assets/audio/LICENSES.md`. Both
files verified as MP3 with ffprobe on 2026-10-27 and decode cleanly.
Listening check on the demo machine speakers/headphones is DEM-018, still
open; these were verified as files only, not played on demo hardware.

## DEM-015 — watchdog-moment caption voiceover (added 2026-10-27)

Task: DEM-015 — 15-second "what you are seeing" caption voiceover for the
watchdog moment, for the fallback video.
File: `dem015-caption-watchdog-moment.mp3`, Helio voice (same as the
WDG-030/WDG-031 take-1 clips and the WDG-033 fallback track, so it cuts
against them without a voice change), 14.5 s measured by ffprobe on
2026-10-27 (rendered at speed 90 to land near the 15-second target; the
first render at full speed ran 13.2 s).

### Script (verbatim)

> What you are seeing: a worker claimed a job, posted once, then went
> silent. No error, no crash. The watchdog caught it, ninety seconds in,
> and fired one red stall alert, in plain English, with a fix.

### What is NOT claimed here

- Placement into the DEM-003 fallback video edit is still open; that edit
  is a later step, and this clip is the asset it consumes.
- Listening check on the demo machine speakers/headphones is DEM-018,
  still open; this clip was verified as a file only, not played on demo
  hardware.
- No live narration was recorded from a human voice; this is a synthesized
  clip in Milo's voice lane, to be replaced or approved at rehearsal.
- Pinning tests: `tests/test_intel_demo_caption.py` (2 tests: MP3 header
  present, duration 12-18 s).

## DEM-017 — ambient crew audio bed (added 2026-10-27)
Task: DEM-017 — ambient crew audio bed (very low, royalty-free/CC0,
license noted) for the fallback video.
File: `dem017-ambient-bed.mp3`, 60 s, synthesized original: soft low pad
(C3/E3/G3/C4 sine tones, slow 0.1 Hz swell, 2 s fades, peak ~0.08), made
to loop under narration with a short crossfade in the edit. License
note in `demo-assets/audio/LICENSES.md`. Pinning tests:
`tests/test_intel_demo_ambient.py` (3 tests: MP3 header, duration
55-65 s, mean volume below -30 dB).

### What is NOT claimed here

- Placement into the DEM-003 fallback video edit is still open; that edit
  is a later step, and this bed is the asset it consumes.
- Listening check on the demo machine speakers/headphones is DEM-018,
  still open; this bed was verified as a file only (ffprobe duration,
  clean decode, volumedetect mean), not played on demo hardware.
- No third-party or CC0 audio is used in this file, so the license note
  records an original work, not an attribution.

## OS-039 — boot audio (added 2026-10-27)
Task: OS-039 — a short sting plus one voice line for the boot moment of the
demo. Lane path: `submission-assets/audio/` (this is the first task to land
files there; the DEM-003 fallback cut that will consume them is Pax's task,
not landed yet).

| File | Content | Length |
| ---- | ------- | ------ |
| `submission-assets/audio/os039-boot-sting.mp3` | Gentle rising arpeggio C4-E4-G4-C5, synthesized sine tones, peak 0.15, faded | 2.00 s |
| `submission-assets/audio/os039-boot-voice-line.mp3` | Helio voice (same as WDG-030/031 take 1 and the WDG-033 fallback track) | 4.03 s |

### Voice line (verbatim)

> Meta OS is up. The crew is awake, and the watchdog is watching.

### What is NOT claimed here

- Placement into the DEM-003 fallback cut is still open; that cut is not
  landed, and this task proves the assets only (short, clean, unclipped, and
  mixed without clipping — see `intel/evals/boot_audio.md` and the check
  script `intel/boot_audio_check.py`, 10/10 PASS).
- Listening check on the demo machine speakers/headphones is DEM-018, still
  open; these files were verified by measurement only, not played on demo
  hardware.
- Pinning tests: `tests/test_intel_os039_boot_audio.py` (5 tests).

## DEM-014 — narration final mix, provisional (added 2026-10-28)

Task: DEM-014 — narration final mix: combine picked takes, level-check
against screen capture audio.
File: `dem014-final-mix.mp3`, 68.49 s, one MP3 track: WDG-031 opening
framing take 1 (Helio, 19.92 s) + 0.5 s silence + WDG-030 watchdog segment
take 1 (Helio, 48.07 s). Check script `intel/final_mix_check.py`
(11/11 PASS): mix decodes clean, length exact, peak -6.7 dB (no clipping,
within 0.6 dB of the louder input, so no level jump at the join).
Eval: `intel/evals/final_mix.md`. Pinning tests:
`tests/test_intel_dem014_final_mix.py` (3 tests).

### What is NOT claimed here

- This mix is PROVISIONAL, not final: Dale has not picked takes at
  rehearsal yet. Take 1 of each is the provisional pick (Helio, the
  default production voice, matching the fallback track and caption).
  If Dale picks take 2, the mix is rebuilt from take 2.
- Sync into the DEM-003 fallback video is still open; that edit is not
  landed, so the mix is not yet placed in any video timeline.
- Level check against screen-capture audio is still open: no screen
  capture exists yet. The check runs against the narration assets plus
  the WDG-033 fallback track as a same-voice reference (-5.5 dB peak,
  reported not forced). Re-check against capture audio when the
  fallback video lands, before calling the mix final.
- Listening check on the demo machine speakers/headphones is DEM-018,
  still open; this mix was verified by measurement only.
- No live narration was recorded from a human voice; synthesized takes
  in Milo's voice lane, to be replaced or approved at rehearsal.
