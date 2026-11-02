# Gaps — what crates/os-identity does not carry from its Python original (B053)

Source: `os/mos/capabilities.py` (the whole file) against
`crates/os-identity/src/lib.rs`. Each entry is a task with the source
lines named. None of these were ported in this pass; the list is the
deliverable.

## G1 — No bus transport

Python performs every operation through `relay_common.api_get` HTTP calls:
`hgetall` (`capabilities.py:37-42`), `hset`/`zadd` (`44-71`), `del`/`zrem`
(`84-89`), `zrange` (`97-100`), job hash reads (`122-136`). The Rust crate
stops at the `CapStore` trait (`lib.rs:200-217`) and ships only
`MemoryStore`.

**Task:** write the `CapStore` implementation over the bus HTTP transport,
including the URL shape and quoting below. **Done when:** a parity test
runs the same scenario against both implementations and the stored hash +
index bytes match.

## G2 — No import-time configuration

Python evaluates `CAPNS` and `STALE_AFTER` once at import
(`capabilities.py:25-26`); tests patch the module attribute directly.
Rust has per-instance `Config` (`lib.rs:64-105`) and `from_env`
(`lib.rs:82-95`).

**Task:** decide and document the process-wide configuration story for the
port (constructor injection is currently the only path). **Done when:** the
caller contract is stated; no code change needed if per-instance stays.

## G3 — Quoting rules are not specified for the adapter

Python leaves the hash **key** unquoted (`_key`, `capabilities.py:29-30`)
but URL-quotes hash **field values** (`65-70`) and every **zset member**
(`72`, `91`, `97-99`); it unquotes index members on read (`100`). The Rust
trait takes plain strings and says quoting is a transport detail
(`lib.rs:21-26`) without stating the key exception.

**Task:** write the quoting table in the transport adapter's docs: key =
raw (including `:` and `/` in a nick), field values = quote, zset member =
quote, zrange result = unquote. **Done when:** an adapter test uses a nick
containing `:` and `/` and `get` still finds the record.

## G4 — `max_jobs` coercion is narrower

Python does `str(int(max_jobs))` (`capabilities.py:54`), so floats and
numeric strings are accepted. Rust takes `i64` (`lib.rs:317`).

**Task:** decide whether callers may pass non-integers; if yes, add a
fallible constructor/coercion at the boundary. **Done when:** the accepted
input domain is named in the API docs and tested.

## G5 — `active_claims` per-job failure behaviour differs

Python catches only the jobs-index read (`capabilities.py:127-132`); a
per-job hash read failure propagates (`133-136`). Rust folds all job reads
into `CapStore::job_claims` and returns 0 on any error
(`lib.rs:414-423`).

**Task:** either split `job_claims` so a per-job error can propagate, or
accept the 0 fallback as a documented deviation. **Done when:** the choice
is recorded in the behaviour record and a test pins it.

## G6 — Empty `MUSE_RELAY_CAPNS` semantics

Python accepts `""` as the namespace (`capabilities.py:25`); Rust ignores
empty and keeps the default (`lib.rs:84-88`).

**Task:** match Python or document the deliberate difference. **Done
when:** one of the two is pinned by a test.

## G7 — Bad `MUSE_RELAY_CAP_STALE` does not fail at load

Python's `int(...)` raises at import (`capabilities.py:26`); Rust silently
falls back to 900 (`lib.rs:89-93`).

**Task:** if a silent fallback is the intended library behaviour, state it
in the public config docs and test it without mutating process env (make
the parser take a lookup function). **Done when:** the invalid-value case
has a named test.

## G8 — `agents` shape differs

Python returns `{nick: dict}` (`capabilities.py:97-112`); Rust returns
`Vec<(String, AgentRecord)>` (`lib.rs:398-412`). Order is the same (index
order), but every dict-style caller needs a mapping layer.

**Task:** provide the conversion at the port boundary, or keep the Vec and
document it for callers. **Done when:** the chosen shape is in the caller
contract.

## G9 — No mutable module state

Python tests mutate `capabilities.CAPNS` at runtime
(`os/intel/load_check.py:252-285`, `os/intel/e2e2.py:157-194`). Rust
configuration is immutable per registry instance.

**Task:** no port needed if per-instance config is the target; record the
migration note for test harnesses that patch `CAPNS`. **Done when:** the
note is in the integration guide.

## G10 — Clock resolution

Python `_fresh` takes a float `now` and truncates with `int()`
(`capabilities.py:114-120`); Rust uses whole seconds (`lib.rs:268-281`).
The staleness boundary is identical at second resolution.

**Task:** none unless a caller depends on sub-second freshness; record the
difference. **Done when:** noted in the behaviour record (done, "Freshness
and matching").
