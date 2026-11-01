# OS home surface — status: NOT BUILT (H3, REPLACED)

Branch: `hana/os-shell`. This file REPLACES the old H3 (build a
home surface) per the boss's no-mocks order, now KERNEL_SPEC.md
rule 6 and a hard rule in `OPENCODE_OS_BUILD.md`.

## Status

NOT BUILT. The OS home surface does not exist.

- No file in this branch builds it. No screen, no UI, no
  clickable fake, no placeholder screen is shipped here.
- The existing program surfaces in this repo (the Trio app and
  its consoles) are PROGRAMS, not the OS home surface. Do not
  confuse them: a program surface running on a development
  machine is not OS state.

## The rule

The OS home surface gets built ONLY when it reads real OS
state. Until real state exists to show, the surface does not
exist. When it is built, every value on it traces to a real
source. No mock, no fixture data in a shipped surface, no stub
presented as working.

What is not real is NOT BUILT, in those words.

## Real-state sources required first

Each source must exist and be proven by a boot log before the
surface may show its values. All four are NOT BUILT today.

| Value the surface will show | Real source | Source status |
|-----------------------------|-------------|---------------|
| Banner: milestone, memory | Kernel boot facts, K2 console | NOT BUILT |
| Task list and count | Scheduler task list, K5 | NOT BUILT |
| Heap used and total | Kernel allocator, K4 | NOT BUILT |
| Service list | Goose service supervisor, K6 | NOT BUILT |

Until all four sources exist, there is no home surface to
check, screenshot, or demo. A demo of a fake surface would
violate the no-mocks rule, so no demo is offered.

## Honest empty state

The honest empty state for the home surface is words, not a
screen: this file, stating NOT BUILT and naming the sources
still missing. That is the pattern the shell keeps everywhere
else in this lane: `help` lists only real commands (today:
none), the banner omits unmeasured lines, the agent record
uses `null` for unmeasured fields. Words that say what is
missing beat a screen that pretends otherwise, every time.

## When it is built (future, not this branch)

When the four sources exist, the surface is built with one
trace per value: banner lines from the kernel boot facts,
task rows from the scheduler list, heap figures from the
allocator, service rows from the supervisor. Any value that
cannot trace to one of those sources is left out, not filled
in. That build is a later task, after K2 at the earliest,
and it is NOT BUILT here.
