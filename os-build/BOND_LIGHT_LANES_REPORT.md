# BOND — the light lanes, executed (2026-11-02)

Base: `main` @ `4bdf3ef` (pulled clean). Lane doc:
`os-build/BOND_LIGHT_LANES.md`. Machine: this Mac, 8GB lane rules
followed — no `cargo build/check` over the workspace, no QEMU, no
model work.

Everything below names the file and the command that proves it.
A claim without a run is labelled CODE-INSPECTED, not VERIFIED.

## Lane 1 — Node and Python suites, extended

New files:

- `tests/face-apps.test.mjs` — 8 tests (dependency-free face apps).
- `tests/surfaces-edges.test.mjs` — 10 tests (escaping, empty/malformed
  input, ladder cap, hostile timeline value).
- `tests/server-queue-edges.test.mjs` — 12 tests (every typed QueueError
  path, deterministic job id, no fabricated assessment).
- `tests/agents-ledger-edges.test.mjs` — 9 tests (registry refusals,
  ledger round-trip, torn line vs unterminated complete line, late kill).
- `tests/queue-python/test_envelope_edges.py` — 11 tests (envelope edge
  cases; node-gated cases skip only when node is absent).

Wired into `package.json`'s `test` script.

Evidence:

```
node --test tests/face-apps.test.mjs tests/surfaces-edges.test.mjs \
  tests/server-queue-edges.test.mjs tests/agents-ledger-edges.test.mjs \
  tests/kernel-records.test.mjs
# tests 46 / pass 46 / fail 0

python3 -m pytest tests/queue-python -q   # 139 passed (includes the 11 new)
python3 -m pytest tests/custos -q         # 125 passed
python3 -m pytest tests/officina -q       # 49 passed
```

Full suite, and the baseline that separates old red from new red:

```
npm test (this tree):        2048 tests, 1993 pass, 55 fail
npm test (clean HEAD clone): 2002 tests, 1947 pass, 55 fail
```

The same 55 failures exist on unmodified `main` (all native/Swift
tests, none touched by these lanes). The 46 added tests all pass.

## Lane 2 — face apps as dependency-free HTML/JS

Files: `os-build/face/notes.html`, `calendar.html`, `calculator.html`,
`settings.html`, `files.html` (new), `shell.html` (dock wiring).

- Notes: multiple notes, create/delete, legacy single-note value
  migrated, localStorage `metaos-notes`.
- Calendar: month grid + selected-day panel with add/delete event,
  `metaos-calendar`.
- Calculator: existing arithmetic kept, keypad + keyboard, `aria-live`
  display, no `eval`.
- Settings: theme, reduced motion, clear-all-`metaos-*` with confirm.
- Files: lists the real `metaos-*` browser records with size, export and
  delete; honest empty state; says plainly these are browser records, not
  disk files.
- Shell dock: Notes/Calendar/Files/Calculator/Settings all open their
  `.html` page; no host binary launch remains for these five.

Evidence: `tests/face-apps.test.mjs` (8/8) checks no external resource,
no `eval`, storage keys, honest empty state, and the dock targets.
CODE-INSPECTED: viewport meta and max-width layouts present in each file;
no browser screenshot was taken (not requested).

## Lane 3 — kernel and OS records

New files:

- `os-build/USERSPACE_ABI.md` — syscalls 0–5 specced from
  `kernel/src/user.rs` (dispatch at `kernel/src/user.rs:90`), arguments,
  returns, the 4096-byte write cap, the `u64::MAX` sentinel, the
  `user bad syscall {n} refused` arm, worked examples, and the FROZEN
  `syscalls.rs` ruling.
- `os-build/KERNEL_BEHAVIOUR.md` — allocator, task lifecycle, fault path,
  each with `file:line` ranges; disagreements listed as findings.
- `os-build/BOOT_LOG_INDEX.md` — every entry in `os-build/logs/` indexed
  by name and line count, with the K5-no-banner and K7-no-banner notes.
