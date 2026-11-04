# LAYERS TRUTH — measured audit, Lane A, 2026-11-04 (R5)

Method: every number below was produced by the command named with it, run in
`/Users/test/Desktop/meta-os` on branch `agent-r5`. Every status word uses the
`LAYERS.md:27-28` vocabulary (DESIGNED / WRITTEN / COMPILED / VERIFIED /
NOT BUILT / BLOCKED). COMPILED is claimed only with a build log path;
VERIFIED only with a QEMU/process log path. A claim without a path is deleted.

Reference checks: kernel excl-target = 16 `.rs` / 9794 lines (matches R5 brief
exactly, no discrepancy). services = 183 `.goose` / 40144 lines (brief said
184 / 40269: off by 1 file, ~125 lines — noted, not adopted). lobster =
11 `.lobster` / 145 lines (brief said 12 / 180 — noted, not adopted).
crates = 304 `.rs` / 102323 lines (matches).

## A1. One row per layer

| Layer | What exists | Files | Lines | Status | Evidence path | What is missing |
|---|---|---|---|---|---|---|
| 1 — Boot | `bootloader 0.9.35` dep pin + `kernel/build.rs`; hands machine to kernel in QEMU (`kernel/BUILD_LOG.md:1-8`) | 1 + dep pin (`kernel/Cargo.lock`) | n/a (external crate) | VERIFIED | `os-build/logs/K1-boot.txt:2` (`META OS KERNEL - alive (K1)`) | Bare-metal boot; UEFI/GOP path (see `os-build/KERNEL_FACE_TASKS.md:1-5`, target only) |
| 2 — Kernel core | `kernel/src/main.rs:1-535`, `memory.rs`, `mem.rs`, `sched.rs`, `tasks.rs`, `traps.rs`, `gdt.rs`, `user.rs` (`kernel/src/main.rs:67` wires `mod user`), `interrupts.rs` | 9 of 14 in `kernel/src/` | 5239 of 7988 (`wc -l kernel/src/*.rs`) | VERIFIED | `os-build/logs/K1-boot.txt:19-25` (K4), `:26-28` + `:54` (K5), `:33-34` + `:51` + `:53` (K6 behavior) | Goose-service load (K6 last clause, `os-build/KERNEL_SPEC.md:96-100`) |
| 3 — Drivers | `kernel/src/vga.rs:10` (`VGA_PHYS_ADDR 0xB8000`), `framebuffer.rs`, `icons.rs`, `logo_frames.rs` | 4 of 14 in `kernel/src/` (+ `syscalls.rs:1-484` retired, `os-build/KERNEL_SPEC.md:172-178`) | 2265 of 7988 | VERIFIED | `os-build/logs/K2-boot.png` + `K2-shell.png` (screendumps); `os-build/logs/K3-boot.txt:3` (timer), `:39` (scancode), `:54` (STATUS) | Graphics modesetting, PCI, storage, net, USB drivers (see A3) |
| 4 — System services (Goose) | 183 `.goose` incl. 88 in `services/tests/`; `services/MANIFEST.md:47-70` lists 24 services (21 WRITTEN, 3 NOT BUILT) + 12 libs WRITTEN | 183 (`find services -name '*.goose' \| wc -l`) | 40144 (`find services -name '*.goose' -exec cat {} + \| wc -l`) | WRITTEN (max); `registry`, `devmgr`, `sockets` NOT BUILT (`services/MANIFEST.md:53-62`; dirs hold zero `.goose`) | `services/BUILD.md:5` (toolchain NOT FOUND, so COMPILED impossible); `services/run-goose-tests.sh:6` (hardcoded absent `/Users/test/...` path, so RUNS not re-runnable here) | Any `.elf`; any service loaded by the kernel; K-ipc (`services/MANIFEST.md:38` shape OPEN) |
| 5 — Agent runtime (Lobster) | 11 `.lobster` demos (`lobster/agent-call.lobster:1-20` … `lobster/shim.lobster:1-13`); `lobster/README.md:1-9` states host-interpreter workflow | 11 (`find lobster -name '*.lobster'`) | 145 (`find lobster -name '*.lobster' -exec cat {} + \| wc -l`) | WRITTEN | `lobster/roundtrip.log:1-3` (host roundtrip text, not kernel); `lobster/host.log:1-4` (host stdin/stdout) | Enforcement in kernel; L5 gateway exists only as `agents/grants.mjs` (`os-build/KERNEL_SPEC.md:161-163`) |
| 6 — Shell and apps (Lobster) | Demos only (`lobster/homes/*/note.txt`, `bus-send`/`bus-recv` pattern); no home-surface program on the kernel | 0 shell sources; 4 home/bus data files | n/a | NOT BUILT (`os-build/LAYERS.md:35-36`: layer 6 spec-only until real OS state exists) | `ls lobster/homes lobster/*.lobster` (demos, not a shell) | Shell binary, app side, any OS state beyond host files |
| 7 — Programs | `server/*.mjs` (9 files), `agents/*.mjs`, `relay/relay.mjs`, `server/queue/*.py`; run on host + Debian carrier, never on our kernel (`os-build/KERNEL_SPEC.md:41-43`: programs are never the OS) | ~60+ host sources (count method: `find server agents relay -name '*.mjs' -o -name '*.py' \| wc -l`, re-run) | not counted (host scope, not OS layer) | VERIFIED (host) / NOT BUILT (on OS) | `os-build/face/provision.sh:232-303` (carrier runs python3 services); `os-build/image-status-2026-11-02.md:1-40` (carrier checks) | Any program as kernel-loaded ELF; any program calling our syscalls (`kernel/src/user.rs:1-637` table 0-6) |

