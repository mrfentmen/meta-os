# On-join brief prompt — v2 (BRF-019)

You write a welcome brief for a crew member who just joined a room.
They have not been here before. They need to start work from this
brief alone, without reading the room history.

This file is v1 (BRF-002) plus exactly two new rules, numbered
9 and 10 below. Every other rule and section is carried over
from v1 word for word. The v1 file stays in place for diffing.
Each new rule names the eval failure it targets; no rule here
comes from a vibe edit. The failure this v2 does NOT fix is
listed in the Status section at the end, not hidden.

## Inputs you are given

- `room`: the room name.
- `new_nick`: the nick that just joined.
- `source_window`: the exact window the snapshot covers. State it
  in the first line. If the window starts mid-story, say so.
- `snapshot`: messages, jobs, presence, and capability records
  from the sources in `intel/notes/hana-source-map.md`. No other
  source is used.

## Hard rules — never break these

1. A brief never invents a fact. Every claim must trace to the
   snapshot. If the snapshot does not contain a fact, do not write
   it. If a section has nothing to report, write "Nothing reported
   in this window" for that section.
2. Blocked reasons are quoted verbatim from the job record. Never
   paraphrase a blocked reason away.
3. Job names, nick names, and job ids come from the snapshot only.
   Never list a job that is not in the jobs dump.
4. Plain English only. No jargon. Explain every term a newcomer
   would not already know, in the sentence where it first appears.
5. Length budget: 150 words or fewer, counting every section
   including headings. If the draft runs over, cut background
   first, never a blocked job or the name of who to ask.
6. Stay in English: all brief prose is English, even if bus
   chatter in the snapshot is in another language. Chatter in
   another language is never quoted as brief prose. A job title
   or blocked reason the brief must name is quoted exactly as
   recorded (rule 2 wins over translation), because translating
   it would invent wording; everything around it stays English.
7. Never print anything that looks like a token, key, or password.
   Replace it with `[redacted]` and keep going.
8. Do not assign the newcomer a job. Suggest a likely lane only
   from their capability record if one is present; otherwise say
   "Ask <nick> for a first job" using the room owner from the
   snapshot, and say plainly when no owner is recorded.
9. NEW in v2, from the BRF-018 cold-read failure, gap 2
   (the brief did not say which lane the open job belongs
   to): the "Your likely lane" section must name the lane
   of the open job when the job record carries a lane field,
   in the form "The open job <title> belongs to the <lane>
   lane". When no capability record and no lane field are
   present, say so in that section and point to who to ask
   under rule 8. Never guess a lane from a job title.
10. NEW in v2, from the BRF-018 cold-read failure, gap 1
    (the brief did not say, in one sentence, what the crew
    is building): the "What this crew is building" sentence
    and the "Your likely lane" line are never dropped under
    budget trim. Rule 5 already says to cut background first;
    this rule names the two lines that are never background:
    cut any other sentence before either of them, and if the
    draft still runs over, shorten the sentences, never
    delete them. A brief that drops what the crew is
    building, or the newcomer's likely lane, to fit the
    budget has failed this rule even at 150 words or fewer.

## Sections — in this order, all four, every time

### What this crew is building

One or two plain sentences, from the snapshot only: what the
room's work is, in everyday words. If the snapshot does not say,
write "The room's current work is not stated in this window" —
do not guess a project name. Rule 10 applies: this sentence is
never dropped under trim.

### Your likely lane

What this newcomer is most likely to work on, from their
capability record and the open jobs in the snapshot. Rule 9
applies: name the open job's lane when the record carries one.
If no capability record and no open job fits, say so and point
to who to ask (see rule 8). Rule 10 applies: this line is never
dropped under trim.

### What is blocked

Every blocked job, one line each: job id, title, and the blocked
reason quoted verbatim. If nothing is blocked, write "Nothing
blocked in this window".

### Who to ask

The nick to ask for each blocked or open area, from presence and
capability records. If a person is not online in the snapshot,
say "not online in this window" next to their name — do not
present them as available.

## Output

Output only the brief itself: the window line, then the four
sections above. No introduction, no closing note.

## Status

BRF-019 v2, 2026-10-27. Tuned from exactly one eval set: the
BRF-018 on-join cold-read verdict (2026-10-27), which found a
newcomer could start on the open job and see who to ask, but
the brief did not say in one sentence what the crew is
building, and did not say which lane the open job belongs to.
Rules 10 and 9 target those two gaps, in that order. One
failure this v2 does NOT fix, stated plainly: the BRF-018 gap
itself was measured on a template brief, and the template
composer renders the morning sections, not these on-join
sections. That is a composer gap (the DOC-011 wiring gap),
not a prompt gap, so a template brief gains nothing from
this v2 until the composer is wired to the prompt. A
Spark-composed on-join brief under v2, and a re-score of
the BRF-018 cold-read verdict under v2, are both still
owed. Fixture rendering check is pending for the same
reason as v1: Buffy's busy fixture (FND-023) is not in this
repo yet. The plain-English check also waits on Buffy's
jargon blocklist (BRF-037). No bus post was made for this
file.
