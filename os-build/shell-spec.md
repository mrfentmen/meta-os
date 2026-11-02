# Meta OS shell spec — complete (Round 4 HN4-1)

Branch: `hana/os-shell`. Lane: Hana — shell and experience.
Round 4 task: HN4-1 (shell-spec.md complete, H-1 to H-4).
Milo gates, Pax merges. This spec is a SPEC ONLY: it contains
no kernel code. Rowan's kernel lane owns `kernel/`.

Status words in this file mean exactly what Round 4 says:
VERIFIED (seen in a named boot log or read in kernel source
on main), CODE-INSPECTED (read in kernel source on main, no
boot log cited), UNIMPLEMENTED (specified here, no kernel
code on main). No other status words are used.

## The claim this spec serves

The adopted claim sentence for the report and the demo, as
posted by Pax on bus room 1:

> Meta OS boots on x86_64 in QEMU, drops to ring 3, runs
> three userspace programs, isolates a fault to one task,
> and gives a shell that reports real state — reproduced
> from a clean checkout by one command, backed by a
> committed boot log.

Evidence named: `os-build/logs/K6-repro-main-2026-11-01.txt`
(the K6 repro on main, typed over the QEMU HMP monitor
with `sendkey`, i.e. the real PS/2 path) and
`os-build/logs/K6-boot.txt`. Every VERIFIED line below
is either in that repro log or in kernel source on main
(`kernel/src/sched.rs`, `kernel/src/main.rs`,
`kernel/src/user.rs`). Nothing here is copied from the
old H1/H2 spec era without re-checking it: several H1/H2
strings turned out to be wrong against the built kernel,
and the drift table at the end names each one.

## The two citizens

Meta OS is built for agents AND for users, and the shell
serves both from the same facts:

- The USER's console: text on the console, written for
  eyes. The exact lines are the frozen strings below.
- The AGENT's structured view: the same facts in a
  parseable form. Today that form is the STATUS line
  shape below (serial gets the same text as the
  console); the JSON record form is specified in
  `shell-formats.md` and UNIMPLEMENTED as an emitted
  record, per the agent-record row below.

An agent never needs to scrape the console to learn OS
state: the STATUS line carries tasks, ticks, and heap
free directly.

Honesty note on status words: this spec uses the Round
4 words VERIFIED / CODE-INSPECTED / UNIMPLEMENTED
(with evidence named) as its operative labels. In the
old H1/H2 spec's words, anything marked UNIMPLEMENTED
here was NOT BUILT as a running behaviour, and this
branch ships no kernel source of its own, so there is
nothing in this branch that stands UNCOMPILED: the
kernel code cited here lives on main and is proven
only by the logs named above.

## Frozen strings

These are the exact strings. Rowan copies strings, not
intentions: where the kernel still prints something else,
the row says so and names the owner of the fix.

### Boot lines

| String | Status | Evidence / note |
|---|---|---|
| `META OS 0.1 (K6)` | UNIMPLEMENTED in kernel as printed | Frozen banner target: milestone names the last PROVEN milestone (K6). Pax confirmed K6, not K7, on bus room 1. |
| `META OS - milestone K3` | VERIFIED as currently printed | `kernel/src/main.rs:118` on main; the K6 repro log prints this line. DRIFT: Rowan R-1 owns changing it to the frozen banner above. |
| `META OS KERNEL - alive (K1)` | VERIFIED | `kernel/src/main.rs:119`; present in both K6 logs. The alive line keeps its K1 wording: it names the first milestone, not the current one. |
| `mem summary: K4 up` | VERIFIED | Present in both K6 logs, after the memory map and heap checks. |
| `mem region <n>: 0x<start>-0x<end> <reserved\|usable>` and `mem map: <n> regions, usable <k>K reserved <k>K other 0K` | VERIFIED as shape | Counts and addresses vary by machine (the two K6 logs differ); the shape is frozen, the numbers are live, never literal. |

### Prompt

| String | Status | Evidence / note |
|---|---|---|
| (no prompt string) | VERIFIED | `kernel/src/sched.rs` `console_task` prints no prompt before reading input, and the K6 repro log contains zero occurrences of a prompt string. The console accepts typing immediately after boot output. The old H2 prompt `metaos> ` was spec-only, never emitted, and is SUPERSEDED. Do not print it as if it exists. A future prompt string, if one is wanted, is a new Pax ruling, not something this spec invents. |

### Status command

Typed: `status`. Output is exactly two lines, in this order
(CODE-INSPECTED in `run_command`, VERIFIED in the repro
log with live values `tasks 7 ticks 805 heap_free 31K`):

```
tasks <count> ticks <ticks> heap_free <kb>K
STATUS tasks=<count> ticks=<ticks> heap_free_kb=<kb>
```

- The first line prints in LightCyan on Black, then the
  console returns to LightGray on Black (CODE-INSPECTED).
  Serial gets the same text as the console.
- The numbers are live: tasks is the live task-slot count,
  ticks is the live timer count, heap_free is free heap
  in KiB. A gate greps the two-line shape, never the
  example numbers.