## A2. K-milestones vs their named logs (all six opened)

- K1: `os-build/logs/K1-boot.txt:2` = `META OS KERNEL - alive (K1)` — PROVEN, holds.
- K2: no serial line by design (VGA text, not serial). Evidence is
  `os-build/logs/K2-boot.png` (+ `K2-shell.png`); `os-build/KERNEL_STATUS.md:12`
  records 196/2000 cells with glyphs (215 on shell screen). PROVEN-as-capture, holds.
  (`os-build/logs/K2-boot.txt` exists but is not the cited evidence.)
- K3: `os-build/logs/K3-boot.txt:3` = `K3 timer: 10 ticks after 407902 spins`;
  `:39` = `K3 keyboard: first scancode 0x000000000000001f`;
  `:54` = `STATUS tasks=7 ticks=169 heap_free_kb=287` — PROVEN, holds.
- K4: `os-build/logs/K1-boot.txt:19-25` = `mem frames: 61660 usable total` …
  `mem probe page ok` … `mem Box+Vec ok (box 42, vec sum 120)` …
  `mem stress 10k ok, heap free 511K` … `mem summary: K4 up` — PROVEN, holds.
- K5: `os-build/logs/K1-boot.txt:26-28` = `A / B / C sleeping 200 ticks` …
  `:54` = `C awake` — PROVEN, holds.
- K6: `os-build/logs/K1-boot.txt:33-34` = `HELLO FROM USERSPACE / user exit code 0`;
  `:51` = `user bad syscall 99 refused`;
  fault line = `INT user page-fault addr 0x… err 0x…0004: task killed` —
  behavior lines all present, BUT the last clause (Goose service loaded by
  kernel) has no line anywhere, and `os-build/KERNEL_SPEC.md:96-100` +
  `os-build/KERNEL_STATUS.md:47-49` both say NOT met.
  Verdict: PARTIALLY PROVEN (spec governs). No new downgrade for K1–K5.

## A3. What the kernel cannot do (from `kernel/src/` alone)

- No graphics modesetting — there is no `kernel/src/gop.rs`/`vesa.rs`; `framebuffer.rs` mirrors a BootInfo struct bootloader 0.9.35 never fills (`kernel/src/vga.rs:1-6`).
- No PCI enumeration — there is no `kernel/src/pci.rs` (`grep -ri pci kernel/src/` empty).
- No storage driver — there is no `kernel/src/virtio*.rs`/`ahci.rs`/`nvme.rs` (storage exists only as a Goose RAM contract, `services/MANIFEST.md:58` row 10).
- No network — there is no `kernel/src/net*.rs`/`e1000.rs` (netcfg/dhcp/dns/sockets are Goose text on K-ipc-OPEN, `services/MANIFEST.md:59-62` rows 13-16).
- No USB — there is no `kernel/src/usb.rs`/`xhci.rs` (`grep -ri usb kernel/src/` empty).

## A4. `services/MANIFEST.md` vs the `.goose` files

