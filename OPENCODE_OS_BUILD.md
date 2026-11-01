# OPENCODE OS BUILD — the giant list

Boss's order, 2026-11-01: build the operating system. Now. The boss is
going to sleep; this file is the work until he wakes and after.

READ FIRST: `KERNEL_SPEC.md` at the repo root. It is the law for this
build. Short version: Meta OS is a layered operating system with its
OWN kernel. Layer 0 kernel in Rust (`kernel/`). Layer 1 system
services in Goose. Layer 2 agent and app layer in Lobster. The OS is
built for agents and for users. Everything else in this repo is
programs. Programs are not the OS.

## How we build it: reverse engineer Linux, then beat it

The boss's method, his words: reverse engineer the Linux thing and
make it better, improve it where it lacks. In practice:

- Study Debian's structure (Section G) and other systems (Section H)
  until each piece is understood well enough to describe its behavior
  in plain writing. That description is the spec. Then write OURS.
- NEVER paste code out of the Linux kernel or any GPL source into our
  kernel. Learn from it, describe it, write it fresh. License hygiene
  is a hard gate (Section P).
- Where Debian lacks for agents, that gap is our improvement list
  (Section I). Debian has no agent identity, no agent memory, no MCP
  wiring, no tool registry, no deterministic records. Our OS does.
- A Linux OS is an OS plus tons of pre installed tools. Ours ships
  the tools too (Section J). Manifest first, install script second,
  every tool verified running.

## Rules of this build

- Work on branch `opencode/os-build`. Small commits, one step each.
  Mac compile errors are the next task, ahead of new features.
- PROOF STANDARD: a kernel claim is true only with a QEMU boot log
  from OUR kernel binary showing it. Capture every boot log into
  `os-build/logs/` with the milestone in the file name.
- Never claim compiled, booted, or working without the log or the
  test output in the report. The running report is
  `os-build/OS_BUILD_REPORT.md`, updated per section, never skipped.
- MCPs: connect to whatever helps you code in Rust, Goose, and
  Lobster (Section M). The Rust docs MCP pattern already exists in
  this project (rustdocs). For Goose and Lobster, find the docs and
  tooling, wire what exists, and write down what does not exist yet
  instead of pretending.
- NO MOCKS, boss's order 2026-11-01: nothing fake ships in this OS.
  No mocked networks or services, no fixture data in any shipped
  surface, no stub or skeleton presented as working. Test data
  lives inside tests only, is named as test data, and never ships.
  A component that is not real yet is NOT BUILT in the report.
  An honest empty state beats invented data, every time.
- Protected: do not edit the crew's merged program code (server/,
  js/, os/worlds/, crates/) from this file. Your ground is kernel/,
  services/, lobster/, os-build/, and docs you create there.
- The cybersecurity program is PARKED by the boss's order. Do not
  start it. It begins only when the OS is done and he says so.

## Section A — K1 boot proof (OS-001..OS-012)

- OS-001: Pull main. Read KERNEL_SPEC.md end to end. Write the
  one paragraph version of it at the top of OS_BUILD_REPORT.md.
- OS-002: Set up the Mac toolchain for kernel/: rustup target
  x86_64-unknown-none, cargo bootimage installed. Record versions.
- OS-003: Build kernel/ as written. First error list goes in the
  report verbatim, before any fix.
- OS-004: Fix build errors in the smallest commits possible, one
  error class per commit.
- OS-005: Produce the bootable image with cargo bootimage. Record
  the image path and size.
- OS-006: Boot it in QEMU with serial output captured to a file.
- OS-007: The capture must contain the line META OS KERNEL - alive
  (K1). Save it as os-build/logs/K1-boot.txt. If it does not, that
  failure is the report.
- OS-008: Boot it 3 times. All 3 logs identical in the alive line.
- OS-009: Write the K1 section of the report: what built, what
  booted, the log file names, what is still unproven.
- OS-010: Check the kernel image size and record it; note the
  bootloader version actually used.
- OS-011: If any step above is blocked, write the blocker in the
  report with the exact error, and move to Section G (research
  needs no compiler). Never sit idle on a blocker.
- OS-012: Section A summary into the report.

## Section B — K2 framebuffer console (OS-013..OS-028)

- OS-013: Read the bootloader crate's framebuffer documentation for
  the exact version in the lockfile. Write the API notes into
  os-build/research/framebuffer.md before touching code.
