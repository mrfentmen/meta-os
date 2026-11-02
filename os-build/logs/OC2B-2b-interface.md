# OC2B-327 — 2b interface note (what a brief contains, what a prior-art note returns)

## What a 2a brief contains (os/worlds/officina/runtime/brief.py)

`parse_rough_words(text)` returns a plain JSON-ready dict:

- artefact_class: "heatsink-fin-geometry" or None (ungradeable)
- gradeable: bool
- source_text / summary: the raw and cleaned rough words
- requirements: [{kind, value, source}] — only what the words state
  (footprint_mm, power_w, passive_cooling / forced_airflow,
  fin_height_mm_max)
- targets: [{kind, value, source}] — target_r_c_per_w, stated or the
  labelled workshop-default
- preferences: [{kind, value, source, note}] — compact, low_cost
  (explicitly not graded)
- unknowns: slots the words never stated (power_w, footprint_mm,
  target_r, airflow) — gaps, never inventions
- conflicts: e.g. a stated footprint != the class 50 mm footprint
- parameters: the workshop first guess the loop moves
  (fin_height_mm, fin_thickness_mm, fin_count, base_thickness_mm)
- bounds: stated caps only (fin_height_mm_max)
- amendments / decision_log: one entry per round with rule, decision,
  reason, and the grade that motivated it

`run_rough_words(text)` returns the run record: rough_input, brief,
rounds_used, final_params, final_grade, verification, proven, status.

## What a 2b prior-art note returns (os/worlds/officina/runtime/prior_art.py)

`build_prior_art_note(record_or_brief, extra_sources=None)` returns a dict:

- stage: "2b-prior-art", artefact_class, brief_summary
- key_features: short strings derived from the brief in code only
- repo_context: [{path, what}] — heatsink.py (live bounds),
  design_loop.py (held-out gate), PACK.md (honesty record), plus
  grep hits from search_repo
- public_context: [{topic, title, url, kind, status, finding}] —
  title+URL per entry, kind primary|secondary, status alive|dead|
  unverified from the 2026-11-02 re-fetch
- claims: [{claim, sources}] — every claim names its sources
- sources: the full mandatory list (schema rejects zero sources)
- differences, shelf_limits, disclaimer, provenance, generated_utc

`validate_note` raises ValueError on zero/missing sources or any
sourceless claim. `search_repo` greps the officina tree on the
brief's own keywords (max 2 hits/file, 20 total). `search_web`
returns the checked shelf (URLs+titles) or raises cleanly offline.
`brief_to_note(rough_words)` wires 2a->2b: run_rough_words, then
search_repo, then build_prior_art_note.
