# `crates/intel` — failure drill (B177)

What breaks first when the crate's inputs stop arriving. Read from the
code, not from a run: every claim below names the branch that decides
it. The commands are the drill another agent can run on the Mac; the
expected lines are what the code must produce, not a recorded pass.

Machine rule: one crate at a time, `cargo test -p intel -j1`. Do not run
the workspace.

## The input chain

```
bus messages ──> b09_core::ingest ──> SnapshotView ──> b10_brief::sections
                                                        │
alerts ──> b09_core::store ──> b10_brief::alerts         ├─> b10_brief::brief ──> Store::put_brief
                                                         └─> b10_brief::dispatch
jobs ──> b09_core::gate / capability ──> journal
jobs ──> b14_trust::trust ──> refusal records
brief ──> b11_spark::spark_client ──> Completion (or a typed SparkError)
```

## What breaks first, in order

| # | Input that stops | First code path | What an operator sees |
|---|---|---|---|
| 1 | New bus messages | `ingest::messages_from_cursor` (`ingest.rs:40-49`) | **No error.** It returns `SnapshotView { messages: [], cursor: None }`. The snapshot is empty, so every downstream section is empty. Silence, not a failure. |
| 2 | Cursor that no longer exists | `ingest.rs:41-44` | Cursor lookup fails, `unwrap_or(0)` starts at the beginning. The reader silently re-reads the store from page 0 instead of refusing a stale cursor. |
| 3 | Disk/process lifetime for the store | `b09_core::store::Store` (`store.rs:75-90`) | The store is in memory. A restart loses every brief, alert and index entry. Nothing reports the loss; the next read is simply empty. |
| 4 | Alert explanation / dedupe key | `store::validate_alert` (`store.rs:53-67`) | The only hard refusal in the alert path: `"alert: missing explanation"` or `"alert: missing dedupe_key"`. The write is rejected, the previous record is untouched. |
| 5 | Prompt file | `brief::load_brief_prompt` (`brief.rs:183-194`) | **No error.** Unreadable or unknown prompt returns `""`; the brief is composed with no system text. A missing fixture cannot fail a brief, so it also cannot be detected from the brief. |
| 6 | Spark endpoint / transport | `spark_client::TransportKind::from_env` (`spark_client.rs:53-61`) | `SparkError::NotConfigured("unknown SPARK_TRANSPORT: ...")` **before anything is sent**. With a declared transport but no reply, `StubTransport::complete` returns `NotConfigured("stub has no reply")`. |
| 7 | Spend headroom | `spark_client::complete` (`spark_client.rs:129-137`) | HTTP only: `SparkError::Budget("spend cap reached: X >= Y")`. Agent transport is not capped here. |
| 8 | A signed job's key | `trust::claim_decision` (`trust.rs:90-136`) | Refusal reasons in order: `"signature absent"`, `"legacy v1 signature, v2 required"`, `"untrusted signer"`, then `verify_signature`'s `"signature bad"` / `"signature expired"`. The job is not claimable; a refusal record is the output. |
| 9 | A launch directory | `launch_run::check_preconditions` (`launch_run.rs:40-57`) | `"argv is empty, nothing to run"`, `"launch directory missing: <dir>"`, or `"launch.json missing"`. Verification runs after those and refuses with `"launch refused, verification failed: <errors>"`. |
| 10 | A well-formed plan | `dispatch::parse_plan` (`dispatch.rs:39-56`) | `"missing goal"`, `"unknown fields: ..."`, `"job needs key + title"`. Then `check_file_overlap` refuses `"file overlap on <f>: <a> vs <b>"`, and `check_dep_graph` refuses `"unknown dep <d> in <job>"`. |

The important shape: **the ingestion and prompt paths fail silent; the
record and trust paths fail loud.** A drill that only watches for errors
will miss the first two.

## Drill A — starve the reader (safe, no services)

```sh
cargo test -p intel -j1 --test gap_close
```

Expected: every test passes; the names include
`empty_store_is_an_empty_snapshot`,
`cursor_not_found_starts_at_the_first_message`,
`page_caps_at_page_size`, `duplicate_ids_are_not_stored`,
`empty_ids_are_skipped`, `cursor_on_last_message_returns_nothing`.
The assertions encode the observations in rows 1-2 above. If one fails,
stop: the ingest contract changed and every downstream section is
reading a different snapshot than this record says.

## Drill B — declare no transport

```sh
cargo test -p intel -j1 --test b11_parity
```

Expected: pass. The cases include an unconfigured client erroring
before send and a stub with no reply returning `NotConfigured`. If a
test ever shows a canned completion, the no-fake rule is broken —
that is a stop-the-line finding, not a flake.

## Drill C — remove the signature

```sh
cargo test -p intel -j1 --test b14_parity
```

Expected: pass. The cases pin `signature absent`, untrusted signer,
and expired signature refusals, plus the timer sweep's expired-lease
handling. A pass here does not prove a boot; it proves the refusal
branches still refuse.

## Drill D — change the key prefix mid-process

1. Build a `Store`, write one alert.
2. Set `MUSE_RELAY_KEY_PREFIX=drill` in the same process.
3. Query the alert by id and by `alert_index_key()`.

Expected from the code: `get_alert(id)` still finds the record because
it is keyed by id in the `alerts` map, but `strings` and `zindex` now
name `drill:intel:...` while the first write used `muse-bus:intel:...`.
The split is the failure this drill is for; see the config record's
finding 1. This is read-only evidence — do not "fix" it in a test.

## What this drill does not prove

- No QEMU, no bus, no Redis, no Spark call. It proves the refusal and
  empty-state branches, not a live intel run.
- It does not prove the cross-batch adapters exist; the drills use the
  `deps.rs` traits. See `intel-callers.md`.
