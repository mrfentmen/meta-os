# `crates/os-memory` — changelog record (B048)

What changed since the port began, from the evidence available in this
tree. **Limitation:** this worker had no terminal and could not run
`git log`; the commit-level history is owed by the coordinator. The
items below are read from the crate header, the batch map, and the
checked-in reports, and each names its source.

## Port start (B17)

- Batch B17 assigned `os/mos/memory.py` to `crates/os-memory`
  (`BATCHES.md:51`, `BATCHES.md:462`; `batches/B17.md:4-5`;
  `docs/RUST_REBUILD_PLAN.md:235`). The batch expects
  `cargo build -p os-memory` and `cargo test -p os-memory`
  (`batches/B17.md:33-34`).
- The crate header records the two deliberate adaptations:
  the Python CLI is ported as the library function `run_cli`, and the
  brief memory-depth functions are ported here because the batch map
  assigns their test file to B17 (`lib.rs:11-31`).
- The same header records the third adaptation: no `serde`, a minimal
  std-only JSON reader/writer for the journal shape (`lib.rs:32-40`).

## What the port added, in file order

1. JSON value + parser + serializer (`lib.rs:50-489`).
2. Store error, entry, outcome, read-all, mount, and ensure types
   (`lib.rs:492-602`).
3. Agent/key validation with the Python order and messages
   (`lib.rs:605-657`).
4. Journal read/append and the entry-shape check, including the
   bool-as-int quirk (`lib.rs:676-751`).
5. Write/read/history/list/read-all/mount/ensure (`lib.rs:764-966`).
6. The CLI-as-library port (`lib.rs:968-1161`).
7. The brief memory-depth slice and ET time formatting
   (`lib.rs:1155-1440`).
8. The in-crate test module (`lib.rs:1435-2296`).

## Test count

- 37 `#[cfg(test)]` tests are recorded for `os_memory` in the finish
  report (`OPENCODE_FINISH_REPORT.md:115`).
- The same file records the ported test-name roots: the store tests
  mirror `os/tests/test_os078_memory.py`, and the depth tests mirror
  `os/tests/test_intel_brief_memory_depth_caller.py`
  (`lib.rs:1430-1434`).

## Later edits visible in the tree

- The crate header still said "Skeleton only: no logic yet" after the
  port landed; that sentence was corrected in this pass to describe the
  B17 scope (`lib.rs:8-11`). The correction is documentation only.
- No other later behaviour change is visible in the source. The file is
  one port; there are no `TODO`, `FIXME`, or `unimplemented!` markers
  in `src/`.

## Owed by the coordinator

Run and append, from the repo root:

```
git log --oneline --follow -- crates/os-memory/src/lib.rs
git log --oneline --stat -- crates/os-memory
```

That output, not this file, is the commit-level changelog. This record
deliberately does not invent commit hashes or dates.

## Commit history (appended by coordinator, from git)

- 17848da 2026-10-30 B17 T100: complete crate docs for os-memory (Milo, gate 1)
- b40ad29 2026-10-30 B17: port memory service to crates/os-memory (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
