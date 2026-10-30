# Meta OS — Rust Rebuild Master Plan

Ordered by Del (Mrfentmen), 2026-10-30 04:47 EDT: stop Trio feature work;
rebuild Meta OS in Rust inside `mrfentmen/meta-os` on a 12-hour push.
Plan written by Pax. Batch map: `BATCHES.md` (repo root). Batch specs:
`batches/B##.md` — one per claimable unit, each cold-executable.
Port rules: the rust-port skill (summarized in every batch spec).

**The one rule, above all others: port behavior, do not redesign.**
The Python/Node source is the specification — same inputs, same outputs,
same edge cases, same error shapes. Port the oddities too, and note them.
Any real design change needs Del's word first.

---

## 1. Mission + definition of done

**Mission.** Port every in-scope Python/Node piece of Meta OS (591 source
files, mapped in `BATCHES.md`) to Rust, in the 19-crate workspace laid by
B00, without changing any wire contract, and without ever breaking the
working Python system that is the hackathon submission today.

**A batch is PORTED when all of these hold:**

1. It compiles at gate 1 (Milo's VM — topology A) **and** gate 2 (Del's
   Mac). Nothing counts as compiled from the Pax sandbox; rustc cannot
   write output there, so sandbox-written Rust is UNCOMPILED by
   definition until a gate says otherwise.
2. Its ported parity tests pass — case-by-case against the Python/Node
   suites, same name roots, same fixtures. Exclusion-blocked cases are
   listed by name in the batch's completion report (never dropped,
   never faked green).
3. The Python/Node originals are untouched.
4. The completion one-liner is posted (bus, topology A) or the branch is
   merged (topology B), with commit messages in the batch format:
   `B##: <piece> — UNCOMPILED` while unproven, `B##: <piece> PORTED`
   only when 1–3 hold.

Doc/data batches (B12b, B12c, B28, B29, B30) close as **CARRIED**:
every listed file inventoried, carried or confirmed in place, and
confirmed logic-free. CARRIED is an honest terminal state, not a port.

**The whole rebuild is DONE when:**

- The full workspace builds clean on Del's Mac: `cargo build` at the
  repo root, zero errors.
- All parity suites pass on the Mac (queue 29-case bar, OS test ports,
  intel ports, harness in B31).
- The Rust stack passes the **same live queue round trip** the Python
  stack passed: frame → `POST /api/assess` → queue → resident agent →
  guarded Spark call → `validateAssessment`-clean result → result key
  read back. (Python stack's verified result on the steam frame:
  "steam or fog.")
- The Spark guardrail is intact in the port: every model call counted
  against the $75 test cap, refused at the cap.

**Fallback rule (no exceptions).** Python stays the live system until
each batch is PORTED. A batch that is not PORTED does not replace
anything. If the rebuild stalls, the submission is the Python stack,
exactly as it stands — the rebuild can only add, never subtract.

## 2. Verified starting state

All facts below were verified by Pax against the live repos (GitHub API
read-backs), not taken from crew reports alone.

**Repos.**

- Submission repo: `mrfentmen/meta-os` (id 1436948804, public) — this is
  the former `meta-sentinel`, renamed 2026-10-30 04:32 on Del's ruling.
  Clean in-window history (created 2026-10-28).
- The old standalone OS repo is `mrfentmen/meta-os-archive`
  (id 1434905243, history preserved), made **private** 2026-10-30 04:35
  on Del's order. Nothing for the rebuild lives there.
- `mrfentmen/meta-ops` exists, public, **empty** — a parked
  post-hackathon consolidation vessel. Not part of this plan.

**Code in the submission repo.**

- The cleaned standalone-OS tree landed under `os/` in 4 batch commits,
  tip `520a0678`: **574 files, subtree SHA `f0a17391` blob-identical to
  the verified source tree** (full 574-pair comparison, not a sample).
  The fold also added the README Repository-map entry for `os/`.
- B00 (commit `87cb6dd8`, on top of `520a0678`, read-back verified):
  root `Cargo.toml` workspace, `BATCHES.md`, 19 crates under `crates/`
  with doc-comment stubs only — no logic, nothing faked. 978 blobs at
  the commit. The skeleton has **never been compiled anywhere**; its
  first compile is a gate-1 job.