- The old H2 status shape (`tasks <count>` /
  `ticks <count>` / `heap <used>/<total> KiB` on
  separate lines) is SUPERSEDED: the kernel does not
  print it.

### Help command

Typed: `help`. Output is exactly one line (VERIFIED in
the repro log):

```
commands: status help uptime mem ps
```

`help` lists the ruled command set (Pax bus idx 494/497:
implemented-and-gate-green wins over the frozen line;
RW4-2 updates the frozen line to match, nothing stripped).
`clear` is implemented (RW4-2 interim, kernel-derived)
but NOT listed here yet: whether it joins the help line
awaits a Pax/Hana ruling.

### Clear command (RW4-2 interim, kernel-derived — spec text still owed)

Typed: `clear`. Effect: the VGA screen is blanked and the
cursor returns to 0,0; no output line is printed. This is
the kernel's own vga.rs clear(), not a spec string: Hana's
spec text for clear is still owed (Pax bus idx 503), and
when she supplies it RW4-2 follows hers. The serial
transcript is untouched. `help` does not list `clear` yet
— the ruled help line stays `commands: status help uptime mem ps` until Pax/Hana
rule that clear joins it.

### Bad input

| Input | Output | Status |
|---|---|---|
| Unknown word | `unknown command` on one line, then `commands: status help uptime mem ps` on the next | VERIFIED from source (`run_command` else-branch). The old H2 form `unknown command: <first-token>` is SUPERSEDED: the kernel does not echo the token. |
| Empty line (Enter with nothing typed) | No output, not an error | VERIFIED from source. |
| Line longer than 80 bytes | `line too long, truncated to 80` printed first, then the command runs on the first 80 bytes | CODE-INSPECTED (`console_task` 80-byte buffer; `run_command` prints the warning before dispatch). The old H2 limit of 256 and wording "ignored" are SUPERSEDED. |

### Prompt behaviour: before, during, after

- BEFORE: no prompt is printed. Boot output ends with
  task output and uptime lines; the console is already
  accepting keys. Nothing announces "ready".
- DURING: each accepted key echoes immediately as typed.
  There is no erase branch in `console_task`: only a
  newline branch and an append branch exist, so a mistyped
  line cannot be deleted in the current console
  (CODE-INSPECTED). Shift is not handled in the scancode
  table: only the lowercase/digit set decodes, a stated
  limit carried from the K3 console. Once per 100 ticks
  the console task prints `uptime <sec>s ticks <ticks>`,
  even in the middle of a typed line: in the repro log
  uptime lines land between keystrokes. A demo reader
  must expect that interleave; it is not an error.
- AFTER: Enter prints a newline, the command runs, its
  output prints, and the loop resumes with no prompt.
  The shell never crashes on bad input: unknown, long,
  and empty lines are each handled and the loop continues.

### Debug lines present in the current build

The K6 repro log shows, per key press and release:

```
INT keyboard scancode 0x<hex>
```

These are the kernel's own debug prints, left in
deliberately in that log (its header names them work
item R-3). They are part of what a reader of today's
logs sees, and they are NOT part of the clean shell
surface: a future log after R-3 lands will not have
them. This spec records them as present, not as desired.

### Userspace and fault lines (from the repro log)

These are program/kernel lines a demo reader sees around
the shell, VERIFIED in the K6 repro log. Pids, addresses,
and byte counts vary; the shapes are frozen:

```
HELLO FROM USERSPACE
user exit code 0
sleeper: before sleep
sleeper: pid <n>
crasher: about to read zero
INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed
user bad syscall 99 refused
sleeper: bad call refused
```

The fault line is the isolation clause of the claim
made visible: the faulting task is killed, the other
tasks keep running (`sleeper: yielded and back`,
`C awake` follow it in the log).

### Agent record

The H2 JSON record (`record`, `os`, `milestone`,
`kernel_version`, `memory_kib`, `tasks`, `ticks`,
`heap_used_kib`, `heap_total_kib`, `status`) is
UNIMPLEMENTED as an emitted record: the kernel's serial
output is the same text as the console, not JSON
(CODE-INSPECTED: the status code comment says serial
gets the same text). Agents today read the STATUS line
shape above. The JSON record stays a specified format
in `shell-formats.md`, not a running behaviour, until
a kernel change emits it and a log proves it.

## Command surface

The 8-command surface named in H-2 is updated here by
RW4-2 to the kernel actually on main: 5 running commands
plus `clear` as a kernel-derived interim, 2 slots still
UNIMPLEMENTED. Every output below is VERIFIED from the
kernel source on main (`run_command` in sched.rs), except
`clear`, which is flagged interim rather than spec.

