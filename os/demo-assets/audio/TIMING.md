# Demo narration timing sheet (WDG-032)

Maps each recorded narration clip to the DEMO.md shot(s) it covers, with
lengths measured by ffprobe on 2026-10-27. All clips live in this directory
(`demo-assets/audio/` at repo root; the plan's
`hackathon/relay-intelligence/demo-assets/audio/` path is stale for this repo).

The demo arc is ~6 minutes (DEMO.md); the clips below cover the opening
framing and the watchdog segment. No take is marked final — Dale picks takes
at rehearsal (see TAKE_LOG.md).

| Clip | DEMO.md shot(s) | Length (take 1) | Length (take 2) | Notes |
| ---- | --------------- | --------------: | --------------: | ----- |
| `wdg031-opening-framing-take1/2.mp3` | Ahead of shot 1 (cold open) | 19.9 s (Helio) | 17.7 s (Aria) | Opening product framing; runs before the raw-bus cold open, not over it. Take 1 lands on the 20-second target. |
| `wdg030-watchdog-segment-take1/2.mp3` | Shots 7–8 (the silent failure → the catch) | 48.1 s (Helio) | 44.6 s (Aria) | One continuous clip spanning both shots: the silent-failure story (shot 7) into the watchdog catch (shot 8). |

## Shot-by-shot placement notes

- **Opening framing → shot 1:** the clip plays as the framing intro, then
  shot 1 (raw bus wall) runs without narration over it. Total intro budget:
  ~20 s, matching the WDG-031 20-second target.
- **Watchdog segment → shots 7–8:** shot 7 is a beat of silence on screen
  (Dale says nothing for a beat; the staged worker goes quiet). The clip's
  catch line ("Ninety seconds after the last progress note... it fires")
  lands on shot 8, when the red STALL alert appears. The clip is not split
  into per-shot files, so the exact second the shot-7/shot-8 boundary falls
  inside the clip is a rehearsal cue, not a measured value — see below.
- **Shot 8 live timing (DEM-012, separate from narration):** the catch must
  land under 90 seconds from the silence cue in demo configuration. That is
  a live watchdog measurement, not a narration length, and is not timed by
  this sheet.

## What is NOT claimed here

- The internal split point of the watchdog clip (where shot 7 ends and
  shot 8 begins inside the 48.1 s / 44.6 s clip) is not separately measured;
  at rehearsal, cue the shot-8 visual to the clip's catch line and record
  the offset, then add it to this sheet.
- No other narration clips exist yet: the fallback full-demo voiceover
  (WDG-033) and the watchdog-moment caption voiceover (DEM-015) are not
  recorded, so they have no timing entries here.
- Listening check on the demo machine speakers/headphones is DEM-018,
  still open; lengths here are file measurements only.