- `tests/kernel-records.test.mjs` — holds the records to the code:
  every dispatched number is specced, the refusal/sentinel/cap are
  present, every logs entry is indexed and every indexed path exists.

Evidence: included in the 46/46 node run above.

## Lane 4 — parity reading + Goose typecheck

Files: `os-build/tools/parity_lane.sh`, `os-build/PARITY_READING.md`.

```
./os-build/tools/parity_lane.sh   # exit 1
PASS  product parity: tests/product-parity.test.mjs        (6/6)
FAIL  bus-tools parity: os/tests/test_bustools_parity.py
SKIP  goose typecheck: goose not on PATH
SKIP  cargo test -p intel --test b13_parity -j1 (opt-in)
```

- Product parity (web vs native lists/config) passes 6/6.
- Goose typecheck could not run: `goose` is not installed on this
  machine. The script reports SKIP, never PASS.
- Bus-tools parity is BLOCKED by an external dependency, not by drift:
  `os/tests/test_bustools_parity.py:32` requires
  `~/workspace/skills/muse-bus-relay/bin/bus-send`, which is absent.
  Fixed test, unmodified.
- The Rust parity tests are compile-dependent; the script runs one crate
  with `-j1` only when `PARITY_RUST=1`, and names the skip otherwise.

## Lane 5 — clean-clone light gate

Files: `os-build/tools/light_gate.sh`, `os-build/LIGHT_GATE.md`.

```
./os-build/tools/light_gate.sh   # exit 1
28 ok, 2 fail, 2 warn
```

What passed: fresh `--no-hardlinks` clone, same commit, identical tracked
file list (2710) and identical committed HEAD tree, the K1/K2/K3-fault/
K4/K5/K6 boot-log grep lines, K7-no-claim, lane sources present, and all
three Python suites inside the clone.

Two real failures, both pre-existing on clean HEAD and NOT introduced by
this work:

1. `gates.md` K3 line: `K3-boot.txt` has `K3 timer: 10 ticks…` but no
   `META OS - milestone K3` line, so the documented grep cannot match.
2. `npm test` in the clone: the same 55 native/Swift failures measured on
   the baseline clone (2002 tests, 1947 pass).

Warnings: dirty worktree (gate compares committed trees, as stated), and
`gates.md` says "K7: NO LOG" while `K7-boot.txt` exists (it carries no K7
banner, so the wording is stale, not the file).

The gate prints `SKIP cargo` and `SKIP QEMU` explicitly. A green light
gate is not a green full `gate.sh`.

## Findings filed, not fixed

- 55 native/Swift tests fail on unmodified `main` (test names captured in
  the run above; all `native-*` / native cross-checks).
- `os-build/gates.md:20` says "K7: NO LOG"; `K7-boot.txt` exists but has
  no K7 banner — the correct claim is "no K7 banner".
- `os-build/gates.md` K3 banner line does not match `K3-boot.txt`.
- Kernel records raised by lane 3: `readkey.rs` imports `sys_read_key`,
  which `lib.rs` does not define; `build.rs` still builds only
  hello/sleeper/crasher; `tasks.rs` header is stale (says UNWIRED and
  claims no Cargo.lock); `boot-test.sh:52` greps a stale K2 banner;
  `MERGED-boot.txt` is empty.
- Bus-tools parity cannot run without the external
  `~/workspace/skills/muse-bus-relay/bin` scripts.
- Goose is not installed, so the Goose typecheck stage is SKIP.
- `pytest tests/queue-python tests/custos tests/officina` in one process
  collides on two `test_pack.py` modules; the gate runs one directory per
  invocation. Pre-existing harness limitation, not a test failure.

## Not run (named, per the lane)

- `cargo build/check` over `crates/` — 8GB lane.
- QEMU/UTM against the face image — 8GB lane.
- Anything holding a model — 8GB lane, boss-parked.
- Full `os-build/gate.sh` — needs the toolchain/QEMU stages above.
