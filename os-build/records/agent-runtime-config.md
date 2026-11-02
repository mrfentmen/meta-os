# `crates/agent-runtime` — config surface (B104)

Every environment variable, flag, and file the crate reads, with the
default and the refusal when it is wrong.

## Environment variables

**None.** A scan of `src/lib.rs` finds no `std::env` use. The crate does
not read `TRIO_JOB_NS`, `TRIO_UPSTASH_HOST`, `TRIO_LOCAL_DB`,
`TRIO_RELAY_URL`, `SPARK_API_KEY` or any other variable.

Those variables belong to the layers around it:

| Variable | Owner | Default | Effect on this crate |
|---|---|---|---|
| `TRIO_JOB_NS` | `queue-store` | `trio` (`queue-store/src/lib.rs:120-122`) | the `JobStore` the caller passes already carries its namespace; this crate never reads the variable |
| `TRIO_UPSTASH_HOST` | `queue-store` (caller/config) | none -> typed error (`queue-store/src/lib.rs:150-166`) | selects the backend before an `Agent` exists |
| `TRIO_LOCAL_DB` | Python resident (`server/queue/trio_agent.py:70-72`) | `server/queue/trio-queue-local.db` | no Rust equivalent in this crate |
| `TRIO_RELAY_URL` | Python resident (`trio_agent.py:86-88`) | unset = no hook | not read; the relay hook is not wired (gap G3) |

## Flags

**None.** There is no binary target and no argument parsing
(`crates/agent-runtime/Cargo.toml:1-4`). The Python CLI flags
(`--once`, `--lease`, `--nick`, `--schema`, `--poll-interval`) live in
`trio_agent.py:335-342` and are not carried (gap G7).

## Files

**None read, none written.** The crate takes bytes (`&[u8]`), returns
`Value`, and writes only through the injected `JobStore`
(`lib.rs:60-62`, `lib.rs:91-155`). It creates no temp file; the Python
original does for the transport (`trio_agent.py:264-277`, gap G5).

## Caller-supplied configuration

The crate is configured entirely through the `Agent` struct
(`lib.rs:64-69`) and the `Generator` implementation.

| Field / parameter | Type | Default in this crate | Where the Python default lives | Refusal when wrong |
|---|---|---|---|---|
| `Agent.nick` | `String` | none — caller must set it | `"trio-agent"` (`trio_agent.py:340`) | no validation; an empty nick is written to the claim key as-is (`lib.rs:78`) |
| `Agent.lease` | `u64` seconds | none — caller must set it | `300` (`trio_agent.py:339`) | no validation; `0` makes the claim expire almost immediately, which is legal and surprising |
| `Agent.jobs` | `JobStore<B>` | none — caller builds it | store opened in `Agent.__init__` (`trio_agent.py:121-139`) | store errors happen before the crate is entered |
| `Agent.gen` | `G: Generator` | none — caller supplies it | `spark_gen.generate` (`trio_agent.py:170-177`) | a generator that panics is not caught (gap G6) |
| `serve_job(jid)` | `&str` | none | job ids come from `open_job_ids()` (`trio_agent.py:325`) | an unknown id claims a new job key and then fails R1 (`lib.rs:92-98`) |
| `Generator::generate(..., correction)` | `Option<&str>` | `None` on the first call | `None` (`trio_agent.py:170`) | the generator's own error becomes R5/R6 |

## Process inputs it does read

| Input | Use | Source |
|---|---|---|
| `SystemTime::now()` | epoch millis for `completed_at` | `lib.rs:25-31` |
| `std::env` | not read | — |
| stdin / argv / files / sockets | not read | — |

Consequence: this crate cannot be misconfigured through the
environment. A wrong lease or nick is a caller bug, not a config
refusal — the crate has no config refusal branch at all.
