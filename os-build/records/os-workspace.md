# Record — crate `os-workspace`, from the code

Scope: `crates/os-workspace` on `main` @ `6d8d54e` (2026-11-02), after the B19
port. Every claim cites `crates/os-workspace/src/lib.rs` (or `Cargo.toml`) by
line range. The Python originals are cited only in the gaps record.

Status words: **LIVE** = implemented and exercised by a test in the crate.
**UNWIRED** = implemented but no production caller in this repository.

## What it is

One library crate, one source file, no binary target (`Cargo.toml:1-5`;
`src/lib.rs:1-38`). It ports two Python modules:

| Area | Python source | Rust range | State |
|---|---|---|---|
| Artifact store (OS-083) | `os/mos/artifact_store.py` | `lib.rs:698-1405` | LIVE in tests; UNWIRED from a program |
| Safe gitops | `os/mos/gitops.py` | `lib.rs:1407-1631` | LIVE in tests; UNWIRED from a program |
| JSON value/parser/serializer | std-only helper for manifests | `lib.rs:90-553` | LIVE |
| SHA-256 | std-only helper for digests | `lib.rs:555-633` | LIVE |
| Timed git runner | std-only process helper | `lib.rs:641-711` | LIVE |

The crate writes nothing on load and has no `main`; the CLI is the library
function `run_cli` (`lib.rs:1279-1407`).

## Artifact store — what it does

Layout under an explicit store root: `jobs/<job_id>/<name>` plus
`jobs/<job_id>/manifest.json` (`lib.rs:713-715`, `888-896`).

- `deposit` (`1012-1116`): validates job id and name, creates the store repo on
  first use (`945-951`),  writes the artifact through a `.tmp` sibling and
  rename (`1048-1049`), writes the manifest the same way (`925-943`), then
  `git add` + `git commit` with a fixed identity
  (`metaos-artifact-store <artifact-store@metaos.local>`, `1095-1110`).
  Version numbers are per artifact name, starting at 1 (`1050`, `1055`).
  A byte-identical redeposit returns the current record with `new_commit:
  false` and makes no commit (`1030-1038`).
- `deposit_str` (`1118-1127`) is `deposit` over UTF-8 bytes.
- `list_artifacts` (`1129-1143`): manifest records for one job, sorted by name
  (BTreeMap order), empty for a job with no manifest.
- `read_artifact` (`1158-1216`): latest bytes read from disk, or a numbered
  version mapped to its commit and read with `git show` (`1200-1214`), so a
  numbered read does not depend on the file currently on disk.
- `history` (`1218-1241`): version records oldest first from the artifact's
  git log (`1145-1151`).
- `attach` (`1243-1277`): returns a copy of a job record with one entry per
  artifact appended to its `artifacts` array; the input record is not mutated
  (`1248-1252`, `1267-1275`).
- `run_cli` (`1279-1407`): `deposit`, `list`, `read`, `show`; every failure is
  `ARTIFACT_STORE_ERROR: <message>` on stderr and exit 2 (`1289-1292`).

## Safe gitops — what it does

- `is_repo` (`1457-1461`), `current_branch` (`1463-1468`), `clean_tree`
  (`1470-1475`), `branch_exists` (`1477-1482`) are thin `git` queries.
- `review_branch` (`1494-1542`): guards, then three-dot `diff --stat`,
  `diff --name-only`, and two-dot `log --format=%h %s`; returns
  `ReviewSummary` (`1484-1492`).
- `approve_merge` (`1544-1581`): guards, checks out the base if needed, merges
  with `--no-ff -m "Merge <branch> (MOS approved)"`, returns `rev-parse HEAD`.
  There is no force-push path anywhere in the file.
- `reject_branch` (`1583-1589`): returns `REJECTED <branch>: <reason>` and
  deletes nothing.
- `worktree_add` (`1591-1617`) / `worktree_remove` (`1619-1629`): detached
  worktrees, forced removal.

The git runner (`650-711`) drains stdout/stderr on reader threads, polls
`try_wait`, and kills the child on timeout. Store calls use 60 s (`770-796`);
gitops calls use 120 s (`1417-1445`).

## What it refuses