- In-scope port surface: **591 source files** (everything under
  `server/`, `relay/`, `os/`, plus `run-stack.sh`, minus the excluded
  `relay/viewer.html`), each assigned to exactly one batch in
  `BATCHES.md`.

**Suite baselines (the bars the ports are measured against).**

- npm suite: **1906/1906** at last crew report (Hana, UI-SPARK-STATUS,
  on top of 1902/1902 at the fold). Re-read the count at the live tip
  before quoting it.
- queue-python: **29/29** (`tests/queue-python/test_queue.py` — the
  parity reference for B01–B04, stays in place).
- OS Python suite in the cleaned tree: **959 runnable tests, 769 pass**.
  Every failure/error traces to Del's relay exclusions (94 import
  errors for the excluded `relay_common` module; missing `bus.html` /
  `crew-board.html` reads; downstream crashes), **not** to fold damage.
  The full standalone suite was 2,416 tests; the cleaned tree ships
  fewer test files and its relay-dependent tests cannot run without
  the excluded code. That is the price of the clean-repo ruling,
  stated plainly — ports touching those areas mark affected tests
  exclusion-blocked.

**Live-verified behavior being ported.**

- Queue leg verified live end-to-end on the real store (claim via SET
  NX lease/heartbeat → guarded Spark call → validate → result written),
  including the idempotency proof (deterministic job id, no re-bill).
- `run-stack.sh` stack round trip verified live: `POST /api/assess`
  answered through the queue envelope; steam frame → HTTP 200,
  "steam or fog."
- Spark: 38 guarded calls, **$0.2543 of the $75 cap** spent. Host
  `api.meta.ai`, model `muse-spark-1.3`.
- Hostname hygiene: the live bus hostname is **not** in the repo;
  `trio_store.py` resolves `TRIO_UPSTASH_HOST` at runtime, else falls
  back to the labeled local SQLite store. Ports keep this exactly.

**Compile gates.**

- **Gate 1 — Milo's VM.** Milo installed rustup stable 1.99.1 into his
  home dir and proved it on the bus: hello-world `rustc` compile *and*
  a cargo project built and ran. No write guard there. Fast loop.
- **Gate 2 — Del's Mac.** Final check for every batch. Del compiles,
  returns errors; the writer fixes. Rustup install one-liner is in §6.
- The Pax sandbox is **not** a gate: the write guard deterministically
  blocks rustc/cargo output there (verified repeatedly; toolchain
  staged at `~/workspace/.rust/bin` cannot change this).

## 3. Two execution topologies

The batches are **agent-agnostic**: every `batches/B##.md` spec is
self-contained and cold-executable by any competent agent (crew Muse,
Buffy, an OpenCode agent, a human). The batch map names owners from the
bus lanes (Rowan B01–B07, Hana B08–B15, Milo B16–B23, Buffy B24–B31,
Pax B00/integration), but ownership is a default, not a lock — an
unclaimed or stalled batch can be re-claimed by anyone under the claim
protocol. **Buffy is optional under this plan**: no batch depends on a
specific agent.

### Topology A — remote crew (bus-coordinated)

- Crew works from their own environments, pushing to `main` of
  `mrfentmen/meta-os` under the lane push protocol: read the live tip
  before every push, one commit per buildable step, never force-push,
  read back after pushing.
- **Claim protocol:** before starting a batch, post the claim to crew
  room 1 (`muse-bus:room:1`): `CLAIM B## <nick>`. A batch with an open
  claim is taken. Release or completion posts use the spec's one-line
  report format.
- **Compile loop:** writer pushes → Milo compiles at gate 1 → errors
  posted back on the bus → writer fixes in small commits → Del compiles
  at gate 2 for the PORTED stamp.
- Pax coordinates: batch tracking, seam triage (B07), the B12 watch,
  and verification of every PORTED claim against the live tip.

### Topology B — Del's Mac tmux fleet (OpenCode, local compile)

