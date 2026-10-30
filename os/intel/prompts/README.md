# Prompts explainer — DOC-011

How the brief prompts and the dispatch prompt work, what each one
is for, and what has (and has not) changed since v1. Read this
before editing any file in this folder.

## What lives here

| File | Owner task | Job |
| --- | --- | --- |
| `brief_morning.md` | Hana BRF-001 | Morning brief prompt, v1 |
| `brief_morning_v2.md` | Hana BRF-019 | Morning brief prompt, v2 — v1 plus the ask-nick, no-priority-order, and since-your-last-brief rules, tuned from the INT-027 cold-start gaps; v1 kept for diffing |
| `brief_onjoin.md` | Hana BRF-002 | On-join brief prompt, v1 |
| `brief_onjoin_v2.md` | Hana BRF-019 | On-join brief prompt, v2 — v1 plus the name-the-open-job's-lane rule and the never-drop-the-crew-building-sentence rule, tuned from the BRF-018 cold-read gaps; v1 kept for diffing |
| `brief_ondemand.md` | Hana BRF-003 | On-demand brief prompt, v1 |
| `dispatch.md` | Pax DSP-001 | Dispatch draft prompt, v1 (Pax lane, not Hana's) |
| `dispatch_v2.md` | Hana DSP-024 | Dispatch draft prompt, v2 — v1 plus the size rule and the contradiction rule, tuned from the DSP-022/023 eval failures; v1 kept for diffing |

The brief prompts are Hana's. The dispatch prompt is Pax's: this
explainer describes it so a brief reader can tell the two apart.
Hana edits it only for her own dispatch-language tasks. DSP-021
(goal-elicitation microcopy), DSP-022 (golden goals), DSP-023
(adversarial goals), DSP-024 (prompt v2, this file's v2 row
above), DSP-025 (summary style), DSP-026 (spec standard),
DSP-027 (acceptance standard), and DSP-028 (secret-leak guard)
have all landed — see "What is still missing" below for what
a Spark run still owes.

## How a brief prompt works

A brief prompt is instructions to Spark, not code that runs. The
flow is:

1. `intel/brief.py` builds a snapshot from the sources mapped in
   `intel/notes/hana-source-map.md` (digest output, store JSONL,
   jobs list, presence, capabilities).
2. The composer (`compose_spark_brief` / `compose_brief` in
   `intel/brief.py`) hands Spark a prompt built from the
   extractor section data and gets back a brief. Note the gap,
   stated plainly: the composer does NOT currently read the
   prompt files in this folder — it builds its prompt inline
   ("Write a {kind} brief from this section data only. Do not
   invent facts. Keep it under {budget} words. Sections: ...").
   The prompt files are the written spec for what a Spark brief
   must do, but the code path and the files are not wired
   together yet. Wiring them is open work; until then, a change
   to a prompt file does not by itself change what Spark is
   asked, and the inline prompt is the thing actually sent.
3. The brief is checked against its kind budget
   (`BRIEF_BUDGETS` in `intel/brief.py`: morning 220 words,
   on-join 150, on-demand 300), redacted by `redact_secrets`,
   and stored via `intel/store.py`.

If Spark is unavailable, no prompt runs at all. The fallback is
a different path, not a different prompt: `compose_template_brief`
builds the brief from the extractors alone
(`extract_decisions`, `extract_blocked`, `extract_owners`,
`extract_watch_items`) and marks it TEMPLATE in its first line,
so a reader can tell it was never composed by Spark. The prompt
files describe the Spark path only; the template path follows
the same sections, budgets, and rules in code.

## The rules every brief prompt shares

All three brief prompts carry the same hard rules, in the same
order of importance:

1. **Never invent a fact.** Every claim traces to the snapshot.
   A section with nothing to report says so ("Nothing reported
   in this window") instead of guessing.
2. **Blocked reasons are quoted verbatim** from the job record.
   Never paraphrased away.
3. **Names come from the snapshot only.** No job, nick, or id
   that is not in the jobs dump.
4. **Plain English only.** No jargon, no unexplained acronyms.
5. **A word budget that counts everything**, headings included.
   When a draft runs over, the prompt says what to cut first:
   watch items (morning, on-demand) or background (on-join) —
   never a blocked job or a decision.
6. **English prose, always** (BRF-021). Chatter in another
   language is never quoted as brief prose. A job title or
   blocked reason the brief must name is quoted exactly as
   recorded, because translating it would invent wording — the
   verbatim rule wins over translation.
7. **Redaction.** Anything that looks like a token, key, or
   password is replaced with `[redacted]` and the brief goes on.
8. **Window honesty.** The brief states its window in its first
   line. If history was trimmed and the window starts mid-story,
   it says so and names its start point.

## How the three brief prompts differ

### Morning brief — `brief_morning.md` (BRF-001, 220 words)

For a crew member starting work. Five sections, always in this
order: Decisions, In flight, Owners, Blocked and why, Watch
items. It answers: what changed, what is moving, who owns it,
what is stuck. Run daily at 08:00 ET via
`intel.py brief --morning --room <room>` (BRF-011; the run
happens on the day it is invoked, not the next morning).

### On-join brief — `brief_onjoin.md` (BRF-002, 150 words)

For a newcomer who has never been in the room. Four sections:
What this crew is building, Your likely lane, What is blocked,
Who to ask. Two rules exist only here: never assign the
newcomer a job (suggest a likely lane only from their
capability record, otherwise point to who to ask), and never
present someone as available when the snapshot does not show
them online ("not online in this window"). The brief is
offered, not auto-posted: a nick with no prior messages gets
an offer record only (BRF-029), and no brief is generated
until it is invoked.

### On-demand brief — `brief_ondemand.md` (BRF-003, 300 words)

The morning brief's five sections, with the window as a
parameter instead of a fixed value. The requester asks for
"last 2 hours", "since <time>", or "last 500 messages"; the
brief states the window actually used, in the requester's words
plus the exact start and end it resolved to. If the snapshot
covers less than the requested window, the brief says plainly
what is missing and never stretches the window to match the
request. Two briefs from the same room with different windows
must have different `source_window` values and non-identical
text. Run via `intel.py brief --ondemand --room <room>
--since <window>` (BRF-024).

## How the dispatch prompt works

`dispatch.md` (Pax DSP-001, v1) turns one plain-English goal
into a DRAFT plan and nothing else. Its output is one JSON
object: a one-paragraph plain-English summary plus 1 to 12
jobs, each with a key, title, spec (goal, context, files,
steps, out-of-scope), files, deps, max attempts, and at least
one machine-checkable acceptance line. It never posts jobs,
never claims jobs, and never announces anything — posting
happens later, through `intel/dispatch.py`, and only after a
human approves the plan. If it cannot produce a valid plan it
says so in plain English and produces nothing else, rather
than inventing a job, file, dependency, or acceptance check.
The output schema is enforced by the parser (Pax DSP-002,
`mos/acceptance.parse_accept`). Like the brief prompts, it is
consumed through `intel/spark_client.py` `complete()` on the
real Spark transport; the file itself states there is no fake
transport, so a draft not produced by a real Spark call is
not a draft.

## v1 to v2: what has changed, and what has not

**There IS now a v2 of two brief prompts: `brief_morning_v2.md`
and `brief_onjoin_v2.md` (BRF-019, 2026-10-27).** The rule held:
v2 is tuned from eval failures only, never from vibes, and
the v1 files are kept for diffing. The failures arrived after
the rubric passes: the BRF-018 on-join cold-read verdict found
a newcomer could start work but was not told in one sentence
what the crew is building, nor which lane the open job belongs
to; the INT-027 cold-start test found a returner could resume
job-level work but not lane-level planning, with five gaps.
Morning v2 targets three of the INT-027 gaps (ask-nick on the
blocked job, no-priority-order stated, since-your-last-brief
honesty) and on-join v2 targets both BRF-018 gaps
(name-the-open-job's-lane, never-drop-the-crew-building
sentence). The two remaining INT-027 gaps (held decisions,
source pointers) are NOT fixed by v2: no source provides them,
and inventing them would break the never-invent rule. No
re-score is claimed yet: a Spark-composed brief under v2
cannot be scored until real Spark transport lands, and the
BRF-018 and INT-027 re-runs under v2 are still owed — the
same fix-then-rescore rule BRF-017 already follows. The
on-demand prompt (`brief_ondemand.md`) has no v2 yet, because
no eval failure targets it.

**There IS a v2 of the dispatch prompt: `dispatch_v2.md`
(DSP-024).** The dispatch evals did produce failures to tune
from: the DSP-023 A5 huge-scope case had no dedicated guard
until DSP-013 landed, and the A1 contradiction guard is
narrow by design (literal create/delete wording only). v2
changes exactly those two things — a hard never-emit-an-
oversized-plan rule with split-or-refuse, and a never-emit-
a-contradictory-plan rule with refuse-in-plain-English —
and carries everything else over from v1 word for word.
`dispatch.md` stays v1, kept for diffing; the diff is the
v2 header plus those two rules plus the bad-answer examples
that name them.

The one substantive change made to the v1 brief prompts since
they were written is still a v1 edit, not a v2:

- **Rule 6 clarified (BRF-021, 2026-10-26).** The morning
  prompt previously said to "translate the meaning" of
  foreign-language chatter, which contradicted the verbatim
  blocked-reason rule. The wording was replaced, not just
  added to: all brief prose is English, foreign chatter is
  never quoted as brief prose, and a job title or blocked
  reason is quoted exactly as recorded. The same rule 6 now
  appears in all three brief prompts. This scores the template
  brief only; a Spark-composed brief over mixed-language
  chatter cannot be scored until real Spark transport lands.

## What is still missing (stated plainly)

- **The prompt files are now wired to the composer, opt-in
  (BRF-007 follow-up, 2026-10-28).** `intel.brief.load_brief_prompt`
  reads the prompt file for a kind and a version (v1 default,
  v2 where one exists), `compose_brief` /
  `compose_spark_brief` send that text as the client's system
  text when the caller passes it as `system_prompt`, and
  `generate_brief` passes `system_prompt` through to
  `compose_brief`, so the stored-brief path can carry a prompt
  file too — proven by
  tests/test_intel_brief_prompt_wiring.py and
  tests/test_intel_brief_prompt_version.py with recording fake
  clients. The inline section-data prompt, the budget trim, and
  the redaction pass are unchanged, and the default call (no
  system_prompt) sends no system text, exactly as before. A
  v2 request for ondemand returns "" with no silent v1
  fallback, because ondemand has no v2 file. What is still
  open: making the wiring the default, and a CLI flag for it —
  the CLI (`intel.py brief`) still builds briefs with no Spark
  client at all, so a flag alone would change nothing until a
  client is wired into that path. A missing prompt file never
  fails a brief: the loader returns "" and the composer sends
  no system text.
- **Fixture rendering checks are pending.** The brief prompts'
  acceptance checks that need Buffy's fixtures (quiet FND-022,
  busy FND-023, jargon blocklist BRF-037 for rubric check 5)
  cannot run until those fixtures land in this repo. The
  scores logged so far (BRF-016/017/021) are on hand-written
  snapshots, and the eval log says so.
- **No Spark-composed brief has been scored.** The composer
  (BRF-007), budgets, fallback, and redaction are implemented,
  but real Spark transport is a hard blocker, so every scored
  brief so far is a template brief. A prompt change that only
  a Spark-composed brief could prove is unproven until then.
- **Hana's DSP tasks are done except the Spark re-runs.**
  DSP-021 to DSP-028 have all landed, including DSP-024
  (`dispatch_v2.md`). What is still owed is the live proof:
  a real Spark run over a vague goal (DSP-021 microcopy),
  Spark-generated golden plans scored against their shapes
  (DSP-022), and Spark-generated adversarial plans scored
  against their guards (DSP-023) — including a Spark plan
  that must now come back split, not oversized, on a huge
  goal, and refused, not contradictory, on a contradictory
  goal, under the DSP-024 v2 rules. Until transport lands,
  the evals score hand-authored literals only, and a Spark
  plan that falls outside a shape or sails through every
  gate on an adversarial goal counts as a DSP-024 prompt
  failure, not a pass.
- **Announcements are held.** BRF-010 (posting
  `BRIEF:<id>` one-liners to the build room) waits on Dale's
  room/posting decision under GOV-002. Nothing in this folder
  authorizes a post.

## How to change a prompt

1. Edit the prompt file only; do not quietly change
   `intel/brief.py` in the same commit to match it. If the
   code and the prompt disagree, that disagreement is a
   finding, not something to paper over.
2. Update the file's Status block (task id, version, date,
   what check is still pending).
3. Run `python3 -m unittest tests.test_intel_brief` and, for
   any code change, the full suite. A red suite blocks the
   change.
4. If the change is driven by an eval failure, log it in
   `intel/evals/log.md` with the failing check, the change,
   and the re-score — that log entry is what turns a v1 edit
   into a v2 when BRF-019 runs.

## Status

DOC-011 v1, 2026-10-26. No bus post was made for this file.
