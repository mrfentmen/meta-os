# intel — Python behaviours not carried (B173)

The Python originals in `os/intel/` are still the live fallback. Each
item below is a behaviour the Rust port does not carry today, with the
Python source lines named. This is a list, not a port.

**G1 — Redis I/O and the record layer.**
`os/intel/store.py:1-120` documents every key and lifecycle; the write
and query functions live at `store.py:397-560` (alerts) and
`store.py:1013-1049` (notifications). Rust `Store` is in-memory
(`crates/intel/src/b09_core/store.rs:75-113`) and has no Redis client,
no connection/retry path, and no `put_*`/`get_*` raw layer. The key
builders are carried; the transport is not.

**G2 — Notification records and index.**
`os/intel/store.py:1013-1049` (`write_notify`, `query_notify`) implements
the general notification record, its validation, dedupe by key, and a
`count`/`last_seen` advance on re-notify. Rust builds `notify_key` and
`notify_index_key` (`store.rs:27-31`) but has no notification record
type, no write, and no query.

**G3 — Watchdog and boot-status records.**
`os/intel/store.py:639-730` carries `boot_status_key` and
`boot_status_is_stale`; the watchdog status record and the
`wd:<nick>` hash (last_seen, last_progress, claimed_jobs) are described
in `store.py:1-120`. Rust has no boot-status record, no staleness
check, no watchdog hash, and no selfcheck record.

**G4 — Spend ledger shape.**
Python stores the spend ledger as a list of JSON entries
(`os/intel/store.py:120` onward). Rust appends `ts:cents:label` lines
to a single string and sums the colon field
(`store.rs:153-170`). A Python reader cannot parse the Rust form.

**G5 — Bus snapshot.**
`os/intel/ingest.py:87-163` reads a room's bus pages and builds a
snapshot with room counts and the latest timestamp. Rust
`ingest::store_messages`/`messages_from_cursor` work on an in-memory
`Vec<Message>` and `snapshot` returns only a message count
(`crates/intel/src/b09_core/ingest.rs:24-52`). No bus reader, no room
filter, no timestamp summary.

**G6 — CLI entrypoints.**
`os/intel.py:141` (`main`) is the intel command surface; the drill
modules each have their own `main` (for example
`os/intel/drills/watchman_boot.py:86`,
`os/intel/watchdog.py:1670`, `os/intel/join.py:381`,
`os/intel/skills_loader.py:280`). Rust `b09_core::cli` carries argument
types and the approval rule only (`cli.rs:11-55`); there is no binary
target and no dispatch to any subcommand.

**G7 — Join config writes.**
`os/intel/join.py` validates the machine/room/key and writes the join
config with 0600 permissions (`join.py:381` and the validators at
`join.rs`'s source). Rust carries the validators and announcement text
(`crates/intel/src/b09_core/join.rs:16-63`) but performs no write and
has no permission path.

**G8 — Spark transports.**
`os/intel/spark_client.py:685` (`complete`) contains the agent and HTTP
transports with the job-queue envelope, lease heartbeat, retry budget,
and token accounting. Rust keeps the request/result shapes, the cap
check, and the injected `Transport` trait
(`crates/intel/src/b11_spark/spark_client.rs:27-152`); only
`StubTransport` exists, so no real completion can be made.

**G9 — Real signature verification.**
`os/intel/trust.py` verifies HMAC-SHA256 v2. Rust `recompute_sig` is an
FNV-1a stand-in (`crates/intel/src/b14_trust/trust.rs:44-58`). The gate
order and badge policy are carried; the cryptography is not.

**G10 — Watchdog and drill drivers.**
`os/intel/watchdog.py` (1670-line `main` at `watchdog.py:1670`) and the
21 `os/intel/drills/*.py` modules have executable entrypoints and
subprocess/systemd interactions. Rust carries drill logic as pure
`run`/`run_drill` functions with injected traits
(`crates/intel/src/b12a_drills/mod.rs:1-32`); no entrypoint, no systemd,
no subprocess runner beyond the shared `audiocheck::SystemRunner`.

**G11 — Mind loader and remaining B11 modules.**
`os/intel/mind_loader.py` is mapped in `b11_spark/mod.rs` but the port
carries `mind_image`, `skills_loader`, `spark_agent`, and
`spark_client` surfaces only; the loader's directory/mount path is not
carried beyond `skills_loader::mount_skill_dirs`
(`crates/intel/src/b11_spark/skills_loader.rs:45`).

**G12 — Devpack pack loading.**
`os/intel/devpack.py` loads and compares the checked-in JSON pack;
Rust `b13_devpack` shapes the four payloads and declares `PACK_FILES`
(`crates/intel/src/b13_devpack/mod.rs:18-23`) but has no loader that
reads the fixtures and compares them byte-for-byte.

**G13 — Timer sweep and launch run.**
`os/intel/timer_sweep.py` and `os/intel/launch_run.py` are listed in
`crates/intel/src/b14_trust/mod.rs`; the modules exist, but the Python
launch path's child-spawn and the sweep's timer/cgroup behaviour are
not exercised by any Rust entrypoint (no binary, no runner).

**G14 — Python-template parity in explanations.**
`os/intel/explanations.py` allows Spark polish of the rendered text.
Rust `polish_explanation` takes a client and returns the template when
the client is absent or fails
(`crates/intel/src/b09_core/explanations.rs:77-100`); there is no real
client, so the polish path is offline-only.
