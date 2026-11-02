# `crates/relay` — changelog record (B192)

**Method limitation, stated up front:** this slice had file tools only, no
terminal, so `git log --follow -- crates/relay` could not be read. Nothing
below invents a hash, date, or author. It records what the checked-in records
and the current files evidence. To complete the task, run:

```
git log --oneline --follow -- crates/relay relay/relay.mjs
```

and append the commits under "Git trail (pending)" below.

## What the repo records say

| Stage | Evidence | What it says |
|---|---|---|
| B08 — the port task | `BATCHES.md:112`, `batches/B08.md` | `relay/relay.mjs` is the source; `crates/relay` is its Rust home. |
| T086 — the port order | `SUPER_PROMPT.md:304` | "Port `relay/relay.mjs` into `crates/relay` — done when the module is in the workspace build and behavior matches the source; state left: UNCOMPILED until gate 1 passes." |
| Workspace skeleton | `Cargo.toml:1-30` | `crates/relay` is a workspace member. |
| Live Node run | `MAC_RUN_REPORT.md:58` | The Node relay was up on :8787 and logged `Meta Nuntius relay listening`. |
| Current tree | `crates/relay/src/*.rs` | Eight source files: `lib`, `main`, `http`, `store`, `json`, `validation`, `notify`, `sha256`. No external crates. |

## What the current files evidence about the port

- The crate header describes the port as complete enough to state the wire
  format, endpoints, caps, and storage
  (`crates/relay/src/lib.rs:1-92`).
- The binary is wired: `main` resolves env, constructs `Relay`, binds, serves
  (`crates/relay/src/main.rs:11-29`).
- The HTTP layer carries route-level parity tests whose names mirror the Node
  suite (`crates/relay/src/http.rs:657-950`), plus unit suites in `validation`,
  `notify`, `store`, `json`, `sha256`.
- B191 (this pass) adds integration coverage in `crates/relay/tests/` for the
  refusal and edge paths; that is the only change this lane makes to the
  crate's test surface.

## Changes in this pass (B181-B192)

| File | Change |
|---|---|
| `crates/relay/src/lib.rs` | Doc fix: "torn final record" → any unparseable record (code skips all of them). |
| `crates/relay/src/store.rs` | Doc fixes: same reload wording; corrected the quoted upstream `since` guard (it is `!Number.isFinite(since) || since < -1`). |
| `crates/relay/tests/error_paths.rs` | New: refusal paths. |
| `crates/relay/tests/edge_cases.rs` | New: empty / maximum / duplicate / out-of-order. |
| `crates/relay/tests/gap_close.rs` | New: `json` module depth (3 → 13 tests). |
| `os-build/records/relay*.md` | New: this record set. |

No production logic changed in this pass.

## Git trail (pending)

Append the output of the command above here. Expected shape:

```
<sha> <subject>
<sha> <subject>
```

## Commit history (appended by coordinator, from git)

- 26ef5e6 2026-10-30 B08: crate docs from relay README (T089) — UNCOMPILED
- a4a22d7 2026-10-30 B08: restore full json.rs PORTED
- ec6d86d 2026-10-30 B08: http server slice PORTED
- ad96206 2026-10-30 B08: http server slice PORTED
- 15526dd 2026-10-30 B08: pure core (validation, notify id, room store) — UNCOMPILED
- a00be76 2026-10-30 B00 gate-1 fix: stub mains for relay + assess-server bins (Milo)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
