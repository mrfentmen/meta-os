<p align="center">
  <img src="docs/assets/banner.png" alt="Meta OS. An operating system for agents." width="100%">
</p>

# Meta OS

**An operating system for agents, built by a person and a crew of agents.**

Meta OS is three things, and this README keeps them apart because the difference matters:

| | What it is | Status |
|---|---|---|
| **The OS** | Our own kernel, in Rust, written from nothing: `kernel/`. Boots, maps memory, schedules, runs userspace, enforces an agent capability policy. | **Proven in QEMU.** K1–K6 with committed boot logs |
| **The platform** | The agent platform: Imperium's watch floor, the lab, the workshop, the studio, the board. Real model calls, real records, real budget guardrails. | **Running daily** |
| **The carrier** | A demo image remastered from Xubuntu so the platform has a desktop while the kernel's drivers are unfinished. | **Remastered demo — labelled, not a claim** |

The carrier is a machine to build on. It is not the operating system, and we do not
call it one. The eight-phase spec for removing it ships with this submission.

Built for the **Meta Global AI Developer Hackathon 2026**. One person directs; AI agents
build in lanes and check each other's work. Where something is partial, this repo says
so in those words.

---

## 1. The OS is real, and you can boot it in one command

`kernel/` is 16 Rust files, 9,794 lines, `no_std`, our own entry point, our own memory
manager, scheduler, interrupt handling and ELF loader. Not a fork. Not Linux.

```sh
# ~5 MB, boots in QEMU in about two seconds
qemu-system-x86_64 -m 512M \
  -drive format=raw,file=kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin \
  -serial stdio
```

What it does, from the committed logs in `os-build/logs/` (`K1-boot.txt`, `K3-boot.txt`,
`K6.1-cap-policy.txt`) and from the longer boot captured for the demo:

- prints `META OS KERNEL - alive (K1)`, then draws the Meta mark on a VGA console it owns
- parses a 15-region memory map, manages 127,996 frames, stress-tests a heap
- rotates three tasks, sleeps one for 200 ticks and wakes it (`C awake`); the demo capture
  also shows a task that never yields being preempted (`K5 preempt: task 1 -> 2`)
- loads and runs **five userspace ELF programs** in ring 3, each with a capability grant
- refuses what it should: `cap deny capcheck write 256 over 109`, `cap deny capcheck syscall 5`,
  `cap deny capcheck sleep 1000 over 100`
- kills a runaway task when its budget expires: `cap kill spinner budget 50 ticks`
- survives a page fault by killing only the faulting task: `INT user page-fault … task killed`
- answers a typed shell command, and exits cleanly: `user exit code 0`

**The agent layer starts in ring zero.** A capability policy is assigned at ELF entry and
checked on every syscall — allowed calls, write quota, sleep cap, wall-clock budget. Grants,
denials and budget kills are serial log lines. That is the first honest claim this project
can make about being an *agentic* OS: the kernel mediates agents, it does not just host them.

**What the kernel does not have yet:** PCI, storage, any filesystem, network, USB, graphics
modesetting, SMP, real-hardware boot. It runs programs because they are in its image, not
because it can read a disk. `os-build/KERNEL_STATUS.md` is the honest matrix.

---

## 2. The platform: institutions, not apps

Every system is a place built for an agent to work in. The agent perceives, decides, acts,
verifies, and records — and the record is the point.

| System | What it does | Status today |
|---|---|---|
| **Vigiles · Ignis · Medicus** | Imperium split into three apps — police, fire, EMS — each its own window and layout on one backend and one camera layer | Working. The submission core |
| **Scientia** | A science lab: forms hypotheses, runs experiments, grades evidence on a ladder it cannot skip | Built, 163-test wave-1 suite passing |
| **Officina** | A workshop: rough words in, a designed, tested artefact out | Working, stages 1–2a |
| **Musica** | A studio: composes, keeps the takes it likes, learns from the ones it keeps | In build |
| **Board (Nuntius)** | One messaging surface: rooms that remember, threads, `@mentions` that route to an agent, and the desk chat every app carries | Working, `board/board.mjs` on :18935 |
| **Custos** | Night watch for machines — patrols of certificates, services, known-exploited vulns | **Retired 2026-11-02**; the idea lives in the OS agents |

