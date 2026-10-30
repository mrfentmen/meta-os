# TASKS — Meta OS Rust rebuild (single source of assignments)

This doc governs who ports what. The plan (`docs/RUST_REBUILD_PLAN.md`)
is the why and how; `batches/*.md` are the per-batch specs;
`BATCHES.md` is the file-list index (exact source files and counts).

- **Nobody ports a batch that is not theirs under this doc.** Sections
  never overlap: every batch B01–B31 (B12 split as B12a/B12b/B12c)
  appears in exactly one section.
- **B00 is done, not assigned:** the cargo workspace skeleton landed in
  `87cb6dd8` and was gate-1 compiled by Milo (`a00be765`, 19/19 crates
  clean). Gate 2 for the skeleton (the boss's Mac) is still open.
- This doc supersedes the earlier lane postings and paste sets as the
  assignment source. Del's word for starting: Buffy reads
  **§ Buffy**; the OpenCode fleet reads **§ OpenCode**.

## Shared rules

- Pull `main` before starting; read the live tip before every push.
- The Python/Node source is the spec: **port behavior, never redesign.**
  Same inputs, outputs, edge cases, error shapes — port the oddity and
  note it.
- Tests first where they exist; parity is case-by-case (same test name
  roots, same fixtures), not "similar coverage."
- Small commits: `B##: <piece> — UNCOMPILED` while unproven;
  `B##: <piece> PORTED` only after compile **and** parity pass.
  CARRIED batches commit as `B##: <piece> CARRIED`.
- **Never force-push.**
- A crate's `lib.rs` / `Cargo.toml` is edited only by the crate owner
  named in `BATCHES.md`. Batches sharing a crate (`intel`, `os-misc`)
  keep their modules in their own module subtree; the claim holder
  coordinates the `lib.rs` wiring.
- **Stall rule:** three compile rounds on the same error class = park
  the batch, write the blocker into the batch spec, move on.
- Python/Node originals stay untouched — they are the live fallback
  until a batch is PORTED. Never delete or stub over an original.
- Tests that need the excluded `relay_common` / muse-relay viewer code
  are marked **exclusion-blocked** in the completion report — never
  silently dropped, never faked green.
- **Compile gates:** Milo's VM is gate 1 for crew-pushed work; the
  boss's Mac is gate 2 and the final word. Nothing counts as compiled
  from the Pax sandbox (rustc cannot write output there).

## Buffy

Buffy — this section is yours, complete and self-contained. Work the
batches **in the order listed**. Exact source files: the batch's entry
in `BATCHES.md`; full spec: `batches/B##.md`. All of B24–B30 land in
the shared crate `crates/os-misc` — keep each batch's modules in its
own subtree and filter `cargo test -p os-misc` by your batch's test
name roots.

1. **B24 — Bus messaging core** — crate `crates/os-misc` — 6 files.
   Sources and spec: `BATCHES.md` §B24, `batches/B24.md`. Port
   `os/poll.py`, `os/presence.py`, `os/send.py`, `os/store.py`,
   `os/watch.py`, `os/watch_nick.py`. Parity bar: no test files are
   assigned to this batch — parity is a behavior-for-behavior match
   against the sources and their in-tree callers. Trap: bus behavior
   that touched the excluded `relay_common` module is ported from the
   in-tree callers only, and the bus-parity test case
   (`test_bustools_parity.py`) is assigned to B31 (also yours, below) —
   name any case you cannot run as exclusion-blocked.
2. **B25 — Bus messaging extras** — crate `crates/os-misc` — 10 files.
   Sources and spec: `BATCHES.md` §B25, `batches/B25.md`. Parity bar:
   the batch's 4 test files ported case-by-case —
   `test_announce.py`, `test_edits.py`, `test_forward.py`,
   `test_saved.py` (same name roots, same fixtures).
3. **B26 — Bus bridges, digest & admin** — crate `crates/os-misc` —
   9 files. Sources and spec: `BATCHES.md` §B26, `batches/B26.md`.
   Parity bar: the batch's 3 test files ported case-by-case —
   `test_digest.py`, `test_export.py`, `test_webhook.py`.
4. **B27 — World packs** — crate `crates/os-misc` — 19 files. Sources
   and spec: `BATCHES.md` §B27, `batches/B27.md`. Mixed batch: the
   `PACK.md` / `pack.json` pack files are **data — carry them
   unchanged**; the only code is `os/worlds/validate_pack.py` — port
   the validator. Trap: the validator's parity test
   (`test_worlds_pack.py`) is assigned to **B31**, so B27 closes
   PORTED only when that case passes under B31.
5. **B28 — OS docs, roles & root docs** — crate `crates/os-misc` —
   16 files. **CARRIED, not ported.** Sources and spec: `BATCHES.md`
   §B28, `batches/B28.md`. Docs only — no code, no tests. Done =
   every listed file inventoried, confirmed logic-free, left in
   place; do not move or rewrite them. Any file that turns out to
   carry logic is bounced back to Pax for re-batching, not ported
   here. No compile gates, no parity bar. Report state CARRIED.
6. **B29 — Crew dirs & demo/submission assets** — crate
   `crates/os-misc` — 22 files. **CARRIED, not ported.** Sources and
   spec: `BATCHES.md` §B29, `batches/B29.md`. Asset batch (crew
   READMEs, demo/submission audio). Done = inventoried, confirmed
   logic-free, left in place. Audio files are never re-encoded or
   regenerated. Report state CARRIED.
7. **B30 — Lane plans** — crate `crates/os-misc` — 12 files.
   **CARRIED, not ported.** Sources and spec: `BATCHES.md` §B30,
   `batches/B30.md`. Plan documents only. Done = inventoried and
   left in place. Report state CARRIED.
8. **B31 — Parity test harness** — crate `crates/parity-tests` —
   34 files. Sources and spec: `BATCHES.md` §B31, `batches/B31.md`.
   Harness first: `os/tests/fake_redis.py`, `os/tests/helpers.py`,
   and `os/mos/acceptance.py` port as test-support code before the
   cases that use them; then the remaining 31 test files port
   case-by-case (same name roots, same fixtures). This harness is
   where the cross-assigned cases land — B24's
   `test_bustools_parity.py` and B27's `test_worlds_pack.py` are in
   this batch's list. Cases needing the excluded `relay_common` /
   viewer code are recorded exclusion-blocked — never dropped.

**Your report format** — one line per batch, posted where you were
told to read this section from:

`B## <PORTED|CARRIED|BLOCKED> crate=<crate> gate1=<pass/fail/na> gate2=<pass/fail/na> parity=<passed>/<total> excl-blocked=<n> commit=<sha>`

(CARRIED batches: `gate1=na gate2=na parity=na`.)

**Your compile loop:** if you are running in the sandbox, you cannot
compile — your batches go through Milo (gate 1), then the boss's Mac
(gate 2), and your commits stay `— UNCOMPILED` until both pass. If
you are running on the boss's Mac, compile locally as you go; the
control window's clean build is still the final word before PORTED.

## OpenCode

Fleet — this section is yours: batches B01–B23 plus B07 integration,
grouped by the plan's waves. Every batch is one claim line: batch,
crate, file count, spec. Full source lists are in `BATCHES.md`; the
cold-executable spec for each batch is `batches/B##.md` — read it
before writing code.

**Fleet protocol:**

- One agent per batch. **Claim = create and push branch
  `batch/B##` BEFORE writing any code.** First claim wins; a batch
  whose branch exists is taken. No branch, no work.
- One git worktree per agent — never two agents in one worktree.
- Agents compile locally on the Mac as they go (`cargo build -p
  <crate>` / `cargo test -p <crate>` from the spec).
- Stagger agent starts 30–60 seconds apart (the shared OpenCode
  sqlite locks if agents start together). Run with
  `opencode run --auto` and stdin closed (`< /dev/null`) or the run
  hangs / auto-rejects.
- Merges happen **only from the control window**, after
  `cargo build` + `cargo test` pass on the branch. Never force-push;
  read the tip before merging.
- Crew agents may also claim from this section by the same branch
  rule — a claim is a claim regardless of who makes it (a crew claim
  also gets announced on the bus, room 1).

### Wave 1 — the assess path

- **B01** Queue core — `crates/queue-core` — 3 files — `batches/B01.md`
- **B02** Queue store (Upstash store + repo layer) — `crates/queue-store` — 2 files — `batches/B02.md`
- **B03** Guardrail + Spark transport — `crates/guardrail` — 2 files — `batches/B03.md`
- **B04** Agent runtime (trio agent) — `crates/agent-runtime` — 1 file — `batches/B04.md`
- **B05** Assess server (Node service) — `crates/assess-server` — 5 files — `batches/B05.md`

### Wave 2 — relay + stack

- **B08** Nuntius relay — `crates/relay` — 3 files — `batches/B08.md`
- **B06** Stack wiring (run-stack) — `crates/stack` — 1 file — `batches/B06.md` (closes the wave; it wires the services the other waves produce)

### Wave 3 — OS services

- **B16** Jobs service — `crates/os-jobs` — 6 files — `batches/B16.md`
- **B17** Memory service — `crates/os-memory` — 3 files — `batches/B17.md`
- **B18** Identity & capabilities service — `crates/os-identity` — 1 file — `batches/B18.md`
- **B19** Workspace & artifact store — `crates/os-workspace` — 2 files — `batches/B19.md`
- **B20** Budget & resource policy — `crates/os-budget` — 13 files — `batches/B20.md`
- **B21** Supervisor & watchdog — `crates/os-supervisor` — 39 files — `batches/B21.md`
- **B22** Worker runtime & drivers — `crates/os-worker` — 19 files — `batches/B22.md`
- **B23** Boot glue & deployment — `crates/os-boot` — 46 files — `batches/B23.md`

### Wave 4 — intel + dashboard

- **B09** Intel core & capability registry — `crates/intel` — 70 files — `batches/B09.md`
- **B10** Briefings & dispatch — `crates/intel` — 43 files — `batches/B10.md`
- **B11** Intel Spark client & mind images — `crates/intel` — 8 files — `batches/B11.md`
- **B12a** Evals & drills — drill and check code (**port**) — `crates/intel` — 39 files — `batches/B12a.md`
- **B12b** Evals & drills — eval records A–L (**CARRIED**, fixtures — carry + verify, do not port) — `crates/intel` — 50 files — `batches/B12b.md`
- **B12c** Evals & drills — eval records P–W + SAM set (**CARRIED**, fixtures — carry + verify, do not port) — `crates/intel` — 49 files — `batches/B12c.md`
- **B13** Examples & devpack — `crates/intel` — 23 files — `batches/B13.md`
- **B14** Trust & launch (remaining intel) — `crates/intel` — 4 files — `batches/B14.md`
- **B15** Dashboard backend contract — `crates/dashboard` — 31 files — `batches/B15.md`

### B07 — integration (closes every wave)

- **B07** Integration assist — no crate of its own, 0 source files — `batches/B07.md`. The checklist (full-workspace build, byte-for-byte contract seam check, cross-crate test pass, compile-error triage under the stall rule, fallback-integrity diff) runs at **every wave close** and whenever two PORTED batches first meet. Claimed per wave by the same branch rule (`batch/B07`), or run directly from the control window. Seam fixes land in the crate that owns the contract — never by copy-pasting a type into the consuming crate.

## Status legend & reporting

- **DRAFT** — claimed, port in progress, uncompiled.
- **GATE1** — compiles + parity passes at gate 1 (Milo's VM, or the
  local Mac build in the fleet topology).
- **GATE2** — compiles + parity passes at gate 2 (the boss's Mac /
  control window). The final word.
- **PORTED** — both gates + parity passed; the Rust port is live for
  that batch and the Python original retires to fallback history.
- **PARKED** — stalled under the stall rule; the blocker is written
  in the batch spec.
- **CARRIED** — data/docs/assets batch: inventoried, verified, left
  in place. No port, no gates.

Status is reported where the work was claimed: the crew bus (room 1)
for crew work; the control window for the local fleet. One line per
batch, in the format given in each spec (`batches/B##.md`).
