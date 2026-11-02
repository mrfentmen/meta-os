# Callers — crates/os-identity (B055)

Searched the repo for `os-identity`, `mos.capabilities`, `capabilities.*`
and the crate's exported names. Result: **no Rust crate depends on
`os-identity` today.** The only Rust reference is a doc comment naming it
as the future home of a seam. The live callers are Python, and they call
the original `os/mos/capabilities.py`, not this crate.

## Rust callers

None. `Cargo.toml` lists `crates/os-identity` only as a workspace member
(root `Cargo.toml:15`); no `Cargo.toml` declares it as a dependency. The
only `use os_identity::…` statements are inside the crate package itself
(`src/lib.rs` tests via `super::*`, plus the three `tests/*.rs` files added
by this pass). No production crate references it.

### Seam that expects this crate but cannot use it as-is

`crates/os-boot/src/cli.rs:82-98` defines `CapabilitiesBackend` and says
"The real implementation lives in the B18 crate (`os-identity`)." The
shape it expects does not match the crate:

| Expectation (`os-boot/src/cli.rs`) | `os-identity` reality | Mismatch |
|---|---|---|
| `register(&mut self, nick, caps: &[String], roles, max_jobs, dm_secret) -> Result<(), String>` (`cli.rs:87-94`) | `register(&mut self, nick, capabilities: &[&str], roles, max_jobs: i64, dm_secret, info) -> Result<bool, RegistryError>` (`lib.rs:312-320`) | caps type, extra `info` arg, return type |
| `agents(&self) -> HashMap<String, AgentRecord>` (`cli.rs:96`) using `os-boot`'s own `AgentRecord` (`cli.rs:44-80`) | `agents(&self) -> Result<Vec<(String, os_identity::AgentRecord)>, StoreError>` (`lib.rs:398`) | container, error, and a different `AgentRecord` type |
| no touch/unregister/find_for/prune_stale on the seam | crate exports all four (`lib.rs:362-478`) | seam is narrower than the crate |

**Flag:** a caller expecting direct delegation would need an adapter that
converts `&[String]→&[&str]`, drops `info`, maps two `AgentRecord` structs,
turns `Vec<(String, _)>` into a `HashMap`, and maps `RegistryError` to
`String`. The current docs' claim that the implementation simply "lives
in" `os-identity` understates the work.

`crates/os-supervisor/src/overseer.rs:17-22` explicitly does **not**
import `os-identity` (nor `os-jobs`/`os-workspace`); it routes the
capability registry through its own `OverseerBackend` seam. No caller
expectation to check there yet.

## Python callers (the live original)

These call `os/mos/capabilities.py` directly and define what the port must
eventually satisfy:

| Caller | Calls | Expects |
|---|---|---|
| `os/mos/overseer.py:76-77` | `find_for(reqs)`, `get(nick)` | list of nicks; dict record or `{}` |
| `os/mos/reconcile.py:85` | `prune_stale()` | sorted removed nicks |
| `os/mos/cli.py:36-43` | `register(...)`, `agents()` | truthy return; `{nick: dict}` |
| `os/mos/worker.py:75-82` | `register(...)`, `touch(nick)` | bool |
| `os/intel/spark_agent.py:179-187` | `register(...)`, `touch(nick)` | bool |
| `os/intel/spark_client.py:423-424` | `find_for([cap])`, `get(nick)` | list; dict or `{}` |
| `os/intel/ingest.py:162` | `agents()` | `{nick: dict}` |
| `os/intel/watchdog_load_check.py:340-342` | `register(...)` | `True` |
| `os/tests/test_mos_capabilities.py:17-80` | all of the above | the authoritative parity cases |

## Visual reader (not a Rust caller)

`bus.html:3743` reads the same hash shape (`caps`, `max_jobs`, `updated`,
`host`) in JavaScript for the bus page. It is a reader of the stored data,
not a caller of this crate, but it pins the field names the crate must
keep writing.

## Mismatches flagged

1. `os-boot`'s seam signature and record type do not match this crate
   (table above) — adapter needed before it can be wired.
2. Python callers expect `agents()` as a mapping and `get()` as a dict;
   the Rust API returns a `Vec` and a typed struct, so a port boundary
   must convert or every caller must change.
3. No production Rust path exercises `CapabilityRegistry`; all Rust
   coverage today is the crate's own `#[cfg(test)]` module
   (`lib.rs:574-938`).
