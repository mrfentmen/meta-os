# Layer 4 (Goose services) — running report

Branch: `buffy/layer1-goose-services`. Pax merges; I do not merge my own branch.
Order: `BUFFY_LAYER1_TASKS.md`, tasks B-L1-01 … B-L1-148. One task, one commit.
This file is updated as tasks land — it is the document the merge gate reads, so
it only ever contains what can be checked.

## The two facts that bound everything below

1. **No Goose toolchain on this machine.** `goose__toolchain_status` →
   `Goose toolchain: NOT FOUND / Looked for: goose (from PATH)`. Build
   instructions it gives: clone `aardappel/goose`, `cmake -B build
   -DCMAKE_BUILD_TYPE=Release -DGOOSE_BUILTIN_LIBS=all`. Until that exists there,
   **no task in this lane can honestly reach COMPILED**, and the work order's own
   rule says so.
2. **The kernel is at K1.** `kernel/src/main.rs` is the skeleton; nothing above
   K1 exists in the tree. So every service is written against a requirement, not
   against a running kernel.

Toolchain used for language grounding: `goose-mcp@1.1.0` (npm, publisher
`mrfentmen`, MIT), which is bundled from `aardappel/goose` @ `b781587`:
389 doc sections, 702 stdlib symbols, 57 keywords, 32 sample programs. Wired
into `/Users/test/Desktop/.agents/mcp.json` and called either as a session tool
(after a restart) or through `os-build/mcp/mcp_client.py`.

## Scoreboard

| Task | What | Status | How verified | What remains unverified |
|---|---|---|---|---|
| B-L1-01 | `services/MANIFEST.md`: 24 services + 9 libraries in build order | **DESIGNED** | Every service named is in the work order with its task number; `goose__toolchain_status` cited for the "nothing above WRITTEN" line | the list itself is a plan, not code |
| B-L1-02 | `os-build/layer1/SERVICE_CONTRACT.md` | **DESIGNED** | 8 Goose forms verified via `goose__*` (section ids in the doc): extern/export forms, trailing bool, optionals, no-heap model, `os` module's 25 symbols | whether any of it compiles; whether the kernel can call a Goose `export fn` at all |
| B-L1-03 | `services/bootlog/` — first service, source + README | **WRITTEN** | every symbol in the source is in the README's verification table with its `goose__` section id | compilation; `format` accepting these exact argument types; freestanding link |
| B-L1-04 | `services/time/` — clock core + self-check entry | **WRITTEN** | same standard; conversions are pure integer maths that can be checked by inspection | compilation; that `sys_ticks` is monotonic and cheap enough to poll |
| B-L1-05 | `os-build/layer1/BOUNDARIES.md` | **DESIGNED** | 10 requirements on L1–3, 9 offers to L5–6, 5 open questions, each marked | nothing — it is a hand-off sheet, and its honesty is the deliverable |
| B-L1-06 | this report | **DESIGNED** | — | — |

Legend, exactly as the work order defines it: DESIGNED (spec written),
WRITTEN (Goose source exists, symbols verified), COMPILED (build log from a real
toolchain), NOT BUILT (anything else).

## Findings worth the boss's attention

1. **Goose's `os` stdlib is a trap on our kernel.** It looks like a ready-made
   service layer: 25 functions including `write_stdout`, `read_line`, `sleep_ms`,
   `time_ns`. But per `spec#40` they are backed by `gs_os_*` functions declared in
   `src/runtime/runtime_ext.h` and **defined in `src/runtime/runtime_os.h`** —
   Goose's own runtime against a host operating system. On Meta OS there is no
   host, so `write_stdout` has nothing behind it. The layer therefore binds to
   kernel syscalls via its own `extern fn`s and does not `import os`. Recorded as
   open question Q-B-L1-3: if the kernel ever implements `gs_os_*`, a large part
   of this layer's file and process work becomes stdlib for free.
2. **No blocking key wait in the six-call shape.** `read_key` plus `yield` means
   the console polls. That is a CPU cost in the one service a user sits in front
   of. Q-B-L1-1 asks Rowan whether a blocking wait is possible.
3. **`yield` is the highest-value kernel call for this layer.** Almost every
   service's wait loop is `yield`-based; a no-op `yield` turns the whole layer
   into hard spins, and no test here would catch it until the scheduler exists.
4. **The largest unknown is not Goose, it is the link.** Whether Goose-generated
   C can link freestanding with no libc is the assumption everything past
   WRITTEN rests on, and nothing in this repo tests it. B-L1-75 says it plainly.

## Merge-gate notes for Pax

- Branch has one commit per task; no task commit touches another lane's files
  (`kernel/`, `os/worlds/`, `crates/`, `server/`, `js/` are untouched).
- The branch was cut from local `main` @ `0599478`, which is **6 ahead / 42
  behind** `origin/main`. The 42 commits include repeated replays of my research
  merge, so `main` upstream already holds `os-build/research/` content but not my
  branch's ancestry. Expect add/add conflicts on `os-build/research/LANE_NOTES.md`
  if this is merged blind — that file is mine and the upstream copy is stale
  (pre-docs-rs). Resolve in favour of my newer copy.
- `BUFFY_LAYER1_TASKS.md` arrives on this branch because local `main` never had
  it; it is the boss's file, copied unchanged.

## Queue

B-L1-07 onward: build layout, BootInfo types, the syscall module, then the
libraries every service needs. Next six are B-L1-07…B-L1-12.
