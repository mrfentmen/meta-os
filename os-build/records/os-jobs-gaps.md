# `os-jobs` — behaviours the Rust port does not carry yet

B029. The Python original is `os/jobs.py` (1,045 lines) plus the five
test files named in `BATCHES.md` §B16. This is a task list, not a port:
each entry names the Python source line and what the Rust crate does
instead today. Nothing here is silently missing; the crate header
(`crates/os-jobs/src/lib.rs:44-70`) states the same limits in prose.

## G1 — The Upstash REST transport

- Python: `_q` 78-80, `_seq_key`/`_job_key`/`_spec_key`/`_claim_key`/
  `_index_key` 82-100, `_hgetall` 102-110, `_hset` 112-120, `_hdel`
  122-125, and every `api_get`/`api_post` call inside the commands.
- Rust: `JobStore` trait (151-176) with `FakeStore` only (177-317).
  `url_quote`/`url_unquote` (319-357) are ported, but nothing calls a
  server. A real transport needs an HTTPS client, which is a crate
  decision, not a port.
- Task: choose an HTTPS crate or a localhost sidecar, then implement
  `JobStore` over Upstash semantics (string/hash/zset, TTL). Keep the
  trait as the seam.

## G2 — The namespace environment variable

- Python: `MUSE_RELAY_JOBNS` overrides `muse-bus:job` (`os/jobs.py:82-84`).
- Rust: `DEFAULT_NS` is a public const (`lib.rs:78`) and is never read;
  the namespace is the `JobQueue::new` argument (952).
- Task: either read the env var in a CLI wrapper or delete the const in
  a breaking-change batch. Today the constant advertises a behaviour
  the crate does not have.

## G3 — The command-line entry point and its exit codes

- Python: `main(argv=None)` and the argparse table (`os/jobs.py:928-1045`);
  every subcommand maps to one `cmd_*`.
- Rust: one public method per command on `JobQueue`; no argv parser, no
  `main`. The `CmdOutcome` triple is the seam a CLI would print.
- Task: write `src/bin/jobs.rs` (or a wrapper crate) that maps flags to
  `PostArgs` and prints `out`/`err` with `code`. Do not move command
  logic into the binary.

## G4 — `--spec -` reads stdin

- Python: `spec = sys.stdin.read() if args.spec == "-"` (`os/jobs.py:398-400`).
- Rust: `PostArgs::spec` is documented as already resolved
  (`lib.rs:866-870`); the caller must read stdin.
- Task: resolve `-` in the CLI wrapper (G3), not in `JobQueue::post`.

## G5 — `--status` is validated by argparse

- Python: `choices=["all","open","claimed","done","blocked","cancelled"]`
  (`os/jobs.py:958-961`) rejects an unknown status before any read.
- Rust: `list(status_filter, json)` accepts any string and treats it as
  a filter (`lib.rs:1498-1616`); an unknown value returns `NO_JOBS`,
  not an error.
- Task: enforce the allowed set in the CLI wrapper, or add a typed
  `Status` enum to the crate in a breaking-change batch.

## G6 — Bus announcements are sent

- Python: `_announce` writes to the bus and warns on failure
  (`os/jobs.py:358-367`).
- Rust: announcements are appended to `JobQueue::announcements`
  (`lib.rs:974-981`, `1156-1168`); nothing is sent.
- Task: implement the bus transport at the announcement sink, preserving
  the best-effort rule (a failed announce never fails the command).

## G7 — The nick-claim check cache

- Python: `relay_common` caches the claim check; the crate header names
  this as not ported (`lib.rs:50-54`).
- Rust: `nick_claim` reads the store every call (`lib.rs:1070-1101`).
- Task: add the cache only if a measured hot path needs it; outcomes are
  already identical.

## G8 — A cryptographic nonce

- Python: `secrets.token_hex(8)` (`os/jobs.py:459`).
- Rust: `fresh_nonce` mixes wall time with a process counter
  (`lib.rs:906-919`), documented as non-cryptographic.
- Task: accept a caller-supplied nonce (constructor/`PostArgs`) or use a
  vetted RNG crate. The signature's security is the HMAC key; the nonce
  only needs uniqueness today.

## G9 — Arbitrary-precision artifact versions

- Python: `int()` accepts any size (`os/jobs.py:150-173`).
- Rust: `u64` parse; overflow is malformed (`lib.rs:672-709`).
- Task: only if a real version exceeds `u64` (it does not today);
  otherwise document the limit where the OS-083 format is specified.

## G10 — Python's `int()` strictness

- Python: `int(h.get("attempts", 0) or 0)` and `int(max_attempts)` raise
  on non-numeric stored values (`os/jobs.py:855-861`); `cmd_requeue`
  does not catch that, so a corrupted hash can traceback.
- Rust: `attempts` defaults to 0 and a non-numeric `max_attempts` is
  treated as unlimited (`lib.rs:2135-2172`), with a comment saying so.
- Task: decide which behaviour the shared contract wants. The Rust
  behaviour is the safer one; if Python is changed, change the test
  fixtures in `os/tests/test_jobs.py` at the same time.

## G11 — Message/claim surfaces from `test_claims.py`

- Python tests: `os/tests/test_claims.py` covers send/poll/watch/
  presence/DM rooms through `relay_common`; only `nick_holder` and the
  claim itself are used by `jobs.py`.
- Rust: only the nick-claim surface is ported (`lib.rs:1059-1111`); the
  rest belongs to the bus/relay batches.
- Task: port them in the batch that owns `relay_common`, not here.

## G12 — The brief composer

- Python: `os/intel/brief.py` `compose_template_brief` and the other
  environment quarters (repo/bus/budget) at 1068-1400 and 2589-2700.
- Rust: only the jobs input and the four `environment_lines` are ported
  (`lib.rs:2281-2597`), as the batch header says.
- Task: the intel batch owns the composer; this crate must not grow a
  second copy.