- OS-014: Take the framebuffer from BootInfo in kernel_main.
- OS-015: Clear the screen to a dark background color. Boot proof.
- OS-016: Draw one pixel grid test pattern. Boot proof screenshot
  via QEMU monitor or serial state note.
- OS-017: Embed a small bitmap font (public domain or own drawn,
  license noted in the file header).
- OS-018: Render the text META OS on the framebuffer.
- OS-019: Build a console writer: position, newline, scroll.
- OS-020: Print the boot banner: META OS, milestone, alive line,
  on screen and serial both.
- OS-021: Add a print macro so kernel code writes to both outputs.
- OS-022: Panic handler draws PANIC on screen in a bright color
  plus the serial line.
- OS-023: Boot proof: os-build/logs/K2-boot.txt plus a framebuffer
  capture file.
- OS-024: Test: force a panic in a test build, confirm the panic
  screen appears, then remove the forced panic.
- OS-025: Record framebuffer resolution and pixel format from
  BootInfo in the report.
- OS-026: Note every unsafe block added this section, one line each,
  in os-build/research/unsafe-ledger.md (start the ledger here).
- OS-027: If the framebuffer is unavailable under QEMU, log the
  exact behavior and fall back to serial only, in writing.
- OS-028: Section B summary into the report.

## Section C — K3 interrupts, timer, keyboard (OS-029..OS-044)

- OS-029: Build the interrupt descriptor table with a breakpoint
  handler that prints on serial and screen.
- OS-030: Trigger int3 in a test path; proof is the handler output
  in the boot log.
- OS-031: Add a double fault handler on its own stack (TSS + IST).
- OS-032: Initialise the PIC, remap offsets, mask everything except
  timer and keyboard.
- OS-033: Timer interrupt handler increments a tick counter.
- OS-034: Print uptime ticks once per second on the console.
- OS-035: Keyboard interrupt handler reads scancodes into a buffer.
- OS-036: Decode scancodes to characters for letters and digits.
- OS-037: Echo typed characters to the console.
- OS-038: Boot proof: os-build/logs/K3-boot.txt shows ticks and a
  typed line, driven by QEMU sendkey or a scripted key feed.
- OS-039: Add the hardware interrupt exit path correctly (EOI) and
  prove 60 seconds of ticks with no stall.
- OS-040: Page fault handler prints fault address and error code,
  then halts. Proof via a deliberate bad access in a test build.
- OS-041: Update the unsafe ledger for this section.
- OS-042: Write os-build/research/interrupts.md: the map of vectors
  we own so far.
- OS-043: If sendkey scripting fails, document the manual QEMU
  monitor steps instead, exactly.
- OS-044: Section C summary into the report.

## Section D — K4 memory, paging, heap (OS-045..OS-060)

- OS-045: Take the physical memory map from BootInfo; print region
  counts by kind on serial.
- OS-046: Build a frame allocator over usable regions.
- OS-047: Build the page table mapper on the bootloader's offset.
- OS-048: Map one new page manually; write and read it back; proof
  line in the log.
- OS-049: Bring up a kernel heap (fixed block or linked list
  allocator, own code or a permissive crate, license noted).
- OS-050: Enable the alloc crate; prove a Box and a Vec work.
- OS-051: Heap stress: allocate and free in a loop 10,000 times;
  proof line with final heap stats.
- OS-052: Guard page test: allocation past the heap faults into the
  K3 page fault handler.
- OS-053: Print a memory summary on the console at boot: total,
  usable, heap size.
- OS-054: Write os-build/research/memory-map.md from the real
  BootInfo data of the test machine.
- OS-055: Update the unsafe ledger.
- OS-056: Boot proof: os-build/logs/K4-boot.txt with the memory
  summary and stress result.
- OS-057: Record allocator choice and why, in the research file.
- OS-058: Remove any test only code paths from the boot path; keep
  them behind a feature flag.
- OS-059: Re-run K1 to K3 proofs after the memory work; all logs
  refreshed, no regressions hidden.
- OS-060: Section D summary into the report.

## Section E — K5 tasks and scheduling (OS-061..OS-074)

- OS-061: Design note first: os-build/research/scheduler.md, one
  page, cooperative round robin to start, why.
- OS-062: Define the task structure: id, stack, state.
- OS-063: Allocate per task stacks from the heap.
- OS-064: Write the context switch in assembly (own file, commented
  register by register).
