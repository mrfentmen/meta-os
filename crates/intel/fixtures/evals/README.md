# Eval methodology - how brief scores were produced (DOC-012)

This note answers one judge question: "how do you know it works?"
Short answer: every brief score in this folder is a hand check of a
real brief against a written manifest. No score is averaged, no score
is guessed, and no score is claimed for a brief that was never
generated.

## The three pieces

1. **Rubric** - [brief_rubric.md](brief_rubric.md) (BRF-015).
   Eight checks, each answered yes or no from the brief text plus
   the fixture manifest only. No check needs a judgement call about
   style. A brief that fails any check is not a good brief, even if
   it reads well.
2. **Log** - [log.md](log.md) (BRF-016, BRF-017, BRF-021).
   Every score lives here as one entry: the brief id, the fixture,
   the per-check yes/no answer, and the manifest fact that proves
   each answer. The brief text scored is quoted in the entry, so a
   reader can re-check it without re-running anything.
3. **Fixtures and manifests** - hand-written snapshots, listed below.
   A manifest is the ground truth for one score: how many messages,
   what markers they carry, how many jobs in each status, who owns
   what, and which alerts exist. If a name, job, or decision is in
   the brief but not in the manifest, check 3 (no invented facts)
   fails. If a blocked job or alert is in the manifest but not in
   the brief, checks 1 or 8 fail.

## How a score is produced, step by step

1. Pick a snapshot and write its manifest down first, before
   looking at any brief text.
2. Generate the brief from that snapshot only. So far every scored
   brief is a template brief: `intel/brief.py`
   `compose_template_brief` (BRF-008, marked TEMPLATE, no language
   model involved). The template path is covered by
   `tests/test_intel_brief.py` `TemplateBriefTest`.
3. Check the brief against the manifest, one rubric check at a
   time. For each check write yes or no, then the manifest fact
   that proves it.
4. Count the words in the brief, headings included, and compare
   against the kind budget (morning 220, on-join 150, on-demand
   300 - constants in `intel/brief.py`, FND-034). That is check 4.
5. Write the entry in [log.md](log.md), with the brief text quoted.
   A score with no log entry does not exist. There is no automated
   rubric scorer in the code yet; every entry so far is a hand
   check, and it says so by quoting its evidence.

## Scores on record so far

- **BRF-016, quiet snapshot, 8/8.** Manifest: 4 messages
  (1 DECISION marker, 3 DONE markers), 3 jobs all done, 4 nicks
  present, 0 blocked jobs, 0 alerts. Brief: 66 words, morning
  budget 220.
- **BRF-017, busy snapshot, 8/8.** Manifest: 4 messages
  (2 DECISION markers, 1 DONE, 1 BLOCKED), 22 jobs (10 claimed,
  6 open, 3 blocked, 3 done), 6 owners, 2 alerts. Brief: 186
  words. Known limit, recorded in the same entry: the same
  22-job shape with 9-word titles instead of 2-word titles ran
  369 words in a trial run, over the 220-word morning budget.
  The template brief has no rewrite pass to compress long
  titles; the Spark composer (BRF-007) is the real fix for
  long-title days, and it is blocked on real Spark transport.
  The scored brief uses realistic 2-word titles, and the
  long-title trial is recorded as a limit, not as a pass.
- **BRF-021, multilingual safety, pass.** Snapshot: one French,
  one Spanish, and one German chatter line, none carrying a
  decision or blocked marker, plus one English decision, one
  claimed job, one blocked job with an English reason, and one
  alert. The template brief contains the English items and none
  of the three foreign chatter lines verbatim. A second case
  with foreign chatter only yields English sections and
  "Nothing reported in this window".

## What these scores do NOT prove

- **Not a Spark-composed brief score.** Real Spark transport is
  the hard blocker (endpoint and key unnamed, fake transport
  rejected). No Spark-composed brief has been produced, so no
  score here is a score for one. When real transport lands, the
  Spark-composed briefs get scored separately, in new log entries.
- **Not a score on Buffy's fixtures.** The quiet, busy, and stall
  fixtures from the Buffy lane (FND-022, FND-023) are not in this
  repo yet. Every fixture above is hand-written, and every log
  entry says so. Re-scores on Buffy's fixtures are still owed
  when they land, and they will be new log entries, not edits
  that rewrite the hand-written scores.
- **Check 5 is provisional.** The rubric's plain-English check
  waits on Buffy's jargon blocklist (BRF-037, not in this repo).
  Until it lands, check 5 uses the plain test written in the
  rubric: no acronym without an explanation in the same sentence,
  and no sentence that needs a technical dictionary. The rubric
  states this so a scorer never has to guess.
- **Brief ids in the early entries are log-only.** The BRF-016
  and BRF-017 entries were written before brief storage landed
  (BRF-009). Their ids identify the scored text in the log, not
  a stored brief. Stored briefs are now retrievable through
  `intel.py brief --list` / `brief --show`.

## How to re-check a score

1. Read the log entry. It quotes the brief and states the
   manifest.
2. Read [brief_rubric.md](brief_rubric.md) and apply the eight
   checks to that brief and that manifest.
3. If any check disagrees with the log, the log is wrong, not
   the method - file the disagreement as a new log entry that
   names the check and the manifest fact, the same way the
   BRF-017 entry records its budget limit.

## Status

DOC-012, 2026-10-26, Hana lane. No bus post was made for this
file. No score in this folder was produced by a language model,
and no fixture manifest here was invented after the brief was
written.
