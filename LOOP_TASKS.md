# LOOP_TASKS.md — task queue for the metaos-loop self-development loop

The loop (`bin/metaos-loop`, see `os/os/METAOS_LOOP.md`)
takes its work from this file, one task per cycle.

## Format

A task is one line that starts with `- [ ] ` followed by one sentence of
plain text telling the agent what to do:

```
- [ ] Fix the typo in the README heading.
```

Rules:

- The loop always takes the FIRST `- [ ] ` line in the file. That is the
  whole scheduling policy: top of file goes first.
- A task must fit on one line. No multi-line tasks, no code blocks.
- When a cycle succeeds (agent run + test gate green + commit), the loop
  itself rewrites that line to `- [x] ...` in the same commit. A human
  closing a task by hand should do the same.
- A failed cycle leaves the line open and appends the reason to the loop
  log. If a task keeps failing, a human moves it down the file or deletes
  it — the loop never skips a task on its own.
- Anything else in this file (headings, prose, HTML comments like the one
  below) is ignored by the loop.

## Current queue

<!-- Example only, the loop ignores lines inside comments:
- [ ] Example task: rename the widget to sprocket in docs/intro.md.
-->