| # | Command | Output | Status |
|---|---|---|---|
| 1 | `status` | Two lines, see above | VERIFIED |
| 2 | `help` | `commands: status help uptime mem ps` | VERIFIED (Pax ruling: ruled line, nothing stripped) |
| 3 | `uptime` | `uptime <sec>s ticks <ticks>` | VERIFIED |
| 4 | `mem` | `mem frames_free <n> frames_total <n> heap_free <n>K heap_total <n>K` | VERIFIED |
| 5 | `ps` | One `ps id <n> state <state> ticks_used <n> prio <n>` line per spawned task slot | VERIFIED |
| 6 | `clear` | Screen cleared, no output line | KERNEL-DERIVED INTERIM (RW4-2, Pax bus idx 503): runs vga.rs clear(); Hana spec text still owed; NOT listed by `help` yet, pending a Pax/Hana ruling |
| 7–8 | (unnamed) | (none) | UNIMPLEMENTED — no name, no output on record. Pax names them or reduces the surface; Rowan implements only what is named here or by a later Pax ruling. |

`help` lists the ruled set `commands: status help uptime mem ps` and nothing
longer until Pax/Hana rule on `clear` joining it.

RW4-2 note: sections above that still describe the
pre-RW4-1 console (periodic uptime prints, per-key
scancode debug lines, no shift/backspace) are stale
relative to the merged RW4-1 kernel and are NOT silently
rewritten here — they await Hana acceptance / a Pax
ruling, like the formats + test pins named in the drift
table.

## Acceptance script: the claim-sentence demo, line for line

This is the script Rowan and OpenCode build against
(`os-build/tools/drive.py` types each line, then Enter,
over HMP `sendkey`). Expected output is given as
shapes; live numbers vary and are never matched
literally except where the line is a fixed string.

1. Boot. Expect, in order: SeaBIOS lines, `Booting
   from Hard Disk...`, then:
   - `META OS - milestone K3` (current kernel; becomes
     `META OS 0.1 (K6)` when Rowan R-1 lands — the
     script accepts the frozen banner once it lands and
     the K3 line until then, and the difference is
     recorded, not hidden)
   - `META OS KERNEL - alive (K1)`
   - memory region lines, `mem map:` shape line,
     `mem summary: K4 up`
2. Tasks run. Expect the demo task letters and:
   - `HELLO FROM USERSPACE`
   - `user exit code 0`
   - `sleeper: before sleep`
   - `crasher: about to read zero`
   - `INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed`
   - later `sleeper: yielded and back` and `C awake`
     (the fault isolated to one task; the rest continue)
3. Type `help`, Enter. Expect exactly:
   - `commands: status help uptime mem ps`
4. Type `status`, Enter. Expect exactly, in order:
   - `tasks <count> ticks <ticks> heap_free <kb>K`
   - `STATUS tasks=<count> ticks=<ticks> heap_free_kb=<kb>`
5. Type an unknown word, Enter. Expect exactly:
   - `unknown command`
   - `commands: status help uptime mem ps`
6. Type Enter on an empty line. Expect no output.
7. Uptime lines (`uptime <sec>s ticks <ticks>`) may
   appear between any two steps above. They are
   expected, not failures. Keyboard debug lines
   (`INT keyboard scancode ...`) may appear around
   typed input until R-3 lands. They are expected in
   today's logs, not failures.

Pass condition: every fixed string above appears, in
order, with the two status lines in the frozen shape.
Fail condition: any fixed string missing, any invented
command listed by `help`, or any number presented as
proof without the line it came from.

## Drift table: old H1/H2 spec vs the built kernel

| Old spec string | Kernel reality | Verdict |
|---|---|---|
| Prompt `metaos> ` | No prompt printed | SUPERSEDED |
| Long line "ignored", limit 256 | `line too long, truncated to 80`, buffer 80 | SUPERSEDED |
| `unknown command: <first-token>` | `unknown command` + help re-list, no token echo | SUPERSEDED |
| Status as 3 separate lines with `heap <used>/<total> KiB` | 2 lines, `heap_free` form + STATUS form | SUPERSEDED |
| `help` lists none (`commands: (none yet)`) | `commands: status help` | SUPERSEDED (commands now exist) |
| Banner `META OS` / `milestone K<n>` 4-line form | Kernel prints `META OS - milestone K3` + alive line; no 4-line banner | SUPERSEDED as printed; frozen banner target is `META OS 0.1 (K6)` (Rowan R-1) |
| JSON agent record on serial | Serial gets console text, no JSON | UNIMPLEMENTED (format specified, not emitted) |
| Command set EMPTY | `status` + `help` run | SUPERSEDED |

`shell-formats.md` and `shell-formats.json` still carry
the old strings, and `tests/os-shell-formats.test.mjs`
still pins them. This commit deliberately does NOT
change those files: updating pinned formats and their
test is a separate Pax/Milo decision, and this spec
names the drift instead of silently rewriting the pins.
Follow-up: formats + test update to the frozen strings
above, or a Pax ruling keeping them as the aspirational
form.

## What this spec does not do

- No kernel code. Rowan's kernel lane owns `kernel/`.
- No service code. Goose services are a later layer;
  no Goose syntax is invented here.
- No home surface. See `home-surface.md`: the home
  surface stays static and labelled MOCK (H-5, unchanged
  by this task) until it reads real OS state.
- No program features. Programs stay warm, not hot.
- No cybersecurity program. PARKED by the boss's order.
  It is named only here, once, as parked.
- No claim without a log or a merge hash behind it.
  Every VERIFIED line above names its log or its
  source file on main.
