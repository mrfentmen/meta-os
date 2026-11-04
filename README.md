<p align="center">
  <img src="docs/assets/banner.png" alt="Meta OS. An operating system for agents." width="100%">
</p>

# Meta OS

**An operating system for agents, built by a person and a crew of agents.**

Meta OS is three things, and this README keeps them apart because the difference matters:

| | What it is | Status |
|---|---|---|
| **The OS** | Our own kernel, in Rust, written from nothing: `kernel/`. Boots, maps memory, schedules, runs userspace, enumerates PCI, draws a 1280×720 framebuffer; mediates agents at the syscall boundary on the caps branch. | **Proven in QEMU.** K1–K6 boot logs, PCI + framebuffer added this round; the capability slice is one merge out |
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
- parses a 15-region memory map, manages its own frame allocator (61,660 frames in
  `K1-boot.txt`, 125,438 in the demo capture), stress-tests a heap
- rotates three tasks, sleeps one for 200 ticks and wakes it (`C awake`)
- loads and runs **five userspace ELF programs** in ring 3 — `hello`, `sleeper`, `crasher`,
  `readkey`, `demand` (`kernel/src/user.rs:19-27`)
- survives a page fault by killing only the faulting task: `INT user page-fault … task killed`
- answers a typed shell command, and exits cleanly: `user exit code 0`

**The agent layer is a kernel layer, and it is one merge from this tree.** The capability
slice (`kernel/src/caps.rs`) is on its own branch — commits `f6c11df3`, `381bd73d` — where it
assigns a per-task permit at ELF entry, checks it on every syscall and preempts a ring-3 task
on the timer. Its capture, `K6.1-cap-policy.txt`, is a real boot of that branch: `cap grant
capcheck write=128 ticks=2000 sleep=100`, then `cap deny capcheck write 256 over 109`,
`cap deny capcheck syscall 5`, `cap deny capcheck sleep 1000 over 100`. It was excluded from
merge `4fd9653c` because it claimed syscall 6, which the frozen table had already given to
IPC; the tree you are reading dispatches 6 = `ipc_send`, 7 = `ipc_recv` and enforces no
capability policy. Landing it means restoring `caps.rs` and taking syscall 8 — the reasoning
and the exact steps are in `os-build/KERNEL_SPEC.md`.

**What the kernel does not have yet:** storage (PCI is enumerated — six devices, IDE found —
but no block driver reads a disk), any filesystem, network, USB, mouse, windowing, SMP, and
any real-hardware boot. It runs programs because they are in its image, not because it can
read a disk. `os-build/KERNEL_STATUS.md` is the honest matrix.

---

## 2. The platform: institutions, not apps

Every system is a place built for an agent to work in. The agent perceives, decides, acts,
verifies, and records — and the record is the point.

| System | What it does | Status today |
|---|---|---|
| **Imperium** | Watches camera feeds and flags scenes for human review across three divisions: **Vigiles** (streets), **Ignis** (fire and smoke), **Medicus** (EMS scenes, never a diagnosis) | Working. The submission core |
| **Scientia** | A science lab: forms hypotheses, runs experiments, grades evidence on a ladder it cannot skip | Built, 163-test wave-1 suite passing |
| **Officina** | A workshop: rough words in, a designed, tested artefact out | Working, stages 1–2a |
| **Musica** | A studio: composes, keeps the takes it likes, learns from the ones it keeps | In build |
| **Nuntius / Board** | One messaging surface: rooms, threads, a board agents and people share | Working (`board/`) |
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
| 3 Drivers | Rust | VGA text console, keyboard, timer, PCI enumeration, 1280×720 linear framebuffer | **Proven (QEMU)**; detection only — nothing reads a disk, no network, no mouse |
| 4 Services | Goose | 22 services + 18 libraries, ~40k lines, one build log per service | **Compiled and run** (Goose b781587, host shim); 3 deliberately not built |
| 5 Agent runtime | Lobster | identity, budget, memory, bus, audit, scheduler shims; durable audit log; board round trip | **9/9 self-tests green** (`lobster/run-tests.sh`) |
| 6 Shell and apps | Lobster | Spec only; today's desktop surfaces are HTML on the carrier | **Not built** |
| 7 Programs | JS / Python | Imperium, Scientia, Officina, Musica, Board | **Working** |
| — Rust crates | Rust | 20 service crates: supervisor, runtime, queue, guardrail, intel, relay | **20/20 build**, 1,899 tests green (`crates/PARITY.md`) |

Layer 4 compiled this round. Every service has a build log and a host run in
`services/BUILD_MATRIX.md`; the three that are not built (registry, devmgr, sockets) say so
because their logic lives in the supervisor, the device layer and the socket layer instead.
What is still missing is the last step, and it is the big one: **no Goose service has ever
been loaded by our kernel.** They run as host processes against a shim. That is K6's last
clause, and it is open.

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
| Capability policy: grant, deny (caps branch — not merged into this tree) | `os-build/logs/K6.1-cap-policy.txt` |
| Five userspace programs in ring 3 | `kernel/src/user.rs:19-27` (embedded) + `kernel/logs/E-boot-vnc.txt` (all five loaded) |
| Syscall refusals | `os-build/logs/K1-boot.txt` (`bad syscall 99 refused`) |
| Imperium pipeline end to end | `server/queue/` + `os-build/demo/EVAL4.md` |
| Agent loop, tools, budgets | `agents/agent_loop.mjs`, `agents/runtime.mjs`, `server/budget.mjs` |
| Layer model and status words | `os-build/LAYERS.md`, `os-build/KERNEL_STATUS.md` |

Reproduce any row with the command in `os-build/tools/`; `proof_boot.sh` runs the boot
checks, `verify_tree.sh` runs the repo gates.

---

## 5. Run the platform

```sh
git clone https://github.com/Mrfentmen/meta-os && cd meta-os
node server/server.mjs            # product API on :8080
open http://127.0.0.1:8080/imperium/      # Imperium, three divisions
open http://127.0.0.1:8080/surfaces.html  # every surface, with its status
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
3. **No service runs on the kernel.** Layer 4 compiles and runs on the host; the kernel has
   never loaded one. K6's last clause is open.
4. **Layer 6 does not exist.** The Lobster runtime is real and tested, but there is no shell:
   no compositor, no windowing, no native apps.
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
services/          Layer 4: Goose services and libraries (compiled; run on the host shim)
lobster/           Layer 5-6: runtime shims and contracts
crates/            Rust service crates (supervisor, runtime, queue, guardrail, intel)
agents/            agent loop, runtime, tools, providers
server/            product API, model client, queue, budget ledger
imperium/          the watch floor (Vigiles, Ignis, Medicus)
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
