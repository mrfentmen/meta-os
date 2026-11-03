# OC2B-367 / 368 — 2d read-back dump + corruption drill

## Read-back drill (OC2B-367)

Fresh-brief context = `recall_for_brief(labs/officina/workshop-memory.jsonl)`:

    total_entries: 3
    oldest_seq: 1
    window (oldest first, limit 5): seq 1, 2, 3

Dump of what the next brief receives (one line per entry):

    seq=1 kind=brief-outcome proven=True final_R=1.7210
      words: "a heatsink for a toasty little board, about 50mm square, no fan, keep it compact, under 2 degrees per watt"
    seq=2 kind=brief-outcome proven=True final_R=1.7210
      words: "a mounting bracket to hold a 50mm square heatsink for a hot little board, no fan, ..."
    seq=3 kind=brief-outcome proven=True final_R=1.8915
      words: "a heatsink for a cramped enclosure, no taller than 25mm, about 50mm square, no fan, ..."

Memory record file: labs/officina/workshop-memory.jsonl (3 entries).
Format documented in the memory module docstring: one JSON object
per line {seq, timestamp_utc, entry}, append-only, no delete/clear API.

## Corruption drill (OC2B-368)

Truncated the memory file mid-entry in a scratch copy (/tmp, never
the repo): appended '{"seq": 999, "broken": ' as a 4th line.

Reader behaviour: FAILS CLEAN with the line number —

    ValueError: workshop memory line 4 is corrupt: Expecting value:
    line 1 column 23 (char 22)

It does not skip the partial entry, does not return partial data,
and does not touch the store. Recorded: fail-clean with line number.