- Everything runs on Del's Mac: agents write *and compile* locally, so
  the compile-error loop is minutes, not bus-round-trips. Full runbook
  in §6.
- **Claim protocol:** the branch is the claim. Before starting, check
  `git ls-remote --heads origin 'batch/*'`; if `batch/B##` exists, the
  batch is taken. Push the empty-claim by creating the branch with the
  spec commit first, then work.
- One git worktree per agent, one branch `batch/B##` per batch, never
  two agents in one worktree (stale-worktree clobber is a known,
  already-paid-for failure — §6).
- The control window (Del, or a supervising agent) merges: it builds
  and tests the branch, then merges to `main`. Agents never merge
  their own branches and never force-push.

### Mixing topologies

A batch is executed under exactly one topology at a time. A claim in
one topology must be visible in the other before work starts: bus
claims are mirrored by a `batch/B##` branch stub, and branch claims
are announced on the bus by Pax. When in doubt, the bus post wins —
it is the crew's shared record.

## 4. Waves and dependencies

Work runs in waves. B07 (integration assist, `batches/B07.md`) closes
every wave: full-workspace build, contract seam check, cross-crate
tests, fallback-integrity diff. A wave is not closed until B07 signs
it. Within a wave, batches run in parallel; across waves, later waves
may start early on crates that don't depend on an open seam.

**Shared-types rule (all waves).** Contract types — job envelope,
result body, assess contract, capability registry shapes — live in the
crate that owns the contract (queue types in `queue-core`/`queue-store`,
assess types in `assess-server`, and so on). Other crates depend on the
owning crate. Copy-pasting a type into a second crate is a defect, and
B07 bounces it.

### Wave 1 — the assess path (the submission's live wire)

| Batch | Piece | Crate |
|---|---|---|
| B01 | Queue core (queue service) | queue-core |
| B02 | Queue store (Upstash + repo layer) | queue-store |
| B03 | Guardrail + Spark transport | guardrail |
| B04 | Agent runtime (trio agent) | agent-runtime |
| B05 | Assess server (Node service) | assess-server |

Dependencies: B02 depends on B01's job/lease types; B04 depends on B01
(claim), B02 (result write), B03 (guarded generation); B05 depends on
B01–B03 shapes for its queue-first path. B01 and B03 are startable
immediately, in parallel. **Wave 1 PORTED = the Rust assess path can
answer the live round trip** (proven at the whole-rebuild level, §1).

### Wave 2 — relay + stack

| Batch | Piece | Crate |
|---|---|---|
| B08 | Nuntius relay | relay |
| B06 | Stack wiring (run-stack) | stack |

B08 is independent of Wave 1 (start any time). B06 closes the wave: it
wires whatever is PORTED (Rust where PORTED, Python where not — the
stack script's job is a working stack, and it must say honestly which
pieces are which).

### Wave 3 — OS services

| Batch | Piece | Crate |
|---|---|---|
| B16 | Jobs service | os-jobs |
| B17 | Memory service | os-memory |
| B18 | Identity & capabilities | os-identity |
| B19 | Workspace & artifact store | os-workspace |
| B20 | Budget & resource policy | os-budget |
| B21 | Supervisor & watchdog | os-supervisor |
| B22 | Worker runtime & drivers | os-worker |
| B23 | Boot glue & deployment | os-boot |

Dependencies: B19's artifact store is used by B16 (job artifacts) —
port B19's interface early or stub the seam in B07, never fork the
type. B21/B22 meet at the watchman/driver seam. B23 is mostly carried
assets (scripts, units) plus the `mos` CLI behavior; it can run in
parallel with everything.

### Wave 4 — intel + dashboard

| Batch | Piece | Crate |
|---|---|---|
| B09 | Intel core & capability registry | intel |
| B10 | Briefings & dispatch | intel |
| B11 | Intel Spark client & mind images | intel |
| B12a | Evals & drills — code | intel |
| B12b | Eval records A–L (CARRIED) | intel |
| B12c | Eval records P–W + SAM (CARRIED) | intel |
| B13 | Examples & devpack | intel |
| B14 | Trust & launch | intel |
| B15 | Dashboard backend contract | dashboard |

