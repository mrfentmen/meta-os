# Gaps — what `crates/os-workspace` does not carry from its Python originals

Source: `crates/os-workspace/src/lib.rs` on `main` @ `6d8d54e`.
Python: `os/mos/artifact_store.py` and `os/mos/gitops.py` (line numbers from the
same tree). This is a task list, not a port: nothing here was implemented.

## Behaviour gaps

**G1 — `dict(current)` extras are dropped.**
`artifact_store.list_artifacts` returns `dict(current)` (`artifact_store.py:217-222`),
so any field a manifest entry carries beyond the eight known ones survives into
`list` and `attach` output. Rust `record_from_value` (`lib.rs:961-981`)
reconstructs only the eight known fields, so extras are invisible to callers
even though `deposit` preserves them on disk (`lib.rs:1055-1072`).
Task: decide whether to return the whole entry object (JSON) or add an `extra`
map; do not widen `ArtifactRecord` silently.

**G2 — no runtime type refusals.**
Python rejects non-bytes data with `artifact data must be bytes or str`
(`artifact_store.py:167`) and rejects non-string ids/names at
`artifact_store.py:87-109`. Rust types make those refusals compile-time
(`lib.rs:1012-1018`, `840`, `866`). A caller that depended on catching the
error at runtime must handle a compile error instead. No work item unless a
dynamic caller appears.

**G3 — deposit result shape.**
Python returns one dict that includes `new_commit` (`artifact_store.py:154-214`);
Rust returns `DepositOutcome { record, new_commit }` (`lib.rs:742-747`,
`1012-1116`), and only the CLI re-adds `new_commit` to the JSON
(`lib.rs:1320-1330`). Task for callers: use `.new_commit`, not the record key.

**G4 — no default `base`.**
Python `review_branch`/`approve_merge` default `base="main"`
(`gitops.py:56`, `76`). Rust requires both branch and base
(`lib.rs:1494`, `1544`). Task: caller passes `"main"` explicitly, or a wrapper
adds the default.

**G5 — different error types for the same message.**
`reject_branch` raises `ValueError` in Python (`gitops.py:96-102`) and returns
`GitError` in Rust (`lib.rs:1583-1589`). Message text matches. Task: callers
that match on exception class must match `GitError`.

**G6 — latest-read error class.**
Python lets a missing on-disk file raise a raw `OSError` from `open`
(`artifact_store.py:247-249`); Rust maps it to `ArtifactStoreError` via the
`From<io::Error>` impl (`lib.rs:64-66`, `1198-1200`). Task: callers that
distinguish `OSError` from `ArtifactStoreError` need the message, not the class.

**G7 — no JSON `input_text` path.**
Python `_git(root, args, input_text=None)` can feed stdin
(`artifact_store.py:69-85`). No caller uses it, and Rust `store_git`
(`lib.rs:770-796`) has no such parameter. Not a behaviour loss today; noted so
a future caller does not assume it exists.

**G8 — no runnable program.**
Python `artifact_store.py` is a module with `main()` and an `if __name__`
entry (`artifact_store.py:309-354`). Rust has no `[[bin]]`; the CLI is
`run_cli(&[String], &mut dyn Write, &mut dyn Write)` (`lib.rs:1279-1407`).
Task: add a binary target that reads `std::env::args` and writes
`io::stdout()`/`io::stderr()` if a runnable store is wanted.

## Fidelity gaps in the JSON helper

**G9 — parser strictness differs from Python.**
Python `json.load` accepts `NaN`, `Infinity`, `-Infinity` and rejects raw
control characters and leading zeros. Rust `JsonParser` (`lib.rs:149-387`)
does the opposite: it rejects the non-finite tokens and accepts raw control
bytes and leading zeros. Manifests written by this crate are finite and
escaped, so the difference only bites on a hand-edited manifest or a foreign
writer. Task: decide whether to match Python exactly; if so, add the
non-finite literals and reject raw controls/leading zeros.

**G10 — U+007F is escaped in Rust, literal in Python.**
`json_escape` (`lib.rs:400-435`) emits `\u007f` for DEL; Python
`json.dump(ensure_ascii=True)` leaves DEL as a literal byte
(`artifact_store.py:133-141`). Byte-compat claim in the crate header is
qualified accordingly. Task: match Python if byte-identical manifests matter.

**G11 — non-finite serialization round-trip.**
`json_dump` writes `NaN`/`Infinity` tokens (`lib.rs:459-470`), matching Python's
default dumps; its own parser then rejects those tokens (G9). Python's parser
accepts them. Task: same decision as G9.

**G12 — timeout message text.**
Python raises `git failed: Command ... timed out after 60 seconds`
(`artifact_store.py:77-80`); Rust raises `git failed: git command timed out`
(`lib.rs:683-690`, `783-790`). Meaning is the same; text is not. Task: match
the text only if a caller parses it.

## Structural differences, not behaviour losses

**G13 — internal re-validation.** Python `_job_dir` re-validates the job id
(`artifact_store.py:111-113`); Rust `job_dir` assumes the caller validated
(`lib.rs:888-890`). Every public entry point validates first, so no path can
reach `job_dir` with a bad id. Keeping the assumption is safe; noting it so a
future internal caller does not skip validation.

**G14 — Python only.** `_git`'s `input_text` and `main()`'s
`except (OSError, ValueError)` umbrella (`artifact_store.py:347`) have no Rust
equivalent; Rust handles each error at its source. No work item.

**G15 — CLI `--author` divergence (deliberate).**
Python crashes with `IndexError` when `--author` is last (`artifact_store.py:324`);
Rust returns usage and exit 2 (`lib.rs:1300-1310`). This is a documented
improvement, not a gap to close, unless exact crash parity is demanded.