**How a flag works.** A small sign is yellow: recorded, shown to a human, chain stops. A big
sign is red: investigation with a step and spend cap, response sent only to a clearly
labelled **simulated** dispatch endpoint. Red means *flagged for human review*. Never
*confirmed incident*. The code refuses every non-loopback dispatch URL; there is no path
from this repo to a real emergency service.

**Identity rule.** Describe what a person looks like, never put a name to a face. Crops only
on flagged events, BOLO cards read `ID: UNIDENTIFIED`, a false alarm purges its evidence.

**Our own numbers, nobody else's.** Second evaluation batch, 100 frames through the live
pipeline: 42 matched the expected call, 46 held back as unsure, **0 real misses** (all 11
scored misses were frames taken before the event began), category validity 100/100, Vigiles
zero false altercations across both batches. On 2026-10-30 a live NYC DOT camera frame ran
the full loop and came back valid in about 6.4 seconds. Honest limit, stated plainly: the
flagged path has fired in staged runs, not yet on a live wild event.

---

## 3. Architecture: seven layers, three languages

The full model is `os-build/LAYERS.md` and `os-build/KERNEL_SPEC.md`. Two of the three
languages are unusual choices, deliberately: **Goose** and **Lobster** are real languages by
Wouter van Oortmerssen — memory-safe systems code and a VM with strict typing — and we use
them where a garbage collector or a lifetime annotation would get in the way.

| Layer | Language | What exists today | Status |
|---|---|---|---|
| 1 Boot | Rust | Our entry path, bootloader handoff, serial + console | **Proven** |
| 2 Kernel core | Rust | Memory, frames, heap, scheduling, IRQs, traps, ELF loader, capability policy | **Proven (QEMU)** |
| 3 Drivers | Rust | Framebuffer text console, keyboard, timer | **Proven (QEMU)**; no storage/net/graphics-mode driver |
| 4 Services | Goose | 21 services + 12 libraries, 40,269 lines | **Written, not compiled** — no build log yet |
| 5 Agent runtime | Lobster | identity, budget, memory, bus, scheduling shims, 180 lines | **Shape proof** |
| 6 Shell and apps | Lobster | Spec only; today's desktop surfaces are HTML on the carrier | **Not built** |
| 7 Programs | JS / Python | Imperium, Scientia, Officina, Musica, Board | **Working** |

We are not going to pretend layer 4 is done because the files are long. `services/BUILD.md`
says it itself: nothing there rises above WRITTEN until a toolchain compiles it and the log
is committed. That is the first lane of the next work round.

---

## 4. What is proven, and where the proof lives

Every claim above has a file. If a claim has no file, it is not in this README.

| Claim | Evidence |
|---|---|
| Kernel boots, prints, halts | `os-build/logs/K1-boot.txt` line 2 |
| Kernel draws its own console | `os-build/logs/K2-boot.png` (196 of 2000 cells carry glyphs) |
| Timer, keyboard, typed command | `os-build/logs/K3-boot.txt` |
| Paging, frames, heap stress | `os-build/logs/K1-boot.txt` (`mem summary: K4 up`) |
| Tasks rotate, sleep, wake | `os-build/logs/K1-boot.txt` (`C awake`) |
| Syscalls, userspace, refusals | `os-build/logs/K1-boot.txt` (`HELLO FROM USERSPACE`, `bad syscall 99 refused`) |
| Capability policy: grant, deny, budget kill | `os-build/logs/K6.1-cap-policy.txt` |
| Five userspace programs, grants and refusals | `os-build/logs/K1-boot.txt`, `os-build/logs/K6.1-cap-policy.txt` |
| Imperium pipeline end to end | `server/queue/` + `os-build/demo/EVAL4.md` |
| Agent loop, tools, budgets | `agents/agent_loop.mjs`, `agents/runtime.mjs`, `server/budget.mjs` |
| Desk chat: roster, rooms, routed `@mentions`, thread memory | `docs/AGENT_PROOF.md` §4 |
| Live tool run, 4 receipts, one recorded refusal, $0.0012 spend | `docs/AGENT_PROOF.md` §6, `tools/proof_agent_tools.sh` |
| Layer model and status words | `os-build/LAYERS.md`, `os-build/KERNEL_STATUS.md` |

