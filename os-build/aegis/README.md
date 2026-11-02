# META AEGIS — section D: the three services (Buffy, 2026-11-02)

Status: **WRITTEN and TESTED on the host.** Host-side node services, not kernel code, not a
sweep. No vulnerability data has been fetched by anything in this directory, and
`DRILL.json` says so in its first line. The spec's own proof rule is the one applied here:
a sweep counts when its report names manifests, source versions, findings and ledger lines.
No sweep has run, so nothing here claims one.

## What exists

| item | module | API | evidence |
|---|---|---|---|
| D1 manifest collector | `aegis/manifests.mjs` | `collectManifests(root)` → path + ecosystem for 8 manifest types | `tests/aegis-manifests.test.mjs` (7) |
| D2 findings record | `aegis/findings.mjs` | `appendFinding` / `readFindings` / `summarize` | `tests/aegis-findings.test.mjs` (6) |
| D3 watch-target pack | `aegis/watch-targets.mjs` | `repoTipTargets(repo)` / `buildWatchTargets({repos,pages,files})` | `tests/aegis-watch.test.mjs` (7) |

Total: **20/20 tests pass**. The watch test does not re-implement the poller's shape — it
imports `pollWatch` from `agents/runtime.mjs`, so a change to the runtime's target format
breaks this test instead of silently producing targets nothing reads.

## Drill, measured

```
$ node os-build/layer1/aegis_drill.mjs
aegis drill aegis-drill-mvz36qt6
  manifests   23  {"cargo":22,"npm":1}
  scanned     371 dirs, skipped 5, capped 0, symlinks 0
  record      1 info, torn 0 (scratch)
  watch       2 targets, quiet poll 0 change(s), deliberate page write detected: 1
  report      os-build/aegis/DRILL.json
  exit        ok
```

The drill writes its findings record to a scratch directory on purpose: a drill is not a
sweep, and a security-looking record on `main` would be worse than no record. `DRILL.json`
holds the full manifest inventory, the watch target list (repo-relative, so it is portable),
and the quiet/vs-changed poll results.

The 23 manifests are the tree as it stands, not a guess: 22 `Cargo.toml` (workspace crates,
kernel, userspace) and the root `package.json`. Five dependency/VCS directories were skipped
and counted; nothing hit the depth cap; no symlinks were present.

## Decisions worth naming

- **No network, and the test enforces it.** `tests/aegis-manifests.test.mjs` fails if the
  collector imports `http`, `https`, `net`, `dns`, `child_process` or calls `fetch(`. Aegis's
  first build is allowed to contact OSV only through the boss's own MCP servers; that call
  does not belong in an inventory walk.
- **Caches are skipped, `vendor` is not.** `node_modules`, `target`, `.venv` and friends hold
  manifests that arrived over the network, not the ground being watched. Vendored code ships,
  so it is walked.
- **A depth cap is reported.** `capped` carries an exact count and a sample, so a truncated
  inventory cannot pass for a complete one.
- **Symlinks are never followed.** A link can leave the tree or loop; both turn a bounded walk
  into an unbounded one. The count is reported.
- **Findings are append-only, with no update or delete export.** `ts` is set by the recorder,
  not accepted from the caller: a writer that can backdate a record makes an unordered record.
  A torn line is skipped and counted, and the one-byte separator fix from the run ledger is
  repeated here, so a crash mid-append cannot fuse the next record into the torn one.
- **A repo tip is two files.** `HEAD` plus the checked-out ref: a commit moves the ref, a
  checkout moves `HEAD`, and watching one of them makes the watch miss the other case. HEAD
  refs that climb out of `.git` are refused; worktree/submodule `.git` files are refused
  rather than half-supported.

## What is NOT built (do not read this file as more than it is)

- **No OSV / CISA KEV sweep.** The data calls are Pax's lane through the boss's MCP servers.
  D1 only produces the inventory a sweep would consume.
- **No secret-hygiene counts, no unicode-confusable checks, no Aegis face.** Those are the
  rest of the spec's first build and none of them are in this section.
- **No registry entry.** Aegis is not yet an `agents/registry.json` entry with a budget and a
  watch cadence; D3 produces the target list, the registration is still open.
- **No kernel work.** Nothing here runs in-kernel; it is host-side until the kernel grows
  real spawn/kill, and the agent layer's contracts are designed to move down unchanged.

## Run it

```
node --test tests/aegis-manifests.test.mjs tests/aegis-findings.test.mjs tests/aegis-watch.test.mjs
node os-build/layer1/aegis_drill.mjs
```
