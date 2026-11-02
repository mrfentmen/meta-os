# `crates/stack` — callers (B199)

## Rust callers

**None.** No crate in the workspace depends on `stack`, no `use stack`
appears outside the crate, and `cargo` sees it only as a workspace
member. Search evidence:

- `Cargo.toml:26` lists `crates/stack` as a member (membership, not a
  dependency).
- `crates/stack/Cargo.toml` has no `[dependencies]` section, so nothing
  could consume it through the workspace graph.
- `os-build/aegis/DRILL.json:112` names `crates/stack/Cargo.toml` as a
  drill target — a file path, not an API caller.

## Non-Rust references and what each expects

| Reference | Expectation | Met? |
|---|---|---|
| `batches/B06.md:4-5` | a port inside `crates/stack`, modules mirroring the source layout, Rust tests named after the Python/Node roots | Partly: one module, tests added in this pass; no Python/Node test-name mapping |
| `batches/B06.md:23` | same ports and env contract as `run-stack.sh`, **including `TRIO_UPSTASH_HOST`** | **No**: the script never sets that variable; the crate correctly omits it, so the batch text is stale |
| `SUPER_PROMPT.md:168-171` | `cargo build -p stack` clean, `cargo test -p stack` parity with the script | **Unverified here**: no terminal in this slice; no live runner exists |
| `os-build/records/relay-callers.md:16-21` | the crate models the relay as a host process with argv, `RELAY_PORT`, and a viewer URL | **Yes** (`src/lib.rs:186-191`, `150-152`, `238`) |
| `os-build/records/relay-callers.md:62-72` | the relay is "supervisor-managed" through this crate | **No**: `crates/stack` only returns a plan; it starts and supervises nothing (`src/lib.rs:10-21`) |
| `run-stack.sh` | the live stack: it starts the four services itself | **Not wired**: the script does not use the crate and still runs the Node/Python originals (`run-stack.sh:74-92`) |

## Flagged mismatches

1. No runner consumes `plan()`. Until one exists, the crate is dead
   code relative to the live stack, and `run-stack.sh` remains the only
   working composition.
2. `relay-callers.md` describes supervision (`kill`, traps) that the
   crate explicitly does not do. The record should say "planner, no
   supervisor" once the owner re-reads it.
3. `batches/B06.md:23` expects `TRIO_UPSTASH_HOST` in the plan; the
   script does not set it. Do not add it to the crate to satisfy the
   batch text.