- OS-065: Spawn two kernel tasks printing A and B alternately.
- OS-066: Proof: boot log shows interleaved A and B lines.
- OS-067: Add a sleep(ticks) using the K3 timer.
- OS-068: Task C sleeps and wakes on schedule in the same log.
- OS-069: Add task exit; a finished task is removed, others run on.
- OS-070: Console task: the keyboard echo from K3 becomes its own
  task.
- OS-071: Boot proof: os-build/logs/K5-boot.txt.
- OS-072: Update the unsafe ledger (the switch is the big entry;
  justify every line).
- OS-073: Write the failure note: what this scheduler cannot do yet
  (preemption, priorities), in the research file, honestly.
- OS-074: Section E summary into the report.

## Section F — K6 syscalls and first userspace (OS-075..OS-088)

- OS-075: Design note: os-build/research/syscalls.md, the first
  five syscalls only (write, exit, sleep, getpid, yield), numbers
  and calling convention.
- OS-076: Enter userspace: build the ring transition with a test
  program.
- OS-077: The test program is a static binary built in this repo
  under os-build/userspace/hello/ (Rust, no_std, own entry).
- OS-078: Load it as an ELF: write the minimal ELF loader, segment
  mapping only.
- OS-079: syscall instruction path wired (or int 0x80 if simpler;
  record the choice and why).
- OS-080: Userspace write syscall prints HELLO FROM USERSPACE via
  the kernel console.
- OS-081: Userspace exit syscall returns control; kernel logs it.
- OS-082: Boot proof: os-build/logs/K6-boot.txt contains the
  userspace line.
- OS-083: A second userspace program that sleeps and prints again,
  proving sleep across the boundary.
- OS-084: Bad syscall number from userspace is refused and logged,
  no crash.
- OS-085: Userspace bad memory access faults in its own context;
  kernel survives, logs, continues.
- OS-086: Update the unsafe ledger.
- OS-087: Write the K6 gate list: which of the five syscalls are
  proven, which are not, in the report. No rounding up.
- OS-088: Section F summary into the report.

## Section G — Debian reverse engineering audit (OS-089..OS-104)

- OS-089: Map the Debian boot chain end to end (firmware to login)
  in os-build/research/debian-bootchain.md, from the actual image
  in this project and package docs.
- OS-090: Map the init and service model: what starts, in what
  order, who supervises restarts.
- OS-091: Map the package system: what a package is, how install
  and remove really work, where the state lives.
- OS-092: Map the filesystem layout: every top level directory,
  what it is for, what breaks if it moves.
- OS-093: Map users and permissions: the model, the files, the
  failure modes.
- OS-094: Map networking bring up: interfaces, DNS, time sync.
- OS-095: Map logging: where logs live, rotation, what is lost on
  crash.
- OS-096: Map updates: how the system updates itself, what can go
  wrong mid update.
- OS-097: List Debian's 20 roughest edges for a machine that hosts
  agents, each with the evidence (a doc, a config, a behavior).
- OS-098: For each rough edge: our OS does what instead, one line.
- OS-099: Inventory what the current Meta OS image actually uses
  from Debian (packages, services), the keep list.
- OS-100: The replace list: which of those our own layers already
  cover, which they do not.
- OS-101: Write the clean room rule card into
  os-build/research/clean-room.md: study, describe, write fresh,
  never paste.
- OS-102: Check 5 behavior descriptions from OS-089..096 against a
  second source each; correct the files.
- OS-103: Summarise the audit in the report: the 10 findings that
  most change our build.
- OS-104: Section G summary into the report.

## Section H — Other systems audit (OS-105..OS-118)

- OS-105: NixOS: the declarative model. What it does better, what
  it costs. One page in os-build/research/others/.
- OS-106: Arch: the simple base plus assemble it yourself model.
- OS-107: Alpine: the small musl based model, why it boots fast.
- OS-108: SteamOS: an appliance OS that games boot straight into.
- OS-109: ChromeOS: a browser as the whole surface, the update
  model (A/B partitions).
- OS-110: Redox OS: a Rust microkernel, real, years in. What its
  structure teaches our kernel.
- OS-111: SerenityOS: a from scratch system built by a community,
  what steady milestones look like.
- OS-112: Haiku: a single purpose revival OS, the focus lesson.
- OS-113: For each system above: one borrowable idea, its license
  position, and whether we take it, in the file.
- OS-114: The A/B update idea: full design note for our updater,
  whichever system inspired it.
- OS-115: The appliance idea: what Meta OS boots straight into, one
  page, in agent terms as well as user terms.