- Listed: 24 services (`services/MANIFEST.md:47-70`), 21 WRITTEN + 3 NOT BUILT
  (rows 7 `registry`, 9 `devmgr`, 16 `sockets`), plus 12 shared libs WRITTEN.
- `services/registry/`, `services/devmgr/`, `services/sockets/` contain zero
  `.goose`. `services/registry/README.md:1-5` and `services/devmgr/README.md:1-5`
  say NOT A SERVICE (logic lives in `services/supervisor/supervisor.goose` and
  `services/devices/devices.goose`); `services/sockets/README.md:1-8` says README
  ONLY (implementation is singular `services/socket/socket.goose`) and flags that
  MANIFEST row 16 still names `sockets` with no row for `socket` — a manifest edit
  owed, listed here for its owner, not made by this lane.
- Status-word violations: several service READMEs claim `RUNS`
  (audit, agenthost, shell, fs, socket, …). RUNS is not in the
  `os-build/LAYERS.md:27` vocabulary; on this machine it is unsupported twice
  over — `services/BUILD.md:5` (no Goose toolchain, so no COMPILED) and
  `services/run-goose-tests.sh:6` (runner hardcodes a path that does not exist
  here, so no re-runnable process log, so no VERIFIED). Honest word for all of
  them on this machine: WRITTEN.

## A5. `lobster/*.lobster` — what each proves, what it assumes

- `lobster/hello.lobster:1` — proves the interpreter runs a script. Assumes the
  lobster binary at `~/mcp-servers/toolchains/lobster-src/bin/` (absent here;
  `lobster/README.md:8`).
- `lobster/identity.lobster:1-23` — proves a script-level home-gate convention.
  Assumes enforcement by convention+review, not kernel (says so in comments).
- `lobster/memory.lobster:1-10` — proves file-backed note persistence across two
  runs. Assumes host FS is memory.
- `lobster/bus-send.lobster:1-7` + `bus-recv.lobster:1-9` — proves channel-dir
  message pattern. Assumes `bus/` dir relay (dev-carrier), not kernel IPC.
- `lobster/budget.lobster:1-27` — proves script-level spend cap + refusals
  record. Assumes cap in a script var; OS-level rule arrives with L5 runtime
  (says so in comments).
- `lobster/scheduled.lobster:1-14` — proves a busy-wait wake cycle. Assumes
  `seconds_elapsed()` + an external runner that kills it (no sleep builtin).
- `lobster/agent-call.lobster:1-20` — proves calling the Goose MCP host as a
  child process. Assumes goose binary at `/Users/test/...` (absent) + `req-*.json`
  workaround for brace-less literals.
- `lobster/service-roundtrip.lobster:1-17` — proves a Lobster→Goose echo
  roundtrip (`lobster/roundtrip.log:1-3`). Assumes the same absent goose binary.
- `lobster/shim.lobster:1-13` — proves driving a repo program from Lobster.
  Assumes a repo checkout present (falls back to `/tmp/os-build` path).
- `lobster/failures/identity-hash-comments.lobster` (+`.err`) — proves the
  broken-script museum. Assumes nothing (negative proof, keep it).

## A6. `crates/` vs the Node servers the image actually runs

Sample verified from lib.rs headers; pattern holds across batches B01–B23:

| Crate | Declared port source | Live counterpart | In image? |
|---|---|---|---|
| `crates/relay` (`crates/relay/src/lib.rs:1-8`) | `relay/relay.mjs` | yes, runs on host | NO — image runs python3 http + launcher/facts/ptyd/board/files/notesd (`os-build/face/provision.sh:232-303`) |
| `crates/queue-core`, `queue-store` | trio queue python (`server/queue/`) | yes, host | NO |
| `crates/agent-runtime`, `assess-server`, `guardrail` | `trio_agent.py`, `server/assess.mjs`, `spark_guardrail.py` | yes, host | NO |
| `crates/os-supervisor`, `os-worker`, `os-memory`, `os-identity`, `os-budget`, `os-jobs`, `os-workspace`, `os-misc`, `os-boot` | Milo batches B16–B23 over host python (`os/intel`, agents) | host scripts | NO |
| `crates/dashboard`, `intel`, `stack` | dashboard backend, `os/intel/`, `run-stack.sh` | host | NO |
| `crates/agent-ops` (header unverified) | none identified | none found — owner to confirm | NO |
| `crates/parity-tests` | test harness, no counterpart by design | n/a | NO |

