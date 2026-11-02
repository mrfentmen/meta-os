# Meta OS shell spec — boot experience for both citizens (H1)

Branch: `hana/os-shell`. Lane: Hana — shell and experience.
Sources: `KERNEL_SPEC.md` (the law), `OS_BUILD_TASKS.md` Hana section,
`OPENCODE_OS_BUILD.md` Section O (OS-205..OS-216).

## Status — read this first

This file is a SPEC ONLY. It contains no kernel code, no framebuffer
code, and no service code. Nothing in this branch boots.

- The only kernel behavior written anywhere is K1: `kernel/src/main.rs`
  on `origin/main` prints `META OS KERNEL - alive (K1)` on COM1
  serial and then spin-halts. That source is WRITTEN, UNCOMPILED,
  and UNPROVEN: no QEMU boot log showing the line has been seen
  from this branch or recorded here.
- Every other behavior in this file is NOT BUILT until a QEMU boot
  log shows it. The format for each behavior lives in
  `shell-formats.md`; the behavior itself does not exist yet.
- What is not real is NOT BUILT, in those words (KERNEL_SPEC.md
  rule 6, NO MOCKS). There are no placeholder screens, no clickable
  fakes, and no fixture data in this branch.

## The two citizens

Meta OS is built for agents AND for users. The shell serves both,
from the same facts, in two forms:

- The USER's console: text on the framebuffer console (from K2),
  written for eyes. Exact lines are defined in `shell-formats.md`.
- The AGENT's structured view: the same facts as one JSON record
  per boot and per status, on the serial port, parseable without
  scraping. Exact fields are defined in `shell-formats.md`.

Rule: the kernel and services emit both forms from the same facts
at the same time. An agent never scrapes the framebuffer and never
parses human console text to learn OS state. If a fact is worth
showing, it is worth emitting in the agent record.

## Why this beats the Linux behavior it refers to

Linux behavior, used here as reference only, prints boot lines
(version, memory, CPU, devices) for humans, and agents learn OS
state by scraping those lines or by running separate tools
(`uname`, `uptime`, `free`, `ps`) and parsing their text. Meta OS
does the same job in one move: the boot facts are emitted once
for eyes and once as a record, from the same source, so the two
can never disagree and nothing needs scraping.

No Linux code is copied or ported anywhere in this branch. No
Linux source tree was read for this spec. The reference is
behavioral only: what a boot shows, and what status answers.

## Boot sequence

Each row states what the user sees, what the agent gets, and the
honest status. NOT BUILT means no boot log proves it.

| # | Stage | User sees (console) | Agent gets (serial) | Status |
|---|-------|---------------------|---------------------|--------|
| 1 | Bootloader hands off to `kernel_main` | Nothing yet | Nothing yet | NOT BUILT |
| 2 | Serial init, COM1 38400 baud 8N1 | Nothing yet | Nothing yet | NOT BUILT |
| 3 | K1 alive line | `META OS KERNEL - alive (K1)` | Same line on serial; agent record format specified, emission NOT BUILT | WRITTEN in `kernel/src/main.rs`, UNCOMPILED, UNPROVEN |
| 4 | K2 framebuffer console | Banner, 4 lines, per `shell-formats.md` | Agent record for the same 4 facts | NOT BUILT |
| 5 | K3 timer + keyboard | Ticks advance; typed input echoes | `ticks` field advances in status | NOT BUILT |
| 6 | Shell prompt | `metaos> ` | Prompt has no agent record; agents use the status record | NOT BUILT |
| 7 | K4 heap | `heap` line in status | `heap` fields in status record | NOT BUILT |
| 8 | K5 tasks + scheduling | `tasks` count in banner and status | `tasks` field in status record | NOT BUILT |
| 9 | K6 first userspace program | First Goose service process noted in status | Service list in status record | NOT BUILT |

## Commands

Today, the real command set is EMPTY. No shell exists yet, so no
command runs. This is the honest empty state, and it is the
pattern the shell keeps: `help` lists ONLY real commands, so
today it would list none (see `shell-formats.md`).

Commands specified for later milestones, all NOT BUILT as running
commands:

- `status`: tasks, ticks, heap — one line each on the console,
  one record on serial (OS-207, OS-208).
- `help`: lists what the shell can do today — only real commands
  (OS-209).
- Bad input handling (OS-211): unknown command, long line, and
  empty line are each handled and logged, never crashing the
  shell. Exact handling strings are in `shell-formats.md`.

## Colors and layout

### clear — ruled 2026-11-02 (H-FP2, closes the RW4-2 gap)

`clear` is a real kernel console command, and this paragraph is
its ruling. Typing `clear` blanks the VGA screen and moves the
cursor to the top-left corner, and it prints no output line of
its own. It touches only the screen: the serial transcript is
left exactly as it was, so nothing already printed is lost from
the record. `help` does not list `clear` yet. The ruled help line
stays exactly `commands: status help uptime mem ps`, and whether
`clear` joins that line awaits a Pax ruling — this paragraph
changes no help text. Source: `kernel/src/sched.rs` (`clear`
branch and `unsafe_console_clear`, RW4-2 interim comment) and
`kernel/src/vga.rs` `clear()`. Note: the Commands section above
predates the built kernel and is not re-ruled here; closing the
rest of that staleness belongs to the build-out spec-close work,
not to this paragraph.

OS-212 (colors and layout pass, screenshot in the logs) is
NOT BUILT. The framebuffer console does not exist yet, so there
is no screenshot to take and no color scheme to claim. This spec
reserves the pass for the K2 console and invents no color codes
for it now: a framebuffer draws glyphs, it is not a serial
terminal, so ANSI color codes are not assumed here.

## What this spec does not do

- No kernel code. Rowan's kernel lane owns `kernel/`.
- No service code. Goose services are a later layer; no Goose
  syntax is invented here (Goose is the boss's own language and
  has no public docs to quote).
- No home surface. See `home-surface.md`: the home surface does
  not exist until real OS state exists to show.
- No program features. Per H5, programs stay warm, not hot, until
  the OS passes K2. This branch adds no program features.
- No cybersecurity program. PARKED by the boss's order. It is not
  started here, and it is named only here, once, as parked.