All intel batches share **one crate** (`crates/intel`): agree the
module layout once (B09 first), keep each batch in its own module
subtree, and expect merge friction — small commits, constant tip
reads. B11 routes Spark counting through B03's guardrail, never a
private counter. B15 is the documented backend contract only; the web
viewer is excluded.

### Wave 5 — remainder + parity harness

| Batch | Piece | Crate |
|---|---|---|
| B24 | Bus messaging core | os-misc |
| B25 | Bus messaging extras | os-misc |
| B26 | Bus bridges, digest & admin | os-misc |
| B27 | World packs | os-misc |
| B28 | OS docs, roles & root docs (CARRIED) | os-misc |
| B29 | Crew dirs & demo/submission assets (CARRIED) | os-misc |
| B30 | Lane plans (CARRIED) | os-misc |
| B31 | Parity test harness | parity-tests |

B31's harness pieces (`fake_redis`, `helpers`, `acceptance`) port
first inside the batch — other batches' cross-cutting cases depend on
them. B24–B26 port bus behavior from the in-tree callers only (the
`relay_common` module is excluded, §9).

### B07 — integration, closing each wave

Not a wave of its own: the checklist in `batches/B07.md` runs at every
wave close and whenever two PORTED batches first meet.

## 5. B12 pre-split (138 files → three claimable units)

B12 as mapped holds **138 files** — one crate's worth of evals and
drills, ~4× the median batch. It is pre-split here; **the claimable
unit is the sub-batch**, and "B12" remains the umbrella name for
reporting. All three land in the shared `intel` crate.

| Unit | Files | Contents |
|---|---|---|
| B12a | 39 | **Code.** All of `os/intel/drills/*.py`, the intel-level check/runner modules (`abrun`, `boot_*_check`, `e2e1–3`, `sam_check`/`sam_render`, `security_pass`, drill runners), plus `os/intel/evals/watchdog_tuning.py`. This is the only B12 unit that ports logic. |
| B12b | 50 | **Eval records A–L (CARRIED).** `os/intel/evals/` specs, rubrics, expected outputs and logs, alphabetical `ab_run` → `log`. Carried unchanged as fixtures in the crate, paths/names preserved. |
| B12c | 49 | **Eval records P–W + SAM set (CARRIED).** `power_cut` → `watchman_watch`, plus the SAM set (`sam/*.png`, `sam/pairs.json`, `sam_pairs.md`). Carried unchanged as fixtures. |

Traps the split creates, stated now so nobody discovers them mid-run:

- B12a's behavior tests are **not** in B12's file list — they were
  assigned by name to B09 (`test_intel_abrun.py`, `test_intel_drill_*.py`,
  demo/drill tests) and B31. B12a ports the code those tests exercise;
  its parity is proven when those cases pass against the ported code.
- The SAM checker/render code is in B12a; the SAM fixtures are in
  B12c. Land B12c's fixtures before running SAM parity.
- Watchman/watchdog *records* are in B12c; the watchman *behavior*
  port is B21. Records are fixtures, never the spec.
- Adversarial fixtures (e.g. `dispatch_adversarial.md`) are test data:
  carried byte-for-byte, never cleaned up.

## 6. Mac runbook — topology B (tmux fleet of OpenCode agents)

For Del's Mac. Agents write and compile locally; Del (or a supervising
agent in the control window) merges.

### 6.1 One-time setup

```sh
# Rust toolchain (one line, official installer)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Repo
git clone https://github.com/mrfentmen/meta-os.git
cd meta-os
cargo build        # skeleton check: 19 crates, stubs only — must build clean
```

If the skeleton does not build clean, stop and report the exact error
before any batch work starts — that is a B00 defect, routed to Pax.

### 6.2 Worktrees and branches — the discipline that prevents the known failure

One worktree + one branch per agent. **Never two agents in one
worktree, never two agents on one branch.** (Lesson already paid for:
a stale worktree clobbering main, 2026-10-04 — every push/merge in
this plan diffs against the live tip first.)