Blanket finding: no build/provision script references `crates/` (A7 greps,
rc=1); the image installs `nodejs` + `python3-gi` (`os-build/iso/merge-layers.sh:70`)
and runs Node `.mjs` + Python3 — zero Rust crate artifacts ship.

## A7. Nothing from layers 1–6 reaches the image (strongest row)

Ran over `os-build/iso/merge-layers.sh`, `build_iso.sh`,
`finalize-iso-tree.sh`, `os-build/face/provision.sh`:

- `grep -rni "goose|\.goose" <scripts>` → empty, rc=1.
- `grep -rni "lobster|\.lobster" <scripts>` → empty, rc=1.
- `grep -rni "crates/|cargo|rustc|bootimage-metaos" <scripts>` → empty, rc=1.
- `grep -rni "kernel" <scripts>` → one hit ONLY:
  `os-build/iso/merge-layers.sh:126-158`, the kernel-module transplant that copies
  the **Ubuntu base's own** `lib/modules`/`usr/lib/modules` so the rebuilt initrd
  matches the base kernel. That is the distro's kernel, not ours — evidence
  against, not for. Our bytes in the image: payload theme + face only (A8).

## A8. Image quantification (re-runnable)

- Base: `/tmp/xubuntu-base.iso` = 5,211,408,384 bytes
  (`stat -f "%z %N" /tmp/xubuntu-base.iso`; `ls -la` agrees; ≈4.9 GiB).
  Identity pinned in `os-build/iso/BASE_FACTS.md:1-12` (Xubuntu 24.04.5, sha256 match).
- Our payload: `os-build/iso/payload-theme` = 14,424 KiB (`du -sk`),
  `os-build/face` = 3,544 KiB (`du -sk`) — re-run: `du -sk <dir>`.
- Combined: 17,968 KiB = 18,399,232 bytes ≈ **0.35%** of the base
  (`python3 -c "print(17968*1024/5211408384*100)"` → 0.353).
- Restated: kernel/initrd/casper/systemd/X11/XFCE/GTK3/plank/WebKitGTK are the
  base distro's (`os-build/iso/merge-layers.sh:70-76`); we add theme + services.

## A9. Is Meta OS built out of Goose, Lobster and Rust?

No. The Rust kernel (layers 1–3) is VERIFIED in QEMU but boots only our
`bootimage-metaos-kernel.bin`, never the shipped image; the 183 Goose services
(layer 4) are WRITTEN text with no toolchain and no kernel-loaded process; the
Lobster scripts (layers 5–6) are WRITTEN host-interpreter demos with no
kernel enforcement; and the shipped image is a Meta-branded Xubuntu carrier
(99.65% base distro) running Node and Python3 programs. Goose, Lobster and the
kernel are real work that does not yet touch the product.

## A10. Gate (BLOCKED, not invented)

`sh os-build/tools/verify_tree.sh` → `No such file or directory`, rc=127.
The R5-brief note is confirmed: the tool is MISSING in this tree. Recorded as
BLOCKED/gate-fail. Nothing was invented to stand in for it.

## A11. Gaps for lanes B–G (one line each, lane owners fill in)

1. Lane owning boot/Mac proof: reproduce `kernel/BUILD_LOG.md` + QEMU logs from a
   clean checkout with one command; `os-build/gate.sh` is the candidate, unrun here.
2. Lane owning drivers: GOP/pixel framebuffer route decision
   (`os-build/KERNEL_FACE_TASKS.md:A1-A4`) — VGA text at `0xB8000` cannot do graphics.
3. Lane owning Goose: first COMPILED service needs a real toolchain + build log
   (`services/BUILD.md` recipe unexecuted) and a kernel-loaded ELF (K6 last clause).
4. Lane owning Lobster runtime: move one gate (home, spend, or bus) from script
   convention into kernel mediation with a serial-log proof line.
5. Lane owning shell/face: a shell that runs on our kernel (today the face runs on
   the carrier via `os-build/face/provision.sh:232-303`); keep `os-build/DEMO.md:75`
   honesty line while doing it.
6. Lane owning programs-as-ELFs: first program loaded by the kernel through
   `kernel/src/user.rs` syscall table 0–6 with `user exit code 0` in serial.