- OS-116: Rank the borrowed ideas by value to an agent first OS.
- OS-117: Anything GPL contaminated gets marked in red in the
  files: idea fine, code never.
- OS-118: Section H summary into the report.

## Section I — Where Debian lacks for agents: the improvement list (OS-119..OS-132)

- OS-119: Agent identity: design note. An agent is a citizen with
  a name, a key, a home. Debian has users; we need both.
- OS-120: Agent memory: where an agent's long term memory lives on
  disk, its format, who may read it.
- OS-121: Agent tools: the tool registry design. How an agent
  finds, trusts, and calls a tool.
- OS-122: MCP host: the OS speaks MCP natively. Design note: where
  the host lives (Goose services layer), what it serves.
- OS-123: The bus: agents talk on a message bus. Design note from
  the crew's working relay experience in this repo.
- OS-124: Deterministic records: everything an agent does is
  written in an append only record a user can audit. Design note.
- OS-125: Attention: how the OS wakes an agent (events, timers,
  messages) and how it lets one sleep. Design note.
- OS-126: Budgets: an agent's spend and compute limits as an OS
  level rule, not an app promise. Design note.
- OS-127: Sandboxing between agents: what one agent may never see
  of another's home. Design note.
- OS-128: The user side of each note OS-119..127: what the human
  sees and controls, one paragraph each, in the same files.
- OS-129: Pick the first three gaps to build right after K6 and
  write why those three, in the report.
- OS-130: Draw the layer map: kernel, Goose services, Lobster
  layer, programs, with every design note placed on it. One file,
  os-build/research/layer-map.md.
- OS-131: Check the map against KERNEL_SPEC.md line by line; fix
  any drift in the notes, never in the spec.
- OS-132: Section I summary into the report.

## Section J — The tools manifest (OS-133..OS-152)

- OS-133: Start os-build/TOOLS_MANIFEST.md: categories first
  (languages, compilers, editors, networking, disks, media,
  security research, agent tooling, debugging).
- OS-134: Languages and runtimes: Rust toolchain, Goose toolchain
  (as available), Lobster interpreter, Python, Node. Each with the
  install source.
- OS-135: Build tools: compilers, linkers, make, cmake, git, the
  QEMU set.
- OS-136: Networking: curl, wget, dig, nmap class tools, ssh set.
- OS-137: Disk and system: partition, filesystem, archive, and
  recovery tools.
- OS-138: Media: ffmpeg and image tools (the demo work needs them).
- OS-139: Text and data: jq, ripgrep, sqlite, hex editors.
- OS-140: Agent tooling: the MCP servers wired in Section M, the
  crew bus tools, the records tools.
- OS-141: For every tool: name, version source, license, size.
  No license line, not on the manifest.
- OS-142: Write the install script os-build/install-tools.sh for
  the dev carrier image: manifest in, installed system out.
- OS-143: Run it on a throwaway image copy. Log every failure.
- OS-144: Fix the script until a clean run exists; the clean run
  log goes in os-build/logs/.
- OS-145: Verify 10 tools from the manifest actually run, with the
  commands and outputs in the report.
- OS-146: Total size of the installed toolset; record it.
- OS-147: The trim pass: anything installed but never used by any
  lane gets a cut or keep line with a reason.
- OS-148: The same manifest, second view: which tools the KERNEL
  image itself will eventually carry natively (post K6), marked.
- OS-149: Prerequisites list: what a fresh machine needs before
  any of this installs, in order.
- OS-150: The manifest is a living file: add the update rule at
  its top (who adds, what proof a new tool needs).
- OS-151: One page summary of the toolset in the report.
- OS-152: Section J summary into the report.

## Section K — Goose services layer (OS-153..OS-166)

- OS-153: Research first: what the Goose language's toolchain is,
  where it lives, how a program builds and runs. Findings, with
  sources, in os-build/research/goose.md. If the toolchain is
  thin, say exactly how thin.
- OS-154: Install the Goose toolchain on the Mac. Record versions
  and the exact steps.
- OS-155: Hello service: a Goose program that prints and exits.
  Build log in the report.
- OS-156: The smallest real Goose daemon: starts, writes a heartbeat line
  to a file every second, stops cleanly on signal.
- OS-157: The supervisor contract: who starts services, who
  restarts them, where their records live. Design note.
- OS-158: The IPC contract between the Goose layer and the kernel:
  messages, errors, timeouts. Design note tied to Section F
  syscalls.
- OS-159: A Goose echo service over that contract (against the
  dev carrier first, the real kernel when K6 lands).