```sh
cd meta-os
git fetch origin
git ls-remote --heads origin 'batch/*'        # see what is already claimed
git worktree add ../metaos-B01 -b batch/B01 origin/main
git worktree add ../metaos-B02 -b batch/B02 origin/main
# one per agent; the pushed branch IS the claim
```

### 6.3 tmux layout

```sh
tmux new-session -s rust -n control
# one window per agent, each started in its own worktree:
tmux new-window -t rust -n B01 -c ~/metaos-B01
tmux new-window -t rust -n B02 -c ~/metaos-B02
# ... etc
```

Session `rust`: window 0 `control` (merges, builds, this plan), then
one window per running agent named by batch id.

### 6.4 Running an agent — hard lessons, baked in

- Always: `opencode run --auto` with **stdin closed**. Without
  `< /dev/null`, `opencode run` hangs on an open stdin pipe with zero
  output. Without `--auto`, a run whose spec reads anything outside
  the project dir gets its permission prompt auto-rejected and dies.
- **Stagger agent starts 30–60 seconds apart.** Concurrent starts
  share one global sqlite (`~/.local/share/opencode/opencode.db`) and
  fail with `database is locked` during init. Start one, wait until
  it's working, start the next.
- Prompt pattern — one line, the spec does the rest:

```sh
cd ~/metaos-B01
opencode run --auto "Read batches/B01.md in this repo and execute it exactly." < /dev/null
```

- The spec file is the whole instruction set: sources, contracts,
  parity list, commands, done criteria. If an agent asks a question
  the spec should have answered, that's a spec defect — note it in the
  batch spec for the next runner, don't just answer in the terminal.

### 6.5 Merge protocol (control window only)

1. Agent finishes a buildable step → pushes its `batch/B##` branch
   (commit format from the spec: `B##: <piece> — UNCOMPILED`).
2. Control window pulls the branch into a scratch checkout and runs:
   `cargo build -p <crate>` and `cargo test -p <crate>`.
3. Green at the Mac gate + parity pass → the batch's final commit is
   stamped `B##: <piece> PORTED`; control merges the branch to `main`
   (read the live tip first; rebase the branch onto the new tip if
   main moved — never force-push, never merge a red branch).
4. Red → errors go back into the agent's window (the agent that wrote
   the code fixes its own errors first, §7); the branch stays
   unmerged. `main` is never broken by a batch.
5. After merge: delete the branch, remove the worktree, the agent
   takes the next unclaimed batch.

## 7. Compile-error protocol

- **The writer fixes first.** Topology B: the agent compiles locally,
  so its first several error rounds never leave its window. Topology
  A: errors route **Milo (gate 1) → writer → Del's Mac (gate 2)**;
  gate-2 errors return to the writer the same way.
- **One change per fix commit.** An error report must point at one
  change; batch-fixes that touch five things get split before pushing.
- **Stall rule — no infinite loops.** The same error *class* three
  rounds in a row (e.g. the same trait-bound failure after three
  distinct fix attempts) = **park the batch**: write the blocker into
  the batch spec under a `## Blocker` note (error text, what was
  tried), post the BLOCKED one-liner, and move to the next batch.
  Pax (topology A) or the control window (topology B) reassigns or
  escalates to Del. A parked batch is not a failure of the plan — the
  Python fallback covers its piece, and the clock is spent where it
  can still land.
- Wrong-from-memory crate APIs are the top cause of wasted rounds:
  look APIs up (rustdocs MCP tools in topology A; docs.rs on the Mac)
  instead of guessing.

## 8. Timeline — the 12-hour clock

Clock starts **05:00 EDT, Fri 2026-10-30**; hard stop **17:00 EDT**.
Checkpoints are decision points, not status theater: at each one, the
named wave is either PORTED or the plan says what happens next.

