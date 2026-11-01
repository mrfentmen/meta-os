# BUFFY — Layer 1 work order: Goose system services

From the boss's order 2026-11-01 (~08:18): the OS build goes parallel
by layer. **Your layer is Layer 1 — the Goose system services.** Pax is
your pairing on this layer (service shape, coordination, and the
merge). Rowan + OpenCode hold Layer 0 (Rust kernel), Hana + Milo hold
Layer 2 (Lobster agents/apps). Work in your own branch; **Pax merges
when you are done — do not merge your own branch** (boss's merge rule).

Branch: `buffy/layer1-goose-services` in `mrfentmen/meta-os`.
Report to crew room 1 at every stage boundary.

## What Layer 1 is

Meta OS has its own kernel (Layer 0, Rust, `kernel/`). Layer 1 is the
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
  the Layer 2 boundary.

Ground every language claim in these tools or the upstream repo.
If the gateway is not reachable from your session, the upstream repo
(github.com/aardappel/goose) is the fallback authority — say which
one you used in your report.

## The honest constraint

Services cannot RUN until the kernel reaches K6 (syscalls, first
userspace, first Goose service process — KERNEL_SPEC.md). So Layer 1
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
  it does, what it needs from the kernel (Layer 0), what it offers
  the layers above. Mark each DESIGNED / NOT BUILT honestly (all
  start NOT BUILT).
- **B-L1-02 — The service contract.** `os-build/layer1/SERVICE_CONTRACT.md`:
  what a Layer 1 service process IS — how it starts, how it is named,
  how it talks to the kernel (syscall shape as K6 will need it), how
  services talk to each other (IPC), how one reports health/failure,
  how it stops. Ground the Goose-side idioms in the MCP (samples and
  stdlib sections), and mark every kernel assumption as a requirement
  on Layer 0, not a fact.
- **B-L1-03 — First service, source.** Pick the simplest service from
  the manifest (a boot log / console service is a good first) and
  write its real Goose source under `services/<name>/`: source files
  plus a README stating its contract, its status word, and how each
  symbol was verified. WRITTEN is the target; COMPILED only if you
  actually run a Goose toolchain and keep the log.
- **B-L1-04 — Second service, source.** The next service from the
  manifest (a time or device service), same standard as B-L1-03.
- **B-L1-05 — Layer boundary notes.** `os-build/layer1/BOUNDARIES.md`:
  what Layer 1 needs from Layer 0 (for Rowan/OpenCode), and what
  Layer 1 offers Layer 2 (for Hana/Milo) — each item marked as
  contract, requirement, or open question. This is the hand-off sheet
  Pax merges against.
- **B-L1-06 — Report.** Running report at
  `os-build/layer1/BUFFY_REPORT.md`: per task — done, status word,
  how verified, what remains unverified. Update it as you go; it is
  the document Pax gates the merge on.

## Done means

Branch pushed, report current, every claim in the report carrying its
status word, and a room-1 post saying the branch is ready for Pax to
merge. Pax verifies against the Goose MCP data before merging.
