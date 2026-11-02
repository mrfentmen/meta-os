# Build-001 vs build-002 comparison (OC2B-391–395)

## What the pipeline did identically

- Same chain: rough words -> 2a brief (run_rough_words) -> 2b note
  (search_repo + checked shelf) -> 2c pack (export_pack) ->
  bounds check (check_pack) -> memory outcome -> independent
  re-read check. No step differed in kind.
- Both proved: no stalls, no unproven exits, every pack check ok,
  every independent re-read check ok.
- Both renders of record are honest: 001 carries a GENERATED concept
  render with receipt; 002 carries explicitly no render.
- Neither build touched the faber loop (it does not exist in this
  tree — verbatim gap in each build's faber.md).

## What differed

| axis | build-001 | build-002 |
|---|---|---|
| words | chunky little heatsink, toasty router board, no fan, keep small (no numbers) | hot garage power supply, fan fine, cheap (different object) |
| airflow | passive (unstated -> natural convection) | forced (stated -> grades at h=25) |
| rounds | 4 | 2 |
| final R | 1.7210 C/W | 1.0623 C/W |
| params | H=39.06 t=1.50 N=15 base=4.00 | H=25.00 t=1.50 N=15 base=4.00 |
| render | render-GENERATED.webp + receipt (1 image attempt) | none (budget kept: 1 attempt total) |
| memory seq | 4 | 5 |

The fan does the work: build-002 proves in 2 rounds at R=1.06 with a
shorter sink, where the passive build-001 needs 4 rounds to reach
R=1.72.

## Per-stage timings, build-002 (OC2B-394)

Wall time on Del's Mac, offline code only (image excluded — 002 made
no image call):

    2a (intake + iterate): 0.0006 s
    2b (repo grep + note): 0.0029 s
    2c (pack emit):         0.0000 s

(Build-001 for reference: 2a 0.0010 s, 2b 0.0052 s, 2c 0.0000 s.
Raw numbers in build-timings.json.)

## Failure honesty (OC2B-395)

- build-001: one stage fell back — faber loop absent, verbatim gap
  recorded in faber.md; render succeeded on attempt 1 of max 2.
- build-002: no fallbacks, no refusals, no skips; render
  deliberately not attempted (budget held at 1 attempt total).
- No stage in either build refused or was skipped silently.

## Memory: oldest first, nothing dropped (OC2B-392)

    seq=1 proven=True R=1.7210 :: toasty little board (brief-a)
    seq=2 proven=True R=1.7210 :: mounting bracket (brief-b)
    seq=3 proven=True R=1.8915 :: cramped enclosure, H<=25 (brief-c)
    seq=4 proven=True R=1.7210 :: build-001 (router board, no numbers)
    seq=5 proven=True R=1.0623 :: build-002 (garage PSU, fan)

Store: labs/officina/workshop-memory.jsonl — 5 entries, seq 1..5
contiguous, oldest present.

## Scripted no-OOB check over ALL packs (OC2B-398)

Ran check_pack over every *pack.json under labs/officina from a
script (read_pack + check_pack, no repo state):

    brief-a-pack.json: ok=True violations=[]
    brief-b-pack.json: ok=True violations=[]
    brief-c-pack.json: ok=True violations=[]
    build-001/pack.json: ok=True violations=[]
    build-002/pack.json: ok=True violations=[]
    ALL PACKS IN BOUNDS: True

## GENERATED filename list (OC2B-399)

Every image under labs/officina (find for png/webp/jpg):

    labs/officina/builds/build-001/render-GENERATED.webp — carries GENERATED

Images without GENERATED in the filename: none.