- OS-160: Service records: every start, stop, and crash lands in
  the append only record format from OS-124.
- OS-161: Failure drill: kill the daemon mid run; the supervisor's
  behavior is logged and matches the contract, or the contract is
  corrected.
- OS-162: The updater service in Goose: checks, stages, and the
  A/B rule from OS-114. The network check is real, against a real
  endpoint. Where no real endpoint exists yet, that part is
  NOT BUILT, never mocked.
- OS-163: The MCP host in Goose, smallest real version: starts, lists one tool,
  answers one call, all logged.
- OS-164: Tests for OS-156, OS-159, OS-163 in Goose's own test way,
  or a runner script if the language lacks one (state which).
- OS-165: Put the layer's files under services/ in this repo, one
  service per folder, each with a README line.
- OS-166: Section K summary into the report, including every place
  Goose tooling forced a workaround.

## Section L — Lobster agent layer (OS-167..OS-180)

- OS-167: Research: the Lobster language (lobster.dev): what it
  is, its interpreter, its embedding story. Sources in
  os-build/research/lobster.md.
- OS-168: Install the Lobster interpreter on the Mac. Record it.
- OS-169: Hello agent: a Lobster script that prints and exits,
  run through the interpreter. Log in the report.
- OS-170: An agent script that calls one MCP tool from OS-163 and
  prints the result.
- OS-171: Agent identity in Lobster: a script that knows its name,
  reads its own home folder, and no other agent's.
- OS-172: Agent memory in Lobster: write a note, exit, run again,
  read the note back. Proof in the log.
- OS-173: The bus in Lobster: two scripts exchange one message on
  the crew bus pattern (dev carrier relay), logged both sides.
- OS-174: A scheduled agent: wakes on a timer, does OS-172's read,
  sleeps. One full cycle logged.
- OS-175: Budget rule enforced: an agent that tries to spend past
  its cap is refused by the layer, and the refusal is recorded.
- OS-176: The first PROGRAM shim: one existing repo program (the
  crew records reader) driven from a Lobster script end to end.
- OS-177: Failure museum for this layer: every broken script kept
  with its error, in lobster/failures/.
- OS-178: Put the layer's files under lobster/ in this repo.
- OS-179: A one page guide: writing an agent for Meta OS, from
  OS-169..176, in lobster/README.md.
- OS-180: Section L summary into the report.

## Section M — MCP wiring for coding (OS-181..OS-192)

- OS-181: Inventory: which MCP servers exist for Rust development
  (docs, crates, diagnostics). Verify each by opening its page.
- OS-182: Wire the Rust docs MCP the way this project already does
  (rustdocs pattern) into the OpenCode config; smoke call logged.
- OS-183: Find Goose language help: docs MCP if one exists, else
  the best docs source, wired as a local skill note with a smoke
  check. State plainly which case it is.
- OS-184: Same for Lobster: MCP if one exists, else docs source
  plus local notes. State which case.
- OS-185: A filesystem and git MCP for the build itself, if not
  already wired; smoke call each.
- OS-186: Write os-build/mcp/WIRING.md: every wired MCP, what it
  is for, its license, its smoke result.
- OS-187: The rule card: keyless first, secrets never in files,
  every wiring proven by a call, in WIRING.md.
- OS-188: Test that a kernel coding task goes measurably better
  with the docs MCP: one API looked up, cited in the commit.
- OS-189: If the local MCP gateway is down, note it in WIRING.md
  with the restart pointer; do not rebuild it from this file.
- OS-190: A crew facing summary of this section posted in the
  report (the crew wires the same way in their own lanes).
- OS-191: Re-run every smoke call at the end of the build; all
  green or the failures are listed, not hidden.
- OS-192: Section M summary into the report.

## Section N — Boot and test pipeline (OS-193..OS-204)

- OS-193: One script, os-build/boot-test.sh: build, boot in QEMU,
  capture serial, grep the expected lines, print PASS or FAIL per
  milestone.
- OS-194: The expected lines file per milestone (K1..K6), in
  os-build/expected/.
- OS-195: The script fails loudly on a missing line; prove it by
  removing one line and watching it fail.
- OS-196: Screenshot capture for the framebuffer milestones via
  the QEMU monitor, saved beside the serial log.
- OS-197: A clean checkout drill: fresh clone, run the pipeline,
  record how long green takes.
- OS-198: The pipeline runs the userspace proofs from Section F.
- OS-199: Nightly shape: the pipeline as one command the boss can
  run, documented in os-build/README.md.