| Input | Refusal | Line |
|---|---|---|
| Empty job id | `job id must be a non-empty string` | `843` |
| `.`, `..`, slash, backslash, NUL in a job id | `job id must be a single path segment` | `849` |
| Job id outside `[A-Za-z0-9._-]` | `job id holds characters outside [A-Za-z0-9._-]` | `857` |
| Empty artifact name | `artifact name must be a non-empty string` | `869` |
| Absolute name, backslash, NUL | `artifact name must be a relative POSIX path` | `874` |
| Empty, `.` or `..` name segment | `artifact name must not contain empty, . or .. segments` | `882` |
| Broken manifest JSON | `manifest unreadable: <io/json error>` | `907-909` |
| Manifest not an object with an `artifacts` object | `manifest has an unexpected shape` | `914-918` |
| Unknown artifact | `no artifact '<name>' for job '<job>'` | `1175` |
| Version < 1 | `version must be a positive integer` | `1190` |
| Version above the commit count | `artifact '<name>' for job '<job>' has <n> versions, no v<k>` | `1196` |
| `attach` on a non-object record | `job record must be a dict` | `1253` |
| `git` missing in the store | `git is not available on this machine` | `783`, `821` |
| `git` nonzero in the store | `git <first arg> failed: <stderr tail>` | `797`, `830` |
| `git` missing in gitops | `git not found on PATH` | `1428-1430` |
| `git` timeout in gitops | `git <args> timed out` | `1430` |
| `git` nonzero in gitops | `git <args> failed: <last 500 chars of stderr>` | `1447-1451` |
| Review with branch == base | `refusing to review base against itself` | `1503` |
| Review/merge of a non-repo (review only) | `not a git repo: <path>` | `1500` |
| Unknown branch | `unknown branch: <b>` | `1507`, `1559`, `1603` |
| Merge with branch == base | `refusing to merge base into itself` | `1550` |
| Merge with a dirty tree | `working tree dirty — refusing to merge` | `1554` |
| Worktree path already exists | `worktree path already exists: <path>` | `1598` |
| Rejection with a blank reason | `rejection needs a reason` | `1585` |
| CLI shape errors | usage line, exit 2 | `1284-1287`, `1399-1401` |

## What it writes down

Only the store: `<root>/jobs/<job_id>/<name>`, `<root>/jobs/<job_id>/manifest.json`,
and git objects under `<root>/.git`. The manifest is JSON with sorted keys,
2-space indent, and a trailing newline (`925-943`). Each deposit is one commit
whose message is `job <job_id>: deposit <name> v<version> by <author>`
(`1106-1112`). A merge writes the fixed merge message (`1572-1578`).
The CLI writes records to stdout: one JSON object for `deposit`, one per
artifact for `list`, raw bytes for `read`, `v<n> <sha>` lines for `show`
(`1305-1394`). The shaped examples are in `os-workspace-records.md`.

## Failure ordering (recorded, not fixed)

- `deposit` writes the manifest **before** it commits (`1091-1110`). If the
  commit fails, the manifest claims a version that git history does not have.
  Python has the same order (`artifact_store.py:195-214`), so this is a ported
  oddity, not a new bug.
- A corrupt manifest fails `read_artifact` even for the latest version, because
  the manifest is read first (`1166-1170`).
- A missing on-disk artifact fails only the latest read; numbered reads still
  come from git (`1200-1214`).

## Findings (doc versus code; docs fixed here where the code is right)

1. **`lib.rs:1` said "skeleton (B00)" and `10-12` said "Skeleton only: no logic
   yet."** False: over 2,200 lines, 39 in-file tests, and both Python modules
   are ported. Header rewritten in this pass.
2. **The header claimed byte-exact Python JSON in all cases
   (`32-37`).** The serializer matches for ordinary manifest values, but the
   parser is stricter and `json_escape` differs on U+007F; header qualified and
   the cases listed in `os-workspace-gaps.md` (G12-G13).
3. **`AttachedArtifact` (`759-768`) is never constructed.** `attach` builds
   the same shape directly as `JsonValue` (`1261-1271`). Doc corrected to say
   so; the type is unused surface (see `os-workspace-surface.md`).
4. **`STORE_ROOT_DEFAULT` (`713`) is never read.** Every function takes an
   explicit root; doc corrected to call it informational.
5. **`list_artifacts`/`attach` drop unknown manifest fields.** Python returns
   `dict(current)` (`artifact_store.py:217-222`) and keeps them. Recorded as a
   gap (G4), not silently changed.
6. **No production caller and no binary.** `run_cli` is referenced only by
   tests (`1689-2280`); nothing imports `os_workspace` outside the crate. The
   parity tests still call this crate a skeleton — stale caller expectation
   (see `os-workspace-callers.md`).

## Tests

In-file: 39 `#[test]` cases in `mod tests` (`1639-2281`), covering SHA-256
vectors, validation, deposit/list/read/history/attach, JSON round-trip,
CLI flows, and gitops review/merge/reject/worktrees.

Integration (this pass): `tests/error_paths.rs` (15 cases),
`tests/edge_cases.rs` (9), `tests/gap_close.rs` (9). None claims a run here;
the coordinator runs `cargo test -p os-workspace -j1`.
