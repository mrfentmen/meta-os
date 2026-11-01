# BUFFY — Layer 4 work order: Goose system services

Renumbered 2026-11-01 ~09:02 on the boss's word: the OS has SEVEN layers (see `os-build/LAYERS.md`). File name, task IDs, branch names, and folder paths keep the old digits as stable identifiers; only the layer numbers in the text changed.

From the boss's order 2026-11-01 (~08:18): the OS build goes parallel
by layer. **Your layer is Layer 4 — the Goose system services.** Pax is
your pairing on this layer (service shape, coordination, and the
merge). Rowan + OpenCode hold Layers 1–3 (boot, Rust kernel core,
drivers), Milo holds Layer 5 (agent runtime), Hana Layer 6 (shell
and apps), and the programs sit at Layer 7. Work in your own branch; **Pax merges
when you are done — do not merge your own branch** (boss's merge rule).

Branch: `buffy/layer1-goose-services` in `mrfentmen/meta-os`.

**COMMIT RULE (boss's word 2026-11-01 ~09:12): commit ONLY to your
branch, `buffy/layer1-goose-services`. Never commit to main, never
merge anything yourself. Pax merges the branch when you post it
ready. One task, one commit.**

**HOW TO WORK THIS LIST (boss's word, same order): set B-L1-01 through
B-L1-78 as your own to-dos and work them in order, autonomously. Each
task is a real chunk — a service, a library, a test program — not a
line edit. When a task's status word cannot honestly rise, finish it
at the honest word and move on; never stall the queue on one task.**
Report to crew room 1 at every stage boundary.

## What Layer 4 is

Meta OS has its own kernel (Layers 1–3, Rust, `kernel/`). Layer 4 is the
system services that run on it, written in **Goose** — a real language
by Wouter van Oortmerssen (github.com/aardappel/goose, Apache-2.0):
memory-safe, no heap, no GC, compiles to C. These services are part of
the OS itself. Imperium, Custos, Musica, the science lab and
everything under `os/worlds/` are PROGRAMS that will run on the OS —
they are not your layer and not the OS.

The Debian image is a development carrier only. **Do not build out
the Debian.** Nothing in this order touches it.

## Your tools — new, use them

The boss just published MCP servers for both languages and Pax wired
them into the local gateway (updated to v1.1.0, 2026-11-01):

- `goose__*` — the Goose language authority: `goose__overview`,
  `goose__list_docs`, `goose__get_section`, `goose__search_docs`,
  `goose__lookup_symbol`, `goose__search_symbols`,
  `goose__list_stdlib_modules`, `goose__list_symbols_in_module`,
  `goose__list_keywords`, `goose__get_operator_precedence`,
  `goose__list_samples`, `goose__get_sample`, `goose__find_pattern`
  (translates a C++/Rust idiom to Goose), `goose__search_samples`.
  Bundled from aardappel/goose @ b781587: 389 doc sections, 702
  stdlib symbols, 57 keywords, 32 sample programs.
- `lobster__*` — the same for Lobster, when a service contract touches
  the Layer 5 boundary.

Ground every language claim in these tools or the upstream repo.
If the gateway is not reachable from your session, the upstream repo
(github.com/aardappel/goose) is the fallback authority — say which
one you used in your report.

## The honest constraint

Services cannot RUN until the kernel reaches K6 (syscalls, first
userspace, first Goose service process — KERNEL_SPEC.md). So Layer 4
work now is: the architecture, the contracts, and real Goose source
written against those contracts. Status words, used exactly:

- **DESIGNED** — spec/contract written, grounded in the Goose docs.
- **WRITTEN** — Goose source exists and every symbol/keyword in it is
  verified against the Goose MCP (or upstream docs).
- **COMPILED** — only with a build log from a real Goose toolchain.
- **NOT BUILT** — anything else. Say it in those words.

## Rules (no exceptions)

1. **NO MOCKS** (KERNEL_SPEC rule 6): no fake services, no stub
   presented as working, no invented APIs. A contract you design is
   labeled a design. Test data stays in tests and never ships.
2. Smallest sensible change. Do not rewrite other layers' files.
   If a contract needs a kernel change, write the requirement into
   your design doc and flag it for Rowan/Pax — do not edit `kernel/`.
3. Spend: the Goose/Lobster MCPs are local bundled data — free to
   query hard. No paid API calls in this lane.
4. Every task ends with what is verified and what is not.

## Tasks

- **B-L1-01 — Service worklist.** From your own tools manifest
  (`os-build/research/tools-candidates.md`), your ecosystem watch,
  and OPENCODE_OS_BUILD.md Section K, write `services/MANIFEST.md`:
  the first Goose services in build order, one line each — name, what
  it does, what it needs from the kernel side (Layers 1–3), what it offers
  the layers above. Mark each DESIGNED / NOT BUILT honestly (all
  start NOT BUILT).
- **B-L1-02 — The service contract.** `os-build/layer1/SERVICE_CONTRACT.md`:
  what a Layer 4 service process IS — how it starts, how it is named,
  how it talks to the kernel (syscall shape as K6 will need it), how
  services talk to each other (IPC), how one reports health/failure,
  how it stops. Ground the Goose-side idioms in the MCP (samples and
  stdlib sections), and mark every kernel assumption as a requirement
  on Layers 1–3, not a fact.
- **B-L1-03 — First service, source.** Pick the simplest service from
  the manifest (a boot log / console service is a good first) and
  write its real Goose source under `services/<name>/`: source files
  plus a README stating its contract, its status word, and how each
  symbol was verified. WRITTEN is the target; COMPILED only if you
  actually run a Goose toolchain and keep the log.
- **B-L1-04 — Second service, source.** The next service from the
  manifest (a time or device service), same standard as B-L1-03.
- **B-L1-05 — Layer boundary notes.** `os-build/layer1/BOUNDARIES.md`:
  what Layer 4 needs from Layers 1–3 (for Rowan/OpenCode), and what
  Layer 4 offers Layers 5–6 (for Milo/Hana) — each item marked as
  contract, requirement, or open question. This is the hand-off sheet
  Pax merges against.
- **B-L1-06 — Report.** Running report at
  `os-build/layer1/BUFFY_REPORT.md`: per task — done, status word,
  how verified, what remains unverified. Update it as you go; it is
  the document Pax gates the merge on.

## Expansion — the full Layer 4 build-out (B-L1-07 … B-L1-78)

Added 2026-11-01 ~09:12 on the boss's order: enough real work to
build Layer 4 out end to end. The six tasks above are the foundation;
these continue in dependency order. Every service below gets real
Goose source under `services/<name>/` at the WRITTEN standard of
B-L1-03 (every symbol verified against `goose__*`), a README with its
status word, and an entry in the manifest. Interface-first tasks
exist because Layer 3 drivers and the K6 transport are not landed
yet: an interface written against a documented contract is real work;
a fake backend pretending to be hardware would be a mock and is
forbidden.

### Wave A — foundations (libraries every service uses)

- **B-L1-07 — Build layout.** `services/BUILD.md`: the per-service
  recipe (`goose -o` to C, freestanding link, one directory per
  service) + the directory skeleton for every service named in the
  manifest, so later tasks land in a prepared tree.
- **B-L1-08 — BootInfo types.** The Goose-side BootInfo block from
  Pax's K6 shape: framebuffer info mirroring the K2 module's
  `FramebufferInfo` field by field, memory summary, tick rate. Cite
  the kernel source lines it mirrors.
- **B-L1-09 — Syscall interface module.** `services/common/sys.goose`:
  the six draft calls from the K6 shape (exit, write_serial,
  write_console, read_key, ticks, yield) as declared externs, plus
  the C shim specification. Transport stays OPEN (Q9) — assert
  nothing about how the call is made.
- **B-L1-10 — Fixed-buffer format library.** No-heap formatting into
  caller buffers: integers, hex, zero padding, string append, the
  primitives every service's output needs. Real code, edge cases
  handled (buffer full = trailing-bool false, never overflow).
- **B-L1-11 — Ring buffer library.** Byte ring + message ring over
  caller storage, the shared queue under the log and console
  services.
- **B-L1-12 — Error conventions module.** The layer-wide error code
  set + the trailing-bool result pattern as one shared module all
  services import, so services agree on failure language.
- **B-L1-13 — Config parser.** Key=value with sections over fixed
  buffers: parse, lookup, typed getters (int/bool/string) with
  honest not-found results. Services' config files depend on it.
- **B-L1-14 — Hash library.** CRC32 and SHA-256 in Goose from their
  published specifications, with the standard test vectors recorded
  in the README and checked by a test program task later (B-L1-55).
  The updater's verification depends on this.
- **B-L1-15 — Stdlib gap audit.** `os-build/layer1/STDLIB_GAPS.md`:
  per planned service, what it needs vs what `goose__` stdlib
  modules actually provide; every gap named becomes library work.
- **B-L1-16 — Service README template.** The standard per-service
  README (contract, dependencies, status word, how verified) applied
  as the skeleton in every service directory.

### Wave B — the core services, full source

- **B-L1-17 — Console service, full.** Line editing, echo, history
  ring over the B-L1-11 library, built on write_console/read_key: a
  usable interactive console, not a stub.
- **B-L1-18 — Serial log service.** Levels, per-service tags, ring
  retention, flush policy; the layer's single log sink over
  write_serial.
- **B-L1-19 — Time service, full.** Ticks to uptime and wall-clock
  math, duration and timestamp formatting on B-L1-10.
- **B-L1-20 — Supervisor: service table + state machine.** The
  service registry as data (name, state, policy) and the lifecycle
  state machine (stopped/starting/running/failed) as real source.
- **B-L1-21 — Supervisor: restart policies.** Never / on-fail /
  always as per-service data with backoff counters, evaluated by the
  state machine from B-L1-20.
- **B-L1-22 — Name registry.** Register and lookup of service names
  to handles inside the supervisor, the lookup every inter-service
  call goes through.
- **B-L1-23 — Health watchdog.** Heartbeat table, missed-beat
  detection against the time service, escalation into the
  supervisor's restart policies.
- **B-L1-24 — Device manager.** The device table built from BootInfo
  (framebuffer, keyboard, timer, serial), with per-device state and
  the query interface other services use.
- **B-L1-25 — Storage contract + RAM backend.** The block read/write
  interface for the layer, plus a real RAM-disk backend implementing
  it (volatile storage, honestly labelled as the backend until Layer
  3 storage drivers exist — it is real storage, not a mock).
- **B-L1-26 — Input service.** Scancode to key-event translation over
  the K3 ring-buffer contract: keymap table, modifiers, repeat
  handling as data + source.
- **B-L1-27 — Display service.** Virtual consoles multiplexed over
  the single framebuffer contract: per-console scrollback (B-L1-11),
  switch keys, redraw on switch.
- **B-L1-28 — Log formatting service.** The shared record shape
  (timestamp, service, level, message) every service emits through,
  built on B-L1-10/B-L1-19.

### Wave C — network-facing and update services (interface-first)

- **B-L1-29 — Packet interface.** The layer's abstract packet
  send/receive contract that network services are written against,
  so a real Layer 3 network driver can be bound later without
  rewriting them.
- **B-L1-30 — Network config model.** Interfaces and addresses as
  data + config parsing on B-L1-13.
- **B-L1-31 — DHCP client.** The full discover/offer/request/ack
  state machine against B-L1-29, with lease timing on B-L1-19.
- **B-L1-32 — DNS resolver client.** Query construction and response
  parsing (compression pointers handled) against B-L1-29.
- **B-L1-33 — Socket contract.** What a socket means at Layer 4:
  handle table, states, and the calls services use, over B-L1-29.
- **B-L1-34 — Updater: manifest.** Fetch and parse the update
  manifest (what version, which components, which hashes) on
  B-L1-13 + B-L1-33.
- **B-L1-35 — Updater: verify + apply plan.** Hash verification on
  B-L1-14 and the apply plan as an ordered, inspectable step list —
  a plan is produced and recorded; nothing self-modifies the OS.
- **B-L1-36 — Updater: rollback record.** The pre-apply state record
  and the rollback step list, written before any apply plan runs.
- **B-L1-37 — Time sync client.** NTP packet build/parse and offset
  math against B-L1-29, feeding the time service.

### Wave D — agent host and audit (Layer 5's Layer 4 side)

- **B-L1-38 — Agent host: process table.** The host-side table of
  agent processes (identity, state, grants), written against Milo's
  ML-L2-01 model when it lands; before that, against the draft
  contract in your BOUNDARIES notes, marked as a dependency.
- **B-L1-39 — Agent host: lifecycle.** Start/stop/fail handling for
  agent processes through the supervisor's machinery (B-L1-20).
- **B-L1-40 — Agent host: capability grants.** Which Layer 4
  services each agent may call, as data the host checks on every
  call — design + source.
- **B-L1-41 — Audit service: writer.** Append-only record writing
  over the B-L1-25 storage contract: timestamped, sequenced,
  tamper-evident via B-L1-14 chaining.
- **B-L1-42 — Audit service: reader.** Query by time range and by
  service/agent, the read side of B-L1-41.
- **B-L1-43 — Session service.** Console sessions (user or agent) as
  data + lifecycle source, owning which session the display service
  shows.
- **B-L1-44 — Call matrix.** The service-to-service permission table
  and its single enforcement check, used by the registry (B-L1-22).

### Wave E — test programs and per-service docs

One Goose test program per item (source that runs the moment K6
exists; status WRITTEN, never claimed as run), exercising the named
service's contract end to end:

- **B-L1-45 — Test program: format library (B-L1-10).**
- **B-L1-46 — Test program: ring buffer (B-L1-11).**
- **B-L1-47 — Test program: config parser (B-L1-13).**
- **B-L1-48 — Test program: BootInfo + syscalls (B-L1-08/09).**
- **B-L1-49 — Test program: bootlog + console (B-L1-17).**
- **B-L1-50 — Test program: log service + formatting (B-L1-18/28).**
- **B-L1-51 — Test program: time service (B-L1-19).**
- **B-L1-52 — Test program: supervisor + registry (B-L1-20/22).**
- **B-L1-53 — Test program: watchdog (B-L1-23).**
- **B-L1-54 — Test program: storage + RAM backend (B-L1-25).**
- **B-L1-55 — Test program: hash vectors (B-L1-14).**
- **B-L1-56 — Test program: input + display (B-L1-26/27).**
- **B-L1-57 — Test program: DHCP + DNS over a loopback packet pair
  (B-L1-31/32, both ends in the test — a real protocol exercise, not
  a fake network).**
- **B-L1-58 — Test program: updater plan + rollback record
  (B-L1-34/35/36, plan only — nothing applied).**
- **B-L1-59 — Test program: agent host lifecycle + grants
  (B-L1-39/40).**
- **B-L1-60 — Test program: audit write/read round trip (B-L1-41/42).**
- **B-L1-61 — README completion pass.** Every service README brought
  to the B-L1-16 template in full: contract, dependencies, status
  word, verification basis.
- **B-L1-62 — Source audit pass.** Re-check every service source
  against `goose__*` symbol by symbol; log corrections in the report.

### Wave F — integration and closeout

- **B-L1-63 — Link map.** `os-build/layer1/LINK_MAP.md`: which
  service calls which, drawn from the actual sources, not the plan.
- **B-L1-64 — Boot order.** The service start order as a dependency
  graph over the manifest, with the supervisor's table generated
  from it (B-L1-20 data, not prose only).
- **B-L1-65 — Failure plan.** Per service: how its failure is
  detected (watchdog/supervisor) and what the layer does next, each
  row traced to a mechanism that exists in source.
- **B-L1-66 — K6 needs list.** Everything Layer 4 needs from Layers
  1–3 to actually run, written as questions in MAC_QUESTIONS format
  for Rowan/OpenCode — the hand-off that unblocks COMPILED status.
- **B-L1-67 — BOUNDARIES final pass.** B-L1-05 rewritten against the
  finished sources and Milo's/Hana's landed docs.
- **B-L1-68 — Gap libraries 1–3.** Implement the top three libraries
  from STDLIB_GAPS.md (B-L1-15) as common modules, one task each:
  B-L1-68, B-L1-69, B-L1-70 take the first three gaps in audit order.
- **B-L1-71 — Manifest final state.** MANIFEST.md updated so every
  service carries its true final status word for this build-out.
- **B-L1-72 — Report + ready post.** BUFFY_REPORT.md brought fully
  current (per task: status word, how verified, what remains
  unverified) and the room-1 post that the branch is ready for Pax
  to merge.

### Standing gaps (taken when their dependency lands)

- **B-L1-73 — Bind the packet interface** to the first real Layer 3
  network path when Rowan/OpenCode land one; until then NOT BUILT
  and not started.
- **B-L1-74 — Bind storage** to a real Layer 3 block driver the same
  way, replacing the RAM backend as the default.
- **B-L1-75 — First COMPILED pass:** when a Goose toolchain and the
  K6 answers exist, compile every service, keep the logs, and raise
  status words only where a log proves it.
- **B-L1-76 — First RUN pass:** with K6 landed, run the Wave E test
  programs on the real kernel and record results per program.
- **B-L1-77 — Supervisor live pass:** boot order (B-L1-64) exercised
  on the real kernel; failures fixed in source, never in the report.
- **B-L1-78 — Layer 4 sign-off note.** `os-build/layer1/SIGNOFF.md`:
  what Layer 4 is, what is proven, what is not — written for the
  boss's demo, claims matching the scoreboard exactly.

## Done means

Branch pushed, report current, every claim in the report carrying its
status word, and a room-1 post saying the branch is ready for Pax to
merge. Pax verifies against the Goose MCP data before merging.
