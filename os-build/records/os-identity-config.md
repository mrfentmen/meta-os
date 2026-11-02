# Config surface — crates/os-identity (B056)

Everything the crate reads from outside its own arguments. The crate reads
no files, opens no sockets, and defines no CLI flags. It has two
environment variables, three constructor arguments, and the system clock.

## Environment variables

Read by `Config::from_env` (`lib.rs:82-95`); nothing reads them implicitly
at load time — `CapabilityRegistry::new` takes the `Config` the caller
built (`lib.rs:293-295`).

| Variable | Read at | Default | Accepted values | Refusal when wrong |
|---|---|---|---|---|
| `MUSE_RELAY_CAPNS` | `lib.rs:84-88` | `muse-bus:cap` (`lib.rs:56`) | any non-empty string; used verbatim as the key prefix | none — an **empty** value is ignored and the default is kept |
| `MUSE_RELAY_CAP_STALE` | `lib.rs:89-93` | `900` seconds (`lib.rs:60`) | any text `i64::from_str` accepts, including negatives and `+` | none — an unparseable value is ignored and the default kept |

Consequences of the permissive cases:

- Negative `stale_after`: `now - updated <= stale_after` is true only for
  timestamps at least that far in the future, so virtually every real
  record is stale (`lib.rs:268-273`).
- `capns` containing `:` or `/`: keys are built by plain `format!`
  (`lib.rs:98-105`); no escaping and no refusal. The transport adapter
  must not quote the hash key (see gaps G3).
- Whitespace in `capns` is kept; `MUSE_RELAY_CAP_STALE` is `trim()`ed
  before parsing (`lib.rs:90`), `MUSE_RELAY_CAPNS` is not.

## Constructor arguments

| Argument | Meaning | Default | Validation |
|---|---|---|---|
| `store: S: CapStore` | hash/zset/job transport | none — caller supplies | trait methods return `StoreError` |
| `config: Config` | namespace + staleness | `Config::default()` if the caller uses it | none beyond the env rules above |
| `host: String` | value written into every record's `host` field | none; `""` is allowed and then omitted on write (`lib.rs:347`, `150`) | none |

`CapabilityRegistry::new` (`lib.rs:293-295`) performs no validation; a
bad config is accepted and shows up as behaviour, not as an error.

## Clock

`now_unix()` reads `SystemTime::now()` and truncates to whole seconds
(`lib.rs:275-281`); if the clock is before the Unix epoch it returns `0`
instead of panicking (`unwrap_or(0)`). `register` and `touch` take the
clock at call time (`lib.rs:342`, `366`); `find_for` and `prune_stale`
take it once per call (`lib.rs:440`, `463`).

## Files and flags

None. No `std::fs` use, no argument parsing, no feature flags in
`Cargo.toml` (which declares only package name/version/edition).

## Difference from the Python original

`os/mos/capabilities.py:25-26` evaluates both variables at import and
`int()` raises on a bad `MUSE_RELAY_CAP_STALE`, so a bad value stops the
whole process at load. The Rust port deliberately falls back instead
(`lib.rs:36-39` documents the choice) — a library should not fail to load
over one env var. This is a real behavioural difference, not a bug, and is
listed as gap G7 for an explicit decision.