Reproduce any row with the command in `os-build/tools/`; `os-build/tools/proof_boot.sh` runs
the boot checks, `os-build/tools/verify_tree.sh` runs the repo gates.

---

## 5. Run the platform

```sh
git clone https://github.com/Mrfentmen/meta-os && cd meta-os
./run-stack.sh                                  # board :18935, queue :8935, apps :8080
open http://127.0.0.1:8080/trio/vigiles.html    # Vigiles
open http://127.0.0.1:8080/trio/ignis.html      # Ignis
open http://127.0.0.1:8080/trio/medicus.html    # Medicus
open http://127.0.0.1:8080/surfaces.html        # every surface, with its status
```

The model calls need a key; without one the pages say so in-place instead of inventing an
answer (`server/model.mjs`). Budget guardrails are live: `server/budget.mjs` shares one
ledger with the queue's Python guardrail, so no path can spend past the cap.

`npm test` runs the suite. `npm run test:agents` runs the agent and chaos packs.

---

## 6. Build the demo image (the carrier)

Only meaningful to someone who wants the desktop: the pipeline needs Docker, an Ubuntu
family base ISO, and about an hour.

```sh
ISO=/iso/xubuntu-base.iso SRCDIR=/iso-mnt WORK=/tmp/isowork OUTDIR=/out \
  os-build/iso/merge-layers.sh
```

It unsquashes the base's `casper/minimal*.squashfs`, overlays our payload, provisions in a
chroot, and writes a branded ISO. What that produces is **a remaster**: the kernel, init,
casper, X11, GTK and WebKit in it belong to the base distribution. Our bytes are the theme,
the apps and the shell pages. Say that plainly on stage and there is nothing to catch you on.

---

## 7. What is not done (read this before believing anything)

1. **The kernel has never booted on real hardware.** Every log is QEMU. No UART, no physical
   framebuffer, no real keyboard controller.
2. **No storage, no filesystem, no network.** The kernel cannot load a program from a disk,
   which is why its userspace is compiled into its image.
3. **Layer 4 has never compiled.** 40,269 lines of Goose with no build log.
4. **The Lobster runtime is 180 lines.** A shape proof, not a runtime.
5. **The shipped image is a remaster**, and the app UI (WebKitGTK) will never run on our
   kernel as it stands. Porting the apps is Phase 6 of the rewrite spec, and it is months,
   not days.
6. **No approval cards yet.** The agent's tool path runs from `agents/`, and no surface
   asks you Allow/Deny before an action.

If a judge asks "so is this your OS?", the answer is: **the kernel is ours, the platform is
ours, the desktop is a carrier we remastered, and here is the log for the kernel.**

---

## 8. Repo map

```
kernel/            the OS: Rust, no_std, our entry point and syscalls
services/          Layer 4: Goose services and libraries (written, uncompiled)
lobster/           Layer 5-6: runtime shims and contracts
crates/            Rust service crates (supervisor, runtime, queue, guardrail, intel)
agents/            agent loop, runtime, tools, providers
server/            product API, model client, queue, budget ledger
trio/              Vigiles, Ignis, Medicus — three apps, one backend
imperium/          the original single watch floor the trio was split from
js/agent-chat.js   the desk chat every app carries
labs/              Scientia surfaces
design/            Officina, Musica, Custos surfaces
board/             the messaging surface
os-build/          image pipeline, branding, kernel specs and logs, gates
docs/              architecture, agentic notes, rewrite-the-ISO spec
plan/              the work rounds, in the order they were run
```

## 9. The crew

One person: **Del (Mrfentmen)** — direction, judgement, final testing on the Mac.
A crew of agents: **OpenCode** lanes (kernel, services, apps, evidence), **Buffy** (product,
UI, the demo), **Pax** (rulings and specs), **Milo**, **Rowan**, **Hana** — each with owned
paths, a branch, and a report that says what is real.

The method is the interesting part: a plan is only accepted with a command that reproduces
it, a status word is used exactly, and "NOT BUILT" is a complete answer.

---

**Status line for the submission:** Meta OS is a Rust kernel proven in QEMU, an agent
platform that runs daily, and a remastered demo image that carries the platform. Three of
those are true; the fourth is labelled.