- OS-200: Flake log: every intermittent failure, dated, in
  os-build/logs/flakes.md. Zero entries is a claim that needs the
  runs to back it.
- OS-201: The pipeline covers the Goose services tests (OS-164).
- OS-202: The pipeline covers the Lobster agent proofs (Section L
  logs checked, not just produced).
- OS-203: Pipeline output goes into the report verbatim for the
  final run of the build.
- OS-204: Section N summary into the report.

## Section O — The shell: what a user and an agent see (OS-205..OS-216)

- OS-205: Design note: the boot screen. Meta OS banner, milestone,
  memory, tasks, one line each. For eyes and for agents (a machine
  readable version of the same facts).
- OS-206: Implement the banner on the K2 console.
- OS-207: A status command in the console: tasks, ticks, heap.
- OS-208: The agent view: the same status as a structured record
  on the serial port, parseable. Format note in the research file.
- OS-209: A help command listing what the shell can do today. Only
  real commands listed.
- OS-210: Every shell command gets a boot log proof line.
- OS-211: The shell survives bad input: unknown command, long
  line, empty line, each logged as handled.
- OS-212: Colors and layout pass: the console looks deliberate,
  screenshot in the logs.
- OS-213: The user's first minute: a scripted walkthrough of what
  a person sees from power to prompt, in os-build/research/.
- OS-214: The agent's first minute: the same, from the structured
  side.
- OS-215: Anything in the walkthroughs that is not real yet is
  marked NOT BUILT in the file, in those words.
- OS-216: Section O summary into the report.

## Section P — License and honesty gates (OS-217..OS-228)

- OS-217: License audit: every crate, tool, font, and borrowed
  idea in the build, one table, os-build/LICENSE_AUDIT.md.
- OS-218: Any GPL code dependency in the kernel itself: zero, or
  it is removed and the removal is in the report.
- OS-219: The clean room check: grep the kernel for any comment or
  identifier that only makes sense copied from Linux source; each
  hit explained or removed.
- OS-220: Claims audit: every claim in OS_BUILD_REPORT.md traced
  to a log or a test output. Untraceable claims are cut.
- OS-221: The word OS is used only for the layered system in all
  new docs from this build. Programs called programs.
- OS-222: KERNEL_SPEC.md re-read; every rule in it checked against
  the build; drifts listed in the report.
- OS-223: The boss's parked list respected: the cybersecurity
  program untouched, named in the report as parked, once.
- OS-224: Unsafe ledger complete: every unsafe block in the kernel
  has its one line justification.
- OS-225: Secrets sweep on everything this build created: counts
  only, zero real secrets, or the build stops and reports.
- OS-226: The report's final honesty block: what is proven, what
  is written but unproven, what is not started. Three lists, no
  blending.
- OS-227: Fresh reader test: follow os-build/README.md from a
  clean clone; every stumble logged and fixed in the docs.
- OS-228: Section P summary into the report.

## Section Q — Endurance and hand back (OS-229..OS-240)

- OS-229: Full rebuild from scratch: clean clone, toolchain,
  kernel, services, agent layer, pipeline green, timed.
- OS-230: The 1 hour soak: the kernel boots and runs its tasks for
  one hour in QEMU; log tail and tick count in the report.
- OS-231: Reboot loop: 10 boots, 10 alive lines, no variance
  unexplained.
- OS-232: Every milestone log K1..K6 (or the honest subset) in
  os-build/logs/, named and dated.
- OS-233: OS_BUILD_REPORT.md finished: per section summaries, the
  honesty block from OS-226, the pipeline output from OS-203.
- OS-234: A short brief for the boss at the top of the report:
  where the OS stands, in plain words, no jargon, 10 lines max.
- OS-235: Next steps list: the following 20 tasks beyond this
  file, written from what the build learned, appended to the
  report (the build feeds its own future).
- OS-236: Commit and push everything on opencode/os-build in
  small clean commits; nothing left only on the Mac.
- OS-237: Verify the branch from a second clean clone: files
  present, pipeline runs, report readable.
- OS-238: If any milestone is still unproven, the brief says which
  and why, in its first 10 lines. No burying it.
- OS-239: Hand back: the report is the deliverable. Post the brief
  to the crew bus when the boss wakes, not before.
- OS-240: STOP at the end of this file. Do not start the parked
  cybersecurity program. Do not start a new file. The boss reads
  the report first.
