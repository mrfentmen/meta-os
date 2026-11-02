# Config surface — `crates/os-workspace`

Everything the crate reads, with its default and its refusal. There is **no
configuration file and no environment variable**: the only `std::env` use is
`temp_dir()` in tests. All configuration is arguments and constants.

## Constants

| Name | Value | Read by | Default | If wrong |
|---|---|---|---|---|
| `STORE_ROOT_DEFAULT` (`lib.rs:713`) | `/var/lib/metaos/artifacts` | nothing in the crate | — | none; it is informational (see `os-workspace.md` finding 4) |
| `MANIFEST_NAME` (`lib.rs:715`) | `manifest.json` | `manifest_path` (`892-896`), `deposit` (`1104`) | fixed | cannot be overridden |
| store timeout (`lib.rs:781`) | 60 s | every store git call | 60 s | hardcoded; a slow git is killed and the call errors |
| gitops timeout (`lib.rs:1427`) | 120 s | every gitops git call | 120 s | hardcoded; same |

## Library arguments

| Argument | Where | Default | If wrong |
|---|---|---|---|
| `root` | every store function, first parameter | none | created on first deposit (`945-951`); an unwritable root is an `ArtifactStoreError` carrying the I/O message |
| `job_id` | `deposit`, `list`, `read`, `history`, `attach` | none | the three validation refusals (`843-857`) |
| `name` | `deposit`, `read`, `history` | none | the three name refusals (`869-882`) |
| `data` | `deposit(&[u8])` | none | typed; no runtime check |
| `author` | `deposit` | `""` | blank becomes `"unknown"` (`1080-1084`) |
| `version` | `read_artifact` | `None` = latest | `0` or negative: `version must be a positive integer` (`1190`); above count: `has <n> versions, no v<k>` (`1196`) |
| `record` | `attach` | none | non-object: `job record must be a dict` (`1253`) |
| `branch`, `base` | gitops | none | `unknown branch: <b>` (`1507`, `1559`, `1603`); equal: the two "against itself" refusals (`1503`, `1550`) |
| `path` | `worktree_add` | none | exists: `worktree path already exists: <path>` (`1598`) |
| `reason` | `reject_branch` | none | blank: `rejection needs a reason` (`1585`) |

## CLI surface (`run_cli`, `lib.rs:1279-1407`)

Command shape: `artifact_store <deposit|list|read|show> ROOT JOB [ARGS]`
(`1284`). No defaults for `ROOT` or `JOB`.

| Flag / word | Command | Default | If wrong |
|---|---|---|---|
| `deposit` | needs root, job, name, source path | — | fewer than 5 words: usage, exit 2 (`1400`) |
| `--author <nick>` | `deposit` | blank → `"unknown"` | flag last with no value: usage, exit 2 (`1300-1310`) |
| `list` | exactly 3 words | — | wrong arity: usage, exit 2 |
| `read` | root, job, name | latest | missing artifact: `ARTIFACT_STORE_ERROR: no artifact ...`, exit 2 (`1374-1378`) |
| `--version <n>` | `read` | latest | flag last: usage, exit 2 (`1364-1368`); non-integer: `invalid literal for int() with base 10: '<v>'`, exit 2 (`1369-1373`); negative: positive-integer error, exit 2 (`1364`) |
| `show` | exactly 4 words | — | wrong arity: usage, exit 2 |
| unknown command | — | — | usage, exit 2 (`1399-1401`) |

Every store error printed by the CLI is prefixed `ARTIFACT_STORE_ERROR: `
(`1289-1292`).

## External programs and files

| Surface | Where | Default | If wrong |
|---|---|---|---|
| `git` on `PATH` | store (`783`, `821`), gitops (`1428-1430`) | inherited `PATH` | store: `git is not available on this machine`; gitops: `git not found on PATH` |
| `safe.directory=*` | store calls only (`774`, `812`) | passed every time | no fallback; without it git may refuse a foreign-owned root |
| commit identity | `deposit` (`1099-1101`) | fixed `metaos-artifact-store <artifact-store@metaos.local>` | never read from global git config |
| merge identity | `approve_merge` (`1566-1580`) | **none passed** | a repo with no `user.name`/`user.email` fails the merge with git's own error |
| `<root>/jobs/<job>/manifest.json` | `read_manifest` (`898-923`) | absent = empty manifest | unreadable: `manifest unreadable: ...`; wrong shape: `manifest has an unexpected shape` |
| `<root>/jobs/<job>/<name>` | `read_artifact` latest (`1198-1200`) | — | missing: `ArtifactStoreError` with the I/O message |
| source file | CLI `deposit` (`1311-1316`) | — | unreadable: `ARTIFACT_STORE_ERROR: <io error>`, exit 2 |
| `<root>/.git` | `ensure_repo` (`945-951`) | created on first deposit | git failure surfaces from `git init` |

## Not configurable

- Retry count: none; a failed git call is one error, no retry.
- Concurrency/locking: none; two concurrent deposits to the same job can race
  on `manifest.json` (last rename wins) and on git's index lock.
- Log level / verbosity: none; output is the CLI's fixed lines.
- Base branch default: none; gitops requires an explicit `base`
  (see `os-workspace-gaps.md` G4).
