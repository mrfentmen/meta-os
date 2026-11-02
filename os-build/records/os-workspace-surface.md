# Public surface inventory — `crates/os-workspace`

Every name the crate exports, one line each, with where it is used today
(`main` @ `6d8d54e`). "Tests only" means the only caller is inside this
crate's tests; **no name here has a caller outside the crate**.

## Types

| Name | Shape | Used by |
|---|---|---|
| `ArtifactStoreError` (`lib.rs:54`) | tuple struct, pub `String` | every store function; `Display`/`Error`/`From<io::Error>` impls at `56-66` |
| `GitError` (`lib.rs:72`) | tuple struct, pub `String` | every gitops function; `Display`/`Error` impls at `74-82` |
| `JsonValue` (`lib.rs:90`) | enum: `Null`, `Bool`, `Int(i64)`, `Float(f64)`, `Str`, `Array`, `Object(BTreeMap)` | manifests, `attach`, CLI output |
| `ArtifactRecord` (`lib.rs:720`) | 8 pub fields | `deposit`, `list_artifacts`, `read_manifest` conversion |
| `DepositOutcome` (`lib.rs:742`) | `record`, `new_commit` | `deposit`, `deposit_str`, CLI |
| `VersionEntry` (`lib.rs:749`) | `version`, `commit` | `history`, CLI `show` |
| `AttachedArtifact` (`lib.rs:759`) | `path`, `reference`, `version`, `sha256` | **UNUSED** — no constructor and no caller; `attach` builds the same JSON directly (`see os-workspace.md` finding 3) |
| `ReviewSummary` (`lib.rs:1484`) | `branch`, `base`, `files`, `stat`, `commits`, `commit_count` | `review_branch`; no external caller |

## Constants

| Name | Value | Used by |
|---|---|---|
| `STORE_ROOT_DEFAULT` (`lib.rs:713`) | `/var/lib/metaos/artifacts` | **UNUSED** in the crate; image scripts create the same path (`os/os/build-image.sh:127-138`), but nothing passes it here |
| `MANIFEST_NAME` (`lib.rs:715`) | `manifest.json` | `manifest_path`, `deposit` |

## `JsonValue` methods

| Name | Signature | Used by |
|---|---|---|
| `obj` (`102`) | `Vec<(&str, JsonValue)> -> JsonValue` | `attach`, `read_manifest`, CLI, tests |
| `get` (`111`) | `&self, key -> Option<&JsonValue>` | `deposit`, `read_artifact`, `attach`, tests |
| `as_str` (`119`) | `&self -> Option<&str>` | callers/tests |
| `as_i64` (`128`) | `&self -> Option<i64>` | `record_from_value`, tests |
| `as_array` (`136`) | `&self -> Option<&Vec<JsonValue>>` | `attach`, tests |

## Store functions

| Name | Signature (abridged) | Used by |
|---|---|---|
| `validate_job_id` (`840`) | `&str -> Result<String, ArtifactStoreError>` | `deposit`, `list_artifacts`, `read_artifact`, `history`, `attach` |
| `validate_name` (`866`) | `&str -> Result<String, ArtifactStoreError>` | `deposit`, `read_artifact`, `history` |
| `deposit` (`1012`) | `(&Path, &str, &str, &[u8], &str) -> Result<DepositOutcome, _>` | CLI, tests |
| `deposit_str` (`1118`) | same over `&str` | tests only |
| `list_artifacts` (`1129`) | `(&Path, &str) -> Result<Vec<ArtifactRecord>, _>` | `attach`, CLI `list`, tests |
| `read_artifact` (`1158`) | `(&Path, &str, &str, Option<u64>) -> Result<Vec<u8>, _>` | CLI `read`, tests |
| `history` (`1218`) | `(&Path, &str, &str) -> Result<Vec<VersionEntry>, _>` | CLI `show`, tests |
| `attach` (`1243`) | `(&Path, &str, &JsonValue) -> Result<JsonValue, _>` | tests only |
| `run_cli` (`1279`) | `(&[String], &mut dyn Write, &mut dyn Write) -> i32` | tests only; no `[[bin]]` |

## Gitops functions

| Name | Signature (abridged) | Used by |
|---|---|---|
| `is_repo` (`1457`) | `&Path -> bool` | `review_branch` |
| `current_branch` (`1463`) | `&Path -> Result<String, GitError>` | `approve_merge` |
| `clean_tree` (`1470`) | `&Path -> Result<bool, GitError>` | `approve_merge` |
| `branch_exists` (`1477`) | `&Path, &str -> bool` | `review_branch`, `approve_merge`, `worktree_add` |
| `review_branch` (`1494`) | `(&Path, &str, &str) -> Result<ReviewSummary, _>` | tests only |
| `approve_merge` (`1544`) | `(&Path, &str, &str) -> Result<String, _>` | tests only |
| `reject_branch` (`1583`) | `(&str, &str) -> Result<String, GitError>` | tests only |
| `worktree_add` (`1591`) | `(&Path, &str, &Path) -> Result<PathBuf, _>` | tests only |
| `worktree_remove` (`1619`) | `(&Path, &Path) -> Result<(), GitError>` | tests only |

## Public-surface counts

- Exported types: 8 (1 unused: `AttachedArtifact`).
- Exported constants: 2 (1 unused: `STORE_ROOT_DEFAULT`).
- Exported functions: 23 (9 store/CLI, 9 gitops, 5 `JsonValue` methods).
- Functions with a caller outside the crate: **0**.
- Functions used only by tests: `deposit_str`, `attach`, `run_cli`,
  `review_branch`, `approve_merge`, `reject_branch`, `worktree_add`,
  `worktree_remove` (8).
