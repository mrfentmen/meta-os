# SHOOT — Demo footage assignment for Buffy

**Boss order, 2026-11-04 (Del, via Pax).** Hackathon submission deadline is
TODAY, Wed Nov 4, 9:00 PM ET. This footage is the critical path. Shoot it now.

## Your job

Boot Meta OS (the home boot that works) and screen-record the REAL OS,
shot by shot, from the list below. Raw clips only — Pax does the edit,
captions, narration, and cards. Real OS only: no fake UI, no mock screens,
no staged substitutes for a screen that exists.

Full script for context: `os-build/` demo script (DEMO_SCRIPT, goal files) —
the shot list below is everything the edit needs.

## Specs

- 1080p if you can, 720p minimum.
- ONE separate clip per shot, named: `shot1_boot`, `shot2_shell`,
  `shot3_dock`, `shot4_imperium`, `shot5_science`, `shot6_officina`,
  `shot7_fastpass`, `shot8_desktop` (mp4/mov, whatever the recorder gives).
- Move the mouse SLOWLY. Pause 2 seconds at the start and end of each clip.
- NOTHING secret on screen: no API keys, no tokens, no personal data, no
  terminal history with credentials. Check every frame before you record.

## Shot list

1. **Boot** — full screen, no cuts, from power-on to the desktop. Let it run.
2. **Shell** — open the shell window. Run the userspace programs
   (hello, sleeper, crasher, readkey, demand). Run crasher: the fault must
   isolate to the one task and the system stays up. Show the shell reporting
   the machine's real state.
3. **Desktop + dock** — desktop wide, then a slow pass across the dock so
   all 16 icons read clearly: Terminal, Dashboard, Files, Notes, Calendar,
   Calculator, Board, Imperium, Musica, Science, Officina, Aegis, Nervus,
   Settings, Trash, About. Open Files and Notes for two seconds each.
4. **Imperium** — open Imperium, show the three services (Vigiles, Ignis,
   Medicus). Run the staged eval-frame flow from the repo's eval pack:
   patrol flags the frame, SAM draws its boxes, Wonder's review lands, then
   the dispatch receipt card. Hold the receipt close-up for a full 3
   seconds. Staged eval frames ONLY. The dispatch screen must read
   SIMULATED. Medicus screens: scene awareness only, no diagnosis text.
5. **Science Lab** — open Science. Show the screening funnel
   (1,128 screened, 46 pass all filters) and the candidate list.
6. **Officina** — type a plain-words brief, let the design land, show the
   rendered blueprint.
7. **Fast pass** — about 5 seconds each: Musica playing, Aegis, the Nervus
   map, Board with messages moving, the agent list at login (29 agents).
8. **Desktop wide** — hold 5 seconds. Closing shot.

## Delivery

- Push the raw clips to branch **`buffy/demo-footage`** in this repo,
  one commit per shot is fine.
- If any clip is over ~90 MB (the API blob limit), split it into two
  shorter clips or report on room 1 exactly what is blocking.
- When done, post to **room 1**: branch name, the clip list, total size,
  and anything that failed or is missing. Do not silently skip a shot —
  report it.

Pax picks the footage up from the branch and edits. Questions go to Pax
on room 1.
