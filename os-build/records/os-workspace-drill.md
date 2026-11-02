# Failure drill — `os-workspace`

Written from `crates/os-workspace/src/lib.rs` on `main` @ `6d8d54e`. The drill
answers one question: **when an input stops arriving, what breaks first, and
what does the caller see?**

Baseline before any drill:

```sh
cargo test -p os-workspace -j1
```

Expected: all in-file tests plus `error_paths`, `edge_cases`, `gap_close`
pass. If the baseline is red, stop — the drill is measuring the wrong thing.

## Drill A — deposits stop arriving

1. Create a store with one deposit (any test or caller; `deposit` at
   `lib.rs:1012`).
2. Call `list_artifacts`, `read_artifact(None)`, `read_artifact(Some(1))`,
   `history`, `attach`.
3. Expected: all five still succeed. No timer, watchdog, or background thread
   exists in the crate (`grep` for `thread::spawn` finds only the git reader
   threads at `lib.rs:660-670`), so nothing notices the silence and nothing
   degrades.
4. First thing that would notice is outside this crate: a caller's own
   deadline.

## Drill B — `git` disappears

Remove `git` from `PATH` for the process, then:

| Call | First break | Message |
|---|---|---|
| `deposit` (new store) | `ensure_repo` → `git init` (`945-951`) | `git is not available on this machine` (`783`) |
| `deposit` (existing store) | `git add` (`1094`) | same message (`783`) |
| `read_artifact(None)` | **no break** — manifest + file read only (`1166-1200`) | — |
| `read_artifact(Some(n))` | `version_commits` → `git log` (`1145-1151`) | `git is not available on this machine` (`783`) |
| `history` | same `git log` | same |
| `list_artifacts` | **no break** | — |
| `attach` | **no break** (uses `list_artifacts`) | — |
| every gitops function | first `git -C` call (`1417-1455`) | `git not found on PATH` (`1430`) |

Note the asymmetry: the store says "not available on this machine", gitops
says "not found on PATH". A caller matching messages must handle both.

## Drill C — manifest corrupts

Write `{not json` into `<root>/jobs/<job>/manifest.json`, then:

| Call | Result |
|---|---|
| `list_artifacts` | `manifest unreadable: ...` (`907`) |
| `read_artifact(None)` | same — **the latest read fails even though the bytes are on disk**, because the manifest is read first (`1166-1170`) |
| `read_artifact(Some(n))` | same |
| `history` | same |
| `attach` | same |
| `deposit` | same, at `read_manifest` before the artifact file is written (`1024`) |

If the manifest parses but `artifacts` is not an object, the message is
`manifest has an unexpected shape` (`914-918`). Recovery is manual: there is
no repair function.

## Drill D — commit fails after the manifest is written

`deposit` writes the manifest **before** it commits (`1091-1110`). A commit
failure therefore leaves:

- the artifact bytes on disk (renamed at `1049`),
- the manifest claiming version N with the new digest,
- git history still at version N-1.

The deposit call returns the git error (`797`). The next
`read_artifact(Some(N))` fails with `has N-1 versions, no vN` (`1196`) even
though the manifest says N. This is the first inconsistency a caller can see.

Reproduce by making the commit step fail (e.g. a `git` wrapper on `PATH` that
exits 1 only for `commit`), then run the deposit twice: first succeeds, second
returns the git error and the manifest still moves.

## Drill E — disk full or root unwritable

| Point | Result |
|---|---|
| `fs::write` of the artifact `.tmp` (`1048`) | `ArtifactStoreError` with the I/O message; manifest unchanged |
| `fs::write` of the manifest `.tmp` (`925-937`) | artifact already renamed, manifest old: latest read returns new bytes under the old digest |
| `git init` cannot create `<root>/.git` (`945-951`) | `git init failed: ...` |

The artifact-before-manifest ordering in the second row is the same in Python
(`artifact_store.py:195-214`); it is a ported failure mode, not a regression.

## Drill F — git hangs

The store kills git after 60 s (`lib.rs:781`, `650-711`); gitops after 120 s
(`1427`). Expected: the call returns `git failed: git command timed out`
(store) or `git ... timed out` (gitops), the child is killed
(`676-690`), and the store's files are left as in drill D or E depending on
where the call stopped.

## What this drill cannot show

No booted image, no service caller, and no concurrent writer. The crate has no
locking (`os-workspace-config.md`, "Not configurable"), so two simultaneous
deposits to one job are outside this drill and are not claimed safe.
