# Config surface — `crates/queue-store`

Everything the crate reads from outside itself, from
`crates/queue-store/src/lib.rs` on `main`, 2026-11-02. There are no
flags, no config file, and no network client in this crate.

## Environment variables

| Variable | Read at | Default | Accepted form | Refusal when wrong |
|---|---|---|---|---|
| `TRIO_JOB_NS` | every `namespace()` call (`lib.rs:102-104`) | `trio` | any string, including `""` | none. An empty value is used as-is (keys start with `:`); no error is raised |
| `TRIO_UPSTASH_HOST` | `resolve_upstash_host_from_env()` (`lib.rs:164-166`) | `""` | bare host (`store.example`) or full URL (`https://store.example/path`) | `TrioStoreConfigError` when this and the credential URL both yield no host (`lib.rs:158-161`); the message names `TRIO_UPSTASH_HOST` |

`resolve_upstash_host(env_host, credential_rest_url)` is the pure
function behind the env read (`lib.rs:147-162`). Its second argument is
**not** an env var: a caller may pass a credential REST URL; the
provided `resolve_upstash_host_from_env` always passes `None`.

## Files

| File | Who chooses it | Default | Refusal when wrong |
|---|---|---|---|
| SQLite database file | the caller, via `SqliteStore::open(path)` (`lib.rs:274-287`) | none — there is no default path | `rusqlite::Error` from `open`; the error is returned to the caller |
| `js/products.js` | not read at runtime — the three product records are embedded (`lib.rs:8-12`, `37-84`) | n/a | n/a; drift is not detected at runtime |

The SQLite backend creates `kv`, `hashes`, and `zsets` on first open
(`lib.rs:275-284`). It does not read or write any other file.

## Not part of this crate's config (Python-only today)

| Python setting | Source | Why it is absent here |
|---|---|---|
| `RELAY_URL` base override | `trio_store.py:160-176` | no Upstash/HTTP path in Rust |
| `TRIO_STORE=local` force | `trio_store.py:357` | no `open_store()` selector in Rust |
| `custom.upstash` credential record | `trio_store.py:63-97` | credential lookup not ported; caller can pass a URL manually |

## Behaviour worth knowing

- `namespace()` re-reads the environment on every call, so a process
  that changes `TRIO_JOB_NS` mid-run moves its keys. Python captures
  the namespace once at import (`trio_store.py:47`).
- `TRIO_UPSTASH_HOST` is trimmed before parsing; a whitespace-only
  value falls through to the credential argument and then to the
  typed error.
- Nothing in the crate reads an API token. The credential token is
  never needed because there is no Upstash transport.