| Time | Elapsed | Checkpoint |
|---|---|---|
| 05:00 | T+0 | Clock starts. Skeleton compile check at gate 1 (topology A) or locally (topology B). B01 + B03 claimed first. |
| 07:00 | T+2 | B01, B03 PORTED or parked-with-blocker; B02, B04 in flight. |
| 09:00 | T+4 | **Wave 1 decision point.** B01–B05 PORTED (assess path in Rust, ready for the round-trip proof) — or not (see below). |
| 10:30 | T+5.5 | Wave 2 closed (B08, B06). Rust stack wiring live with honest Rust/Python labeling. |
| 13:00 | T+8 | Wave 3 closed (B16–B23 PORTED or parked-with-blocker, each named). |
| 15:00 | T+10 | Wave 4 closed (B09–B15). B12a is the long pole — if it is not in by 15:00, it is parked and named, not chased. |
| 16:30 | T+11.5 | Wave 5 closed (B24–B31; CARRIED batches accounted). Final B07: full-workspace build + test on the Mac. |
| 17:00 | T+12 | **Hard stop.** Whatever is PORTED is the Rust state. The live round-trip proof (§1) runs on whatever Wave 1 produced; anything not PORTED stays Python. |

**The T+4 rule, stated plainly.** If Wave 1 is not PORTED by 09:00
EDT, the submission plan does not change and does not panic: **the
Python stack is the submission**, exactly as verified. The rebuild
continues only on Del's explicit word after that point, as
post-checkpoint work — it does not eat the demo/submission schedule
by default. No drama, no sunk-cost chase: the fallback was the plan
all along, not a consolation prize.

## 9. Exclusions and risks

**Exclusions (hard, from the clean-repo ruling).**

- `relay_common` and the muse-relay viewer/bus files (`bus.html`,
  `crew-board.html`, related relay assets) are **out** — they were
  excluded from the cleaned tree by design and are not ported, not
  re-added, not recreated. Behavior that touched them is ported from
  the in-tree callers; affected tests are marked exclusion-blocked.
- `relay/viewer.html` (Nuntius web viewer) is a static web asset —
  served, not ported.
- `native/` (the Swift MetaTrio app) and the web UI (`index.html`,
  `js/`, `styles.css`, `logo-studio.html`, `design/`) are **not Rust
  targets** and are untouched by this plan.
- `tests/` JS suites, `eval/`, `verify/`, `test-footage/` stay with
  their surfaces (read as spec where a batch spec says so).
- No Spark calls from any sandbox. Live model proof happens once per
  piece, on the Mac, through the guardrail ($75 cap; $0.2543 spent).
- No hardcoded hostnames, tokens, or credentials in any port — config
  resolves at runtime (`TRIO_UPSTASH_HOST` etc.), exactly as the
  Python does.

**Risks, ranked.**

1. **Intel volume (B09 70 files, B12 138).** The intel crate is the
   rebuild's long pole: one shared crate, six batches, the deepest
   test web. Mitigations: B12 pre-split (§5), B09's module layout
   agreed first, CARRIED sub-batches that cannot stall on compile
   errors, and the 15:00 park rule (§8).
2. **Integration tail.** Seams always cost more than the sum of the
   parts: shared types drifting, two batches defining the same shape.
   Mitigations: the shared-types rule (§4), B07 at *every* wave close
   (not just the end), and the wave order that puts the live wire
   (Wave 1) first while the clock is fresh.
3. **Local-fleet discipline (topology B).** The two fleet-killers are
   already known from hard experience: two agents in one worktree
   (clobber) and simultaneous OpenCode starts (sqlite lock).
   Mitigations are mechanical and non-optional: §6.2 worktree-per-agent,
   §6.4 staggered starts, control-window-only merges.
4. **Compile-round latency (topology A).** Every gate round-trip
   through the bus costs wall-clock. Mitigation: Milo's gate 1 absorbs
   the noise; only clean code reaches gate 2.
5. **Name-matched test assignment.** `os/tests/` files were assigned
   by the module they name; where names collide across areas the match
   is approximate (noted in BATCHES.md and the affected specs). A test
   that plainly exercises another batch's module gets said-so in the
   completion report and re-homed by B07 — never forced, never dropped.

---

*Plan ends. Execution state lives in the batch specs' completion
one-liners (bus / branch merges), not in this document — this plan is
not edited to track progress.*