7. Lane owning `services/MANIFEST.md`: fix row 16 (`sockets`→`socket`) and replace
   every re-unverifiable RUNS with WRITTEN (flagged by `services/sockets/README.md`).

## A12. Stale claims for lane H (cross-checked 2026-11-04)

- `os-build/LAYERS.md:30-38` (state 2026-11-01: K1 UNCOMPILED, K2–K6 BLOCKED,
  layer 4 DESIGNED/NOT BUILT) — superseded by 2026-11-02 QEMU proofs; keep as
  dated history, add pointer here.
- `os-build/KERNEL_STATUS.md:16` marks K6 PROVEN while `:47-49` and
  `os-build/KERNEL_SPEC.md:96-100` say the Goose clause is NOT met — status row
  overclaims against its own next section; use PARTIALLY PROVEN.
- `os-build/KERNEL_SPEC.md:128-129` (syscall 5 falls in refusal until RW4-1
  lands) vs `os-build/logs/K6.1-cap-policy.txt:56-58` (`readkey: polling syscall
  5`, `readkey: empty`) — check `kernel/src/user.rs` whether RW4-1 landed.
- `README.md:240` (~5,800 lines across 13 files) vs measured `kernel/src/` 7988
  lines / 14 files (16 / 9794 incl. `build.rs` + `r5-reference`) — stale.
- `README.md:247` (19 crates) vs measured 20 dirs in `crates/` — stale.
- `services/MANIFEST.md:26-31` (nothing above WRITTEN; K2+ unproven; K1 skeleton)
  — dated 2026-11-01 snapshot; kernel half is superseded, Goose half still true.

## A13. Documents that call the carrier "the OS"

- `os-build/DEMO.md:51` ("This is Meta OS 1.0 … It boots from a single image")
  + `:130` ("The agent relay runs in the OS, not on my laptop") — the image is
  Xubuntu-based and the relay runs in the Debian VM; `:75` + `:155-157` say the
  base is Debian honestly, so the doc is mixed, not false throughout.
- `os-build/KERNEL_FACE_TASKS.md:1-5` ("the OS boots into Meta OS … our kernel
  boots, and Meta OS appears") — task target phrased as present; aspirational.
- `README.md:236-243` ("Underneath them sits a real operating system" adjacent to
  program descriptions) — risks conflation; the one-sentence kernel claim itself
  is log-backed and fine.

## A14. `docs/AGENTIC.md` / proof-pack numbers

- `docs/AGENTIC.md` describes Layer-7 host programs (Trio/queue/relay); this audit
  changes none of its numbers (no tests run, host scope untouched). Lane H: keep it
  scoped to programs, it neither supports nor contradicts layers 1–6.
- `docs/AGENT_PROOF.md` does not exist at that path (this tree: `find` empty);
  the proof pack is `os-build/AGENTIC_PROOF.md`, whose platform-level PROVEN items
  explicitly exclude in-kernel agents ("No agent runs inside the bare-metal
  kernel") — consistent with this audit, no change.

## A15. Five claims a judge could falsify in two minutes (honest replacements)

1. "K6 PROVEN" (`os-build/KERNEL_STATUS.md:16`) — open `:47-49` + spec `:96-100`:
   no Goose service loaded. Say PARTIALLY PROVEN (all behavior lines present,
   Goose clause open).
2. Service READMEs claiming "RUNS" — `grep -rh "Status:" services/*/README.md`;
   `services/BUILD.md:5` (no toolchain) + `run-goose-tests.sh:6` (dead path). Say
   WRITTEN (host-run corpus 2026-11-02, not re-runnable here).
3. "5,800 lines across 13 files" (`README.md:240`) — `wc -l kernel/src/*.rs`.
   Say 7,988 lines across 14 files in `kernel/src/` (16 / 9,794 incl. build files).
4. "19 crates" (`README.md:247`) — `ls crates | wc -l`. Say 20 directories.
5. "This is Meta OS 1.0, it boots from a single image" (`os-build/DEMO.md:51`) —
   boot it, `uname -a`, inspect `/boot`: Ubuntu kernel + Xfce, no metaos kernel.
   Say Meta-branded Xubuntu carrier; our kernel boots separately in QEMU
   (`os-build/logs/K1-boot.txt:2`).
