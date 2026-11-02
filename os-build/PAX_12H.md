# PAX — the 12-hour finish

**To:** Pax (spec keeper, gate, merges, boss's report)
**From:** Buffy (research and tools lane)
**Written:** 2026-11-01, ~20:05 EST
**Branch:** `buffy/pax-12h-plan` off `origin/main`. Three files: this doc, one boot log, one tool. Nothing else, so it reviews in five minutes.
**Status of every number here:** measured on this Mac in this session. Appendix A re-runs them. If a lane's report disagrees with a command in Appendix A, the command wins.

---

## 0. Four findings, and one of them is bad news

I need you to read this section before anything else, because it changes the plan, the scoreboard, and what we are allowed to tell the boss tonight.

### 0.1 The OS boots on this machine right now. That was not established before.

The docs said the kernel had never been built here, no nightly existed, and every kernel number was inherited evidence from another checkout. **All of that is wrong**, and I found out by trying it:

```
$ cd kernel && cargo check                    # 10.57s, 0 errors, 22 warnings
$ cargo bootimage                             # 8.2 MB image
$ qemu-system-x86_64 -drive format=raw,file=...bootimage-metaos-kernel.bin \
                     -serial file:/tmp/boot.txt -display none -no-reboot -m 128M
```

`nightly-aarch64-apple-darwin` is installed. `qemu-system-x86_64` is installed. `bootimage 0.10.5` is installed. What was actually wrong was **PATH shadowing**: Homebrew's stable `cargo`/`rustc` (1.99.1) sit ahead of the rustup proxies, so `-Z` flags get rejected by a stable compiler and the failure reads like "no toolchain". The fix is one line of environment:

```bash
NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
PATH="$NIGHTLY:$PATH" cargo bootimage
```

The kernel builds and boots from `main` today. That is the single fact that makes 12 hours plausible instead of impossible, and it was sitting behind a PATH bug.

### 0.2 The bad news: `main` does not run ring 3 today, and the fix is one flag

My first fresh boot of `main` was not the K6 everyone remembers. Every userspace program was refused:

```
user hello: 2523088 bytes magic=0x464c457f type=Some(2) entry=Some(2101600)
user hello loader refused: address in use
user sleeper loader refused: address in use
user crasher loader refused: address in use
```

`entry=2101600` is `0x201000` — two megabytes up. The kernel deliberately loads user programs at `0x6000_0000_0000` and above, so refusing them is the loader being *correct*. The binaries are wrong.

**Root cause, precisely:** `os-build/userspace/user/link.ld` is the script that puts `.text`/`.rodata`/`.data`/`.bss` at the right base, and its own header says the base is set **per program via sed** — hello `0x600000000000`, sleeper `0x610000000000`, crasher `0x620000000000`. But the tracked cargo config, `os-build/userspace/.cargo/config.toml`, passes:

```toml
rustflags = ["-C", "relocation-model=static", "-C", "code-model=large", "-C", "link-arg=-no-pie"]
```

There is no `-C link-arg=-Tlink.ld` in it. So `link.ld` is never used, every binary links at the default low address, and the loader refuses all three. The correctness of the refusal is the proof that the loader is fine and the build is broken.

**I fixed it and proved it.** With `-C link-arg=-T<link.ld-at-the-right-base>` on each program, one boot produced a complete K6 repro — logged at `os-build/logs/K6-repro-main-2026-11-01.txt`:

```
user hello: entry 0x600000000000
HELLO FROM USERSPACE
user exit code 0
user sleeper: entry 0x610000000010
sleeper: before sleep
sleeper: pid 5
sleeper: yielded and back
sleeper: bad call refused          <- syscall 99 refused, as designed
user crasher: entry 0x620000000110
crasher: about to read zero
INT user page-fault addr 0x0 err 0x4: task killed
```

That is ring 3, ELF loading at three distinct bases, `exit`, `sleep`, `yield`, an unknown-syscall refusal, and a fault isolated to one task — all from `main`, on this Mac, tonight. **K6 is real and re-earned.** It was one linker flag away the whole time.

### 0.3 The shell exists, takes typed input, and answers with live numbers — with no prompt and a scancode flood

I told the boss there was no shell. Wrong. `console_task` (`kernel/src/sched.rs:312`) and `run_command` (`:345`) are real, and I drove them with actual PS/2 keystrokes through the QEMU monitor (the tool is now committed at `os-build/tools/drive.py`):

```
INT keyboard scancode 0x0000000000000023
hINT keyboard scancode 0x00000000000000a3
...
commands: status help

sINT keyboard scancode 0x000000000000001f
...
tasks 7 ticks 805 heap_free 31K
STATUS tasks=7 ticks=805 heap_free_kb=31
```

So: yes, you can type into Meta OS, and `status` tells the truth about the machine. Also visible in that same log, and this is the honest list of what is wrong with it:

- **no prompt** — a blank line just sits there, you cannot tell if it heard you
- **no backspace** — `0x0E` is unhandled, so a typo can only be fixed by 80 bytes of noise
- **every keystroke prints a debug line** — 24 of them in a 103-line log, interleaved into the echo
- **`uptime Ns` every second**, forever, into serial
- **two commands** — `help`, `status`
- **the banner says `META OS - milestone K3`** while K4, K5, K6 features are all running. The kernel understates its own milestone in its own first line. That is a Milo/gate honesty issue and it is a one-string fix in `main.rs`.

This is the cheapest real milestone available to us tonight, and it is 80% done.

### 0.4 Correction to my own numbers: 1,060 dead lines, and two competing syscall layers

My earlier report said 484 lines of the kernel are unwired. Counting the module declarations against the files that exist gives a different and worse answer:

| Wiring | Modules | Lines |
|---|---|---|
| **live** (declared in `main.rs`) | `gdt` 162, `interrupts` 520, `mem` 301, `memory` 1004, `sched` 446, `tasks` 702, `traps` 183, `user` 465, `vga` 166, plus `main` 189 | **4,138** |
| **dead** (in `src/`, never declared) | `framebuffer` 576, `syscalls` **484** | **1,060** |
| total | 12 files | 5,198 |

So **20% of the kernel cannot run**, not 9%. I missed `syscalls.rs` and I want that on the record before you certify anything.

The reason it matters beyond a line count: **there are two syscall implementations.**

- `kernel/src/syscalls.rs` — 484 lines, a generic `dispatch<S: KernelServices>` layer with a trait, service records, boot-info and start-error validation. Its own header says, in capitals, `UNWIRED ... NOT A KERNEL-CRATE COMPILE, NOT A BOOT VERDICT, NOT A SYSCALL THAT HAS EVER RUN`. Rowan wrote it honestly and labelled it honestly.
- `kernel/src/user.rs:90` — a 40-line `match num` inline in the trap handler. **This is the one that runs.** It is the one that printed `HELLO FROM USERSPACE`, refused syscall 99, and exited 0.

Both exist, both are plausible, and nothing in the repo says which is authoritative. If F1 is not resolved with a file name attached, six agents will write against different syscall layers and we will spend the night merging two ABIs. My reading: the inline `user.rs` dispatch is what is proven, so it is authoritative tonight, and `syscalls.rs` is a 2026-11-02 decision — wire it deliberately or delete it, but do not leave two.

---

## 1. Corrections owed before anything merges

You gate on documents, and three of them ask you to certify things that are not true. I am not asking for trust — Appendix A re-derives every row.

| File | Says now | Measured | Owner |
|---|---|---|---|
| `os-build/layer1/BUFFY_REPORT.md` | 21 services + 12 libraries `WRITTEN` | `goose check`: **7 of 95 pass, 297 errors** | **me**, tonight |
| `os-build/layer1/SIGNOFF.md` | reads as a deliverable layer | deliverable as *source*, never executed | **me**, tonight |
| `os-build/SCOREBOARD.md` (v4 @ `445daf8`) | L1 "no K1 boot log exists anywhere" | `K1-boot.txt` + `run1/2/3` + K2–K6 all present in `os-build/logs/` | **Milo** |
| `os-build/SCOREBOARD.md` | L4 "DESIGNED, NOT BUILT", no buffy branch on remote | branch exists and is pushed (`ebf05d7`, 95 files) | **Milo** |
| `os-build/SCOREBOARD.md` | L2/L3 kernel "unverified: kernel-crate compile, any boot" | **compiles (0 errors) and boots here**, K6 repro committed tonight | **Milo** — biggest correction |
| `os-build/SCOREBOARD.md` | K2 framebuffer "576 lines merged, queued for wiring" | `DEAD`: documented unreachable on bootloader 0.9.35 (`main.rs:7`) | **Milo** |
| `os-build/SCOREBOARD.md` (and my own report) | "484 lines unwired" | **1,060** dead lines across `framebuffer.rs` + `syscalls.rs` | **Milo** and **me** |
| `SCOREBOARD.md` L6 "no shell runs against real OS state" | shell runs, takes typed input, reports live tasks/ticks/heap | **Milo** |

The scoreboard is stale by roughly 8 commits and it understates the kernel in the *safe* direction and overstates the services in the *unsafe* direction. Fix both, in the same pass, tonight.

**And one thing the boss should hear from you, not from me:** the 21 services are source, not running code. They do not load into this kernel and there is no syscall surface that would let them. Tonight they can typecheck; they cannot serve.

---

## 2. Where we actually are

Words used exactly: `PROVEN` (a log file I can name) · `TYPECHECK-FAILS` · `WRITTEN` (never executed) · `DEAD` (documented unreachable) · `NOT STARTED`.

| Layer | What exists | Status | Evidence |
|---|---|---|---|
| L1 Boot | K1 skeleton, proof string | **PROVEN** | `logs/K1-boot*.txt` (4 runs) |
| L2 Kernel core | 5,198 lines, 12 files; paging, heap, scheduler | **PROVEN on this Mac** | `logs/K4-repro` results inside `K6-repro-main-2026-11-01.txt`; `K4-boot.txt`, `K5-boot.txt` |
| L3 Drivers | IDT/PIC/PIT/PS-2 keyboard | **PROVEN, typed input this session** | `K6-repro-main-2026-11-01.txt` |
| L3 display | `framebuffer.rs` 576 lines; `main.rs` states no pixel framebuffer exists under bootloader 0.9.35 | **DEAD — and already documented as dead by Rowan** | `kernel/src/main.rs:7-8`, `os-build/research/framebuffer.md` |
| L2 syscalls | `syscalls.rs` 484 lines, generic dispatch, self-labelled UNWIRED; the live ABI is the inline `match` in `user.rs:90` | **DEAD, with a live duplicate** | `kernel/src/user.rs:90` vs `kernel/src/syscalls.rs:1-30` |
| L4 Services | 95 files, 21,773 lines | **TYPECHECK-FAILS (7/95, 297 errors)** | App. A §A3 |
| L5 Agent runtime | Lobster host, real tool round-trips | **PROVEN at demo scale** | `lobster/host.log` |
| L6 Shell | `help` + `status`, typed input, no prompt, no backspace | **PROVEN** | `K6-repro-main-2026-11-01.txt`, `O-shell2.txt` |
| L7 Programs | — | **NOT STARTED** | nothing on any branch |

**Correction to my own earlier report, in fairness to Rowan:** the framebuffer was not a discovery on my part. `main.rs` already says in its header that no pixel framebuffer exists under `bootloader 0.9.35` and points at a research note. He documented his own dead end correctly. What nobody escalated is that 576 lines of module sit in `src/` that no boot path can reach — that belongs in the scoreboard as `DEAD`, not as "queued for wiring".

---

## 3. What we are allowed to claim at H+12

Aim every lane at this one sentence and nothing else:

> **Meta OS boots on x86_64 in QEMU, drops to ring 3, runs three userspace programs, isolates a fault to one task, and gives you a shell that reports the machine's real state — reproduced from a clean checkout by one command, every claim backed by a committed boot log.**

Every clause of that is **already true tonight**. What is missing is that it takes a human who knows the PATH trick and the linker flag, and that it has no prompt, no backspace, and two commands. So the 12 hours are not about *reaching* the claim. They are about *automating* it and making the shell decent enough to demonstrate.

The demo that proves it — the target screen, not a wish list:

```
$ os-build/gate.sh
  toolchain  nightly ok
  userspace  3 binaries ok   bases 0x6000.., 0x6100.., 0x6200..
  kernel     0 errors, 22 warnings
  boot       7/7 proof lines found
  GATE GREEN

META OS 0.1  (K7)
tasks 7  ticks 812  heap 31K free

meta> help
  commands: help status mem ps clear uptime ls cat panic
meta> ps
  idle  cpu 3%   ticks 700
  C     cpu 1%   ticks 61   sleeping until 812
  A/B   cpu 0%   ticks 20/20
meta> mem
  frames 28962 free / 28962
  heap   256K total, 225K free
meta> hepl
  unknown command: hepl      (try: help)
meta> []
```

Concretely, that needs from the kernel: a prompt string, backspace + shift, `mem`, `ps`, silence on scancodes, no per-second uptime, and a milestone string that tells the truth. Every number `mem` and `ps` need is already computed by `memory.rs` and `tasks.rs`. **Nothing in the demo needs the framebuffer, networking, graphics, or a package manager.**

**What we will not claim,** and should say in the same breath on the boss's report:

- the services layer does not run in the kernel; it typechecks natively at best
- no framebuffer, no graphics, only VGA text
- no networking (the `services/` IP/ARP/TCP files are source, not sockets)
- no persistence across reboot, no SMP, no USB, no sound, no installer
- Layer 7 does not exist

---

## 4. Six agents on six codebases: what actually helps

Straight answer, because the boss is expecting acceleration.

**Our critical path is one crate with one entry point.** 4,138 of the kernel's 5,198 lines are reachable from `main.rs`; every module anyone writes has to land in that same tree to be provable, and 1,060 lines already sit there unreachable because two people wrote modules in parallel and nobody wired them. Two agents editing `sched.rs` and `user.rs` simultaneously produce a merge nobody can boot, and a boot nobody can reproduce is worth zero tonight. So kernel lanes add throughput only up to **one writer per file**, and tonight there is room for exactly one kernel writer: Rowan.

The parallelism that is real, and how I would spend it:

```
serial critical path:  toolchain fix -> gate.sh -> boot -> shell commands -> log -> report
true parallel (4 lanes): kernel shell work | format contract | goose corpus | gate+docs
```

**The multiplier is not the sixth agent. It is `gate.sh`.** Once one command builds both crates and asserts on a boot log, every lane becomes verifiable by you in 90 seconds, no human on a Mac, no inherited evidence, no "trust me". That is worth more than three extra agents, and it is the first thing OpenCode should do — before any kernel feature work.

So my recommendation for the roster: Rowan on the kernel, Hana on the format contract and demo script, Milo on gates and the honest scoreboard, OpenCode on the toolchain + `gate.sh` + boot logs, me on the Goose corpus and the corrections, you on freezes, merges and the report. Five writers and a gate. Adding a sixth does not shorten the night.

---

## 5. Four things to freeze in the first 30 minutes

After H+0:30 these are frozen; any change costs a merge to `main` plus a line in `KERNEL_SPEC.md`.

### F1 — Syscall numbers (the only true ABI we have)

Live in `kernel/src/user.rs:90`, `int 0x80`:

| num | call | status |
|---|---|---|
| 0 | `exit` | PROVEN (`user exit code 0`) |
| 1 | `write` | PROVEN (`HELLO FROM USERSPACE` prints) |
| 2 | `sleep` | PROVEN (`sleeper: yielded and back`) |
| 3 | `pid` | PROVEN (`sleeper: pid 5`) |
| 4 | `yield` | PROVEN |
| 5 | **`read_key`** | **PROPOSED** — the keyboard ring buffer exists and the console already drains it; a syscall needs a getter, not new machinery |
| 99 | unknown | PROVEN refused (`user bad syscall 99 refused`) — the `n =>` arm at `:110` is already safe |
| 6–15 | reserved | keep the block; never renumber, never re-use |

**Ask:** approve 5, reserve 6–15, rule that a number is never reallocated, and **name the authoritative implementation: `kernel/src/user.rs:90` (the proven inline dispatch), with `syscalls.rs` frozen as DEAD until 2026-11-02.** Every program and service written today points at this table, and right now there are two tables.

### F2 — Banner and status fields, as data

The kernel's banner is currently wrong in the other direction (`META OS - milestone K3` on a K6 tree), which proves the point: this must be a contract, not a string someone edits. Minimum, reconcilable with what the shell already prints in `STATUS tasks=7 ticks=805 heap_free_kb=31`:

```
version   META OS 0.1
milestone K<last proven>
state     healthy | N degraded
tasks     <n>
ticks     <n>
heap      <n>K free
```

**Ask:** confirm the field set and the `KEY value` shape so the kernel can print it with no allocation and the shell can parse it. Hana's spec wins if it already says otherwise — but say which, tonight, or Rowan hard-codes a fourth variant.

### F3 — Where the Goose root lives

`services/root.goose` is the file that makes the corpus typecheck (§0.4 below). Goose resolves `import a.b.c;` relative to the root file's directory. **Ask:** pick root-at-`services/` (smallest diff; existing imports already read `common.sys.sys`) or root-at-repo (imports must all be rewritten), and put it in `KERNEL_SPEC.md`.

### F4 — Freeze discipline

One owner per file, declared in §6; a second agent comments on the PR instead of editing. Nobody merges to `main` but you. Milo gates Rowan and Hana; you gate Milo; you personally gate every kernel merge. **Hard freeze at H+9:** all lanes push their tip and stop; after that, only gate fixes and the report.

---

## 6. Lane assignments

### Rowan — kernel (branch `rowan/kernel`)

| # | Deliverable | File | Proof |
|---|---|---|---|
| R-1 | Fix the banner: real milestone, `META OS 0.1 (K7)` shape per F2 | `kernel/src/main.rs` | boot log, first line |
| R-2 | Prompt string + backspace (`0x0E`) + shift (`0x2A/0x36`, releases `0xAA/0xB6`) | `kernel/src/sched.rs` | boot log showing a corrected typo |
| R-3 | Kill the per-keystroke `INT keyboard scancode` debug line; keep it behind a debug switch if wanted | `kernel/src/sched.rs` (and wherever the INT handler prints) | boot log: 103 lines → ~45, echo readable |
| R-4 | Stop the once-per-second `uptime` print; keep `uptime` as a command | `kernel/src/sched.rs` | 30s quiet run |
| R-5 | `mem`: print what `memory.rs` already computes (free frames/total, heap used/total) | `kernel/src/sched.rs` | boot log |
| R-6 | `ps`: task slots + per-task ticks/cpu from the counters the scheduler keeps | `kernel/src/sched.rs`; getter in `tasks.rs` only if missing | boot log |
| R-7 | Syscall 5 `read_key` | `kernel/src/user.rs` | ring-3 program calls it, log shows a key |
| R-8 | Keep `MAC_QUESTIONS.md` current with exact API points | `kernel/MAC_QUESTIONS.md` | — |

**Not tonight:** framebuffer (documented dead — leave it), paging or allocator changes, SMP, anything in `gdt.rs`/`traps.rs` without telling Pax first, `cat`/`ls` until R-1…R-7 are green.

### Hana — shell and experience (branch `hana/os-shell`)

| # | Deliverable | File | Proof |
|---|---|---|---|
| H-1 | Freeze F2 as data: exact strings for banner, prompt, status, and the unknown-command error | `os-build/shell-spec.md` | Pax confirms; Rowan copies strings, not intentions |
| H-2 | The 8-command surface with **exact output** for each, including the refusal wording | `os-build/shell-spec.md` | Rowan implements from it |
| H-3 | Prompt behaviour: before, during, after a command; what a truncated line looks like | `os-build/shell-spec.md` | matches R-2 |
| H-4 | Retype the §3 demo as the acceptance script, line for line | `os-build/shell-spec.md` | OpenCode turns it into O-4 |
| H-5 | Home-surface mock stays static, labelled MOCK, no invented live data | app | unchanged |

**Not tonight:** Musica or any program feature (boss's sequencing), any Swift.

### Milo — verification and gate (branch `milo/os-gate`)

| # | Deliverable | File | Proof |
|---|---|---|---|
| M-1 | The boot-log gate: the exact grep line proving each milestone K1…K7, as a runnable checklist | `os-build/gates.md` | runs against `os-build/logs/` and passes |
| M-2 | Scoreboard v5 in the true words of §1 and §2, including `DEAD` for the framebuffer and the K1-log correction | `os-build/SCOREBOARD.md` | no PROVEN row without a named log |
| M-3 | The per-merge checklist (≤10 lines: what runs, in order, and what "no" looks like) | `os-build/gates.md` | Pax runs it unaided |
| M-4 | Gate-1 on every Rowan and Hana push, verdict in room 1 with the log file named | — | verdicts posted |
| M-5 | Reject any report line that claims a milestone without a log file name | — | that is the whole job |

### OpenCode — build and boot (branch `opencode/os-build`)

Highest-leverage lane tonight: everyone else's proof depends on it.

| # | Deliverable | Proof |
|---|---|---|
| O-1 | **`os-build/gate.sh`** — the paste-ready recipe is Appendix B, already proven end to end here. Builds userspace (per-program bases), builds kernel, boots QEMU headless, greps proof lines, exits non-zero on any miss | one command, green |
| O-2 | Fix the toolchain so it does not depend on a human's PATH: either a `rust-toolchain.toml` + doc'd `PATH`, or a wrapper in `gate.sh` that pins nightly via `rustup which`. Also note `llvm-tools-preview` must be present for `bootimage` | gate runs on a machine where Homebrew cargo is first in PATH |
| O-3 | **The userspace linker fix** (Appendix C): `-Tlink.ld` per program with its own base, so `main` runs ring 3 without hand-editing | fresh clone → boot → `HELLO FROM USERSPACE` |
| O-4 | `os-build/logs/K7-boot.txt`: the §3 demo typed through `os-build/tools/drive.py`, committed | log shows prompt + 8 commands |
| O-5 | Re-run QEMU against every merge Pax lands and post the log name; no merge green on a stale log | gate comments |

### Buffy — research and tools (branch `buffy/layer1-goose-services`)

| # | Deliverable | Proof |
|---|---|---|
| B-1 | `services/root.goose` + the F3 convention → kills **225 of 297** errors in one file | `goose check` counts before/after |
| B-2 | The ~72 dialect errors: `guard`/`pad` reserved, `let` reassignment, `x++`, `\b`, `parse_int`, missing `common.err` imports | 0 errors, or a named remainder |
| B-3 | Correct `BUFFY_REPORT.md` + `SIGNOFF.md` to measured words | diff is words only |
| B-4 | Exercise the service corpus natively, report pass/fail as measured | output in the report |
| B-5 | One page for the boss: what the services layer *is* (userland Goose source, typechecked, not kernel-loadable) | `os-build/layer1/SERVICES_SCOPE.md` |
| B-6 | Keep `os-build/tools/drive.py` working as the typed-input harness the gate uses | committed tonight |

**Not tonight:** tools manifest, distro notes, network stack, new services.

### You — Pax

Merges, the four freezes, the report, and the one job nobody else can do: **keep "OS" from meaning two different things in the same document.**

---

## 7. Requests, numbered, each with a deadline

| # | Ask | By | If you decline |
|---|---|---|---|
| **P-1** | Approve §3 as the definition of done and as the only claim in the boss's report | H+0:30 | Six lanes aim at six targets and we finish none |
| **P-2** | Rule F1: syscall 5 = `read_key`, 6–15 reserved, never renumber | H+0:30 | R-7 waits; kernel shell work stops at the prompt |
| **P-3** | Rule F2: banner/status fields, `KEY value` shape, and that `milestone` must name the **last proven** milestone | H+0:45 | The kernel ships a false milestone string on its own first line |
| **P-4** | Rule F3: Goose root location | H+0:45 | I still fix 72 dialect errors; 225 stay |
| **P-5** | Order the corrections: scoreboard (Milo) and my report (me), and require `DEAD` for the framebuffer and `TYPECHECK-FAILS` for services | H+1 | Gate 1 certifies fiction again |
| **P-6** | Declare `gate.sh` mandatory: **no merge tonight without a green gate run**, docs included | H+1 | Every claim stays inherited evidence |
| **P-7** | Put the kill list in writing: framebuffer, graphics, networking, SMP, persistence, package manager, installer, cybersecurity program | H+1 | Someone spends H+8 on graphics |
| **P-8** | Enforce the H+9 freeze; after it, only gate fixes and the report | H+9 | Six unmergeable branches at H+12 |
| **P-9** | Give O-1/O-2/O-3 to OpenCode **ahead of** any kernel feature work | H+1 | The critical path stays human-serialised |
| **P-10** | Rule on `main` tonight: accepts only (a) a kernel module that boots with a log, (b) doc corrections, (c) `gate.sh`, (d) the userspace linker fix. Everything else waits for the freeze | H+1 | `main` mixes proven and claimed again |
| **P-11** | Tell the boss the sentence in §0.2 before the good news: **`main` as committed does not run ring 3; it is one linker flag away and the fix is proven.** He should hear it from the gate, with the log, not discover it later | H+1 | The first question he asks that we cannot answer costs a day of trust |
| **P-12** | Rule the fate of `kernel/src/syscalls.rs` (484 lines, DEAD): **freeze it tonight**, decide wire-or-delete on 2026-11-02. Nobody writes a syscall into it before that ruling | H+0:45 | Two ABIs, six agents, one night |
| **P-13** | Require every lane report tonight to state its line counts as wired/dead (Appendix A §A11), because that is the measure that exposed 1,060 unreachable lines | H+1 | Reports keep saying "N lines written" and we keep mistaking that for N lines that run |

One thing I am asking for myself: if a lane's work cannot be verified tonight, let it land on a branch unmerged and name it in the report. An unmerged honest branch is worth more at H+12 than a merged claim we cannot defend.

---

## 8. Risks, with the trigger that means "change the plan"

| Risk | Odds | Trigger | Response |
|---|---|---|---|
| `gate.sh` slips | Medium | not green by H+3 | You and Milo verify by hand; expect 3–4 merges, not 10 |
| Two writers in `sched.rs` | High if OpenCode touches it | any commit outside Rowan's lane | one owner per file, enforced by you |
| PATH/toolchain fix does not survive a fresh clone | Medium | O-2 not done by H+2 | pin the nightly path *inside* `gate.sh`; document `llvm-tools-preview` |
| Keyboard edge cases (shift, release codes) eat an hour | Medium | 2h without a clean corrected line | ship without shift; backspace is the one that must work |
| Goose dialect fixes cascade | Medium | B-2 exceeds 4h | fix in dependency order, stop when `common.*` is clean, report the remainder by name |
| Someone "wires the framebuffer" | Medium | branch touching `framebuffer.rs` | P-7 kill list; it is `DEAD` on 0.9.35 and needs a bootloader upgrade, which is a 2026-11-02 decision |
| A report claims PROVEN without a log | Medium | any row lacking a filename | Milo's gate rejects it |

---

## 9. What I expect to actually happen

- **H+2:** gate green on this Mac from a clean checkout; `main` boots ring 3 without hand-edits (O-3); toolchain pinned.
- **H+4:** prompt, backspace, no scancode noise, no uptime spam (R-1…R-4). First log where you can read the transcript.
- **H+7:** `mem`, `ps` live; `read_key` in the ABI; demo script typed end to end.
- **H+9:** freeze. Goose corpus at 0 errors or a named remainder; scoreboard and reports honest.
- **H+11:** `K7-boot.txt` committed, one kernel merge, report written.
- **What slips first:** `cat`/`ls` (needs a RAM-disk), shift, and the service test run. I would let all three slip before I let the gate slip.

If we land that, the sentence in §3 is true, reproducible and demonstrable, and nobody has to be talked past a word. We will not have the seven-layer architecture in `KERNEL_SPEC.md`: services are userland source, the agent layer is a host process, and Layer 7 is a blank page. Saying that plainly beside the demo is the difference between a project that survives the week and one that dies the first time someone asks for the boot log we cannot produce.

---

## Appendix A — reproduce everything

```bash
cd meta-os

# A1. Toolchain (the real situation: nightly IS installed, PATH shadows it)
rustup toolchain list                      # nightly-aarch64-apple-darwin present
which cargo rustc                          # /opt/homebrew/bin/... <- the shadow
rustc --version                            # 1.99.1
NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
echo "$NIGHTLY"                            # .../toolchains/nightly-aarch64-apple-darwin/bin
rustup component list --toolchain nightly | grep llvm-tools   # required by bootimage
which qemu-system-x86_64                   # /opt/homebrew/bin/qemu-system-x86_64
bootimage --version 2>/dev/null || PATH="$NIGHTLY:$PATH" cargo bootimage --version   # 0.10.5

# A2. Userspace: WITHOUT the linker script (what the repo does today)
cd os-build/userspace/user
PATH="$NIGHTLY:$PATH" cargo build --target x86_64-unknown-none --bins
# entry points land near 0x201000 -> loader refuses them at boot

# A3. Userspace: WITH the linker script (the fix, per program)
for pair in "hello 0x600000000000" "sleeper 0x610000000000" "crasher 0x620000000000"; do
  set -- $pair
  sed "s/0x620000000000/$2/" link.ld > /tmp/link-$1.ld
  RUSTFLAGS="-C relocation-model=static -C code-model=large -C link-arg=-no-pie \
             -C link-arg=-T/tmp/link-$1.ld" \
    PATH="$NIGHTLY:$PATH" cargo build --target x86_64-unknown-none --bin $1
done

# A4. Kernel: compile and image
cd ../../../kernel
PATH="$NIGHTLY:$PATH" cargo check                # 0 errors, 22 warnings, ~10s
PATH="$NIGHTLY:$PATH" cargo bootimage            # 8.2 MB image

# A5. Boot headless, capture serial
rm -f /tmp/boot.txt
(qemu-system-x86_64 -drive format=raw,file=target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin \
  -serial file:/tmp/boot.txt -display none -no-reboot -m 128M >/dev/null 2>&1 &)
sleep 20; pkill -f bootimage-metaos-kernel
grep -E "HELLO FROM USERSPACE|page-fault|STATUS tasks" /tmp/boot.txt

# A6. Type into the shell (real PS/2 keys, not serial)
python3 os-build/tools/drive.py 9 help status

# A7. Does main run ring 3 as committed? (the §0.2 regression)
git stash -u && # rebuild userspace per A2, boot per A5
grep -c "loader refused" /tmp/boot.txt      # 3  <- as committed today
# after A3: grep -c "HELLO FROM USERSPACE" -> 1

# A8. Goose corpus (Layer 4's real status)
cd ..                                        # meta-os/
find services -name '*.goose' | wc -l        # 95
find services -name '*.goose' -exec cat {} + | wc -l   # 21773
ok=0; bad=0
for f in $(find services -name '*.goose'); do
  goose check "$f" >/dev/null 2>&1 && ok=$((ok+1)) || bad=$((bad+1))
done; echo "OK $ok FAIL $bad"                # OK 7 FAIL 88
for f in $(find services -name '*.goose'); do goose check "$f" 2>&1; done \
  | grep -c "cannot find module"             # ~225 of 297

# A9. The shell that exists
grep -n 'fn console_task\|fn run_command' kernel/src/sched.rs   # 312, 345
sed -n '345,375p' kernel/src/sched.rs
cat os-build/logs/K6-repro-main-2026-11-01.txt

# A10. Framebuffer: dead, and already documented as dead
sed -n '1,14p' kernel/src/main.rs            # "No pixel framebuffer exists under bootloader 0.9.35"
grep -A2 'name = "bootloader"' kernel/Cargo.lock   # 0.9.35

# A11. Wired vs dead lines (the measure that found 1,060 unreachable lines)
cd kernel/src
wc -l *.rs | sort -rn                         # total 5198
grep '^mod ' main.rs                          # 9 modules declared
# declared: gdt interrupts mem memory sched tasks traps user vga
# NOT declared, therefore cannot run: framebuffer.rs (576), syscalls.rs (484)
for m in gdt interrupts mem memory sched tasks traps user vga framebuffer syscalls; do
  printf '%-12s %5s lines  %s\n' "$m" "$(wc -l < $m.rs)" \
    "$(grep -q "^mod $m;" main.rs && echo wired || echo DEAD)"
done
```

---

## Appendix B — `gate.sh`, paste-ready (proven end to end tonight)

```bash
#!/usr/bin/env bash
# os-build/gate.sh — build both crates, boot, assert. Non-zero on any miss.
set -euo pipefail
cd "$(dirname "$0")/.."

NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
export PATH="$NIGHTLY:$PATH"
FLAGS="-C relocation-model=static -C code-model=large -C link-arg=-no-pie"

echo "== userspace"
cd os-build/userspace/user
for pair in "hello 0x600000000000" "sleeper 0x610000000000" "crasher 0x620000000000"; do
  set -- $pair
  sed "s/0x620000000000/$2/" link.ld > "/tmp/link-$1.ld"
  RUSTFLAGS="$FLAGS -C link-arg=-T/tmp/link-$1.ld" cargo build --target x86_64-unknown-none --bin "$1"
done
cd ../../..

echo "== kernel"
(cd kernel && cargo bootimage)

echo "== boot"
LOG="$(mktemp)"; DRIVE="$(mktemp)"
IMG="kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin"
qemu-system-x86_64 -drive format=raw,file="$IMG" -display none -no-reboot -m 128M \
  -serial "file:$LOG" -monitor "unix:$DRIVE,server,nowait" &
QEMU=$!
sleep 18
python3 os-build/tools/drive.py --monitor "$DRIVE" help status
sleep 1; kill $QEMU 2>/dev/null || true; sleep 1

echo "== assert"
fail=0
check() { grep -q "$1" "$LOG" && echo "  ok   $2" || { echo "  FAIL $2"; fail=1; }; }
check "META OS KERNEL - alive"   "K1 alive"
check "mem summary: K4 up"       "K4 memory"
check "HELLO FROM USERSPACE"     "K6 ring 3"
check "user exit code 0"         "K6 clean exit"
check "task killed"              "K6 fault isolation"
check "commands: status help"    "shell answered"
check "STATUS tasks="            "status reported live state"
grep -q "loader refused" "$LOG" && { echo "  FAIL userspace refused"; fail=1; }
[ $fail -eq 0 ] && echo "GATE GREEN ($LOG)" || { echo "GATE RED ($LOG)"; exit 1; }
```

`drive.py --monitor` attaches to a QEMU the gate already owns, so the gate keeps one process to kill and one log to assert on. `drive.py` without `--monitor` starts its own QEMU for a human; that is how the K6 repro log in this branch was produced.

Two things the gate should assert that this draft does not: the boot log must contain a **prompt** (R-2) and must **not** contain `loader refused` (O-3). Both are one `check` line each, and both are exactly the regressions we just found by hand.

---

## Appendix C — the userspace fix, as a patch

The whole regression, in one file:

```diff
  # os-build/userspace/.cargo/config.toml
  [target.'cfg(target_os = "none")']
- rustflags = ["-C", "relocation-model=static", "-C", "code-model=large", "-C", "link-arg=-no-pie"]
+ rustflags = ["-C", "relocation-model=static", "-C", "code-model=large", "-C", "link-arg=-no-pie",
+             "-C", "link-arg=-Tlink.ld"]
```

That is not sufficient by itself, because `link.ld` hard-codes **crasher's** base (`0x620000000000`). Two honest options:

1. **Per-program configs** (what I proved): build each bin with its own `-T` script at its own base. Needs `gate.sh` to pass `RUSTFLAGS` per `--bin`, which cargo invalidates between invocations — 9s per program, ~27s total. Works today.
2. **One base + relocatable loading** (cleaner, 2026-11-02): link all three at one base and have the loader pick a free window per program. This is the right design and it is not a tonight change — it touches the mapper's refusal logic, which is currently doing exactly what it should.

Take option 1 tonight. Do not touch the loader's refusal path; that refusal is the reason we could diagnose this in ten minutes.
