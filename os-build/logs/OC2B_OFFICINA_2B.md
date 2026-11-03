# Officina stage 2b record — prior-art (OC2B-344)

## What it does

Turns a 2a brief (or run record) into a prior-art note: repo grep
over the officina tree on the brief's own keywords plus a
build-time-checked public shelf (titles + URLs + primary/secondary
kind + alive/dead status). Every claim names its sources; the schema
rejects sourceless notes. Wired as `brief_to_note`: 2a runs first,
unchanged, then the repo search, then the note.

Runs: brief-a (heatsink-fin), brief-b (mount bracket for the sink),
brief-c (fin-array under a 25 mm cap) — all proven, all notes saved
under labs/officina/builds/, all source lists dedup-clean, all
timings under 0.01 s, offline drill refuses clean.

## What it never claims

- No novelty or protectability conclusion, ever. The writer strips
  the forbidden phrase instead of emitting it (pinned by test).
- No patent-database search was performed; the shelf says so.
- The dead ATS link is marked dead, not quoted.
- A note is a research aid, not a clearance: a human decides.

## Registry/README proposals (OC2B-345 — FOR PARENT: lift into status file §14, do NOT edit agents/registry.json here)

- PROPOSE agents/registry.json: workshop-herald capability
  "+prior-art-note (2b, descriptive only)" — no new agent, no new
  role, additive line only.
- PROPOSE os/worlds/officina/PACK.md: parts list gains
  runtime/prior_art.py with the one-line honesty note
  "descriptive aid; states no opinions".
- PROPOSE os/worlds/README.md: officina row gains "(2b notes: repo
  + checked shelf, no legal opinions)".
