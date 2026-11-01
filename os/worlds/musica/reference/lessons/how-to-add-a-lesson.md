# How to add a lesson

[source: written note. This is the improve-over-time loop.]

## The loop

1. Run a session (brief + seeds + takes, logged as usual).
2. Run the keeper pass and the audits.
3. Measure the session: takes, keepers, rejects by reason,
   params used, Spark assist status per take.
4. Append the measured result to `keeper-history.md` (update
   the totals and the by-session / by-params tables) and, if
   the session teaches something general, add a short lesson
   note in this folder.
5. Commit the corpus change with the session's work. A lesson
   that is not committed is not reference — it is a draft.

## Rules for new lessons

- Measured only. Every number comes from a take log, a keeper
  pass, or an audit run. Never invent, round up, or carry a
  number from a different session.
- Source-labelled. Every note names its source: a session id,
  a take-log path, or the pack file it was read from.
- Dated. Every addition carries the date it was measured.
- Small samples stay small. A 4-take session proves a brief
  renders; it does not prove a rate. Say so in the note.
- No copyrighted material. Theory, params, and measured
  results only — never lyrics, never a transcribed melody from
  a real song.
- If a lesson contradicts an older lesson, keep both and date
  the contradiction. Do not silently rewrite history.

## Lesson template

```markdown
# <short title>

[source: session <id>, take log <path>, measured <date>.]

## What happened

<2-4 sentences: params, takes, keepers, rejects by reason.>

## What it teaches

<1-3 sentences: what to do differently next time, or what to
keep doing.>

## Caveats

<sample size, single-session limits, anything that would make
this lesson wrong if quoted without it.>
```
