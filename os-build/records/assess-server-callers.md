# crates/assess-server — callers and their expectations (B139)

The crate is a **binary target with no library target** (`Cargo.toml:6-8`), so
there is no Rust caller that can `use` it. The callers below are therefore of
four kinds: the workspace build, the batch records that expect a test parity
run, the crates whose functions it calls (the dependency direction, which is
where the real coupling is), and the Node callers that still use the original
`server/*.mjs` rather than this port.

| Caller | Line | What it expects | Verdict |
|---|---|---|---|
| `Cargo.toml` workspace members | `Cargo.toml:9` | the crate builds as part of the workspace | OK — `cargo test -p assess-server --no-run` compiles |
| `batches/B05.md` | 38-39 | `cargo build -p assess-server` and `cargo test -p assess-server` | PARTIAL — 40 unit tests now live in `main.rs` (11 at the start of this lane; the error, edge and gap suites were added here); the package still has no library target, so no `tests/*.rs` |
| `BATCHES.md` batch map | 39, 91, 106 | B05 is the assess-server port; wave 1 lists it as built | OK — the file exists and compiles |
| `docs/RUST_REBUILD_PLAN.md` | 198, 210 | assess types live in `assess-server`; B05 owns the crate | OK |
| `SUPER_PROMPT.md` | 158-166 | four source files ported, compile fix, parity run, crate docs | PARTIAL — see the parity gap list (`assess-server-gaps.md`) |
| `batches/B07-report-wave1.md` | 10, 38-42 | `/api/assess` v2 validation present; assess-server has 2 tests at that wave | OK — validation is present; tests have since grown to 11 |
| `OPENCODE_FINISH_REPORT.md` | 22 | B05 serving stack done, 11/11 tests, live 200/502/503 | OK — the 11 tests are the `main.rs` module |
| `OPENCODE_FINISH_REPORT.md` | 46, 70 | dedup: `assess_with_model` → `guardrail::check` pre-send, `queue-core` id | OK — `main.rs:190-192`, `436-438` |
| `crates/queue-core/README.md` | 34 | assess-server consumes `deterministic_job_id` | OK — `main.rs:190-192`, 204 |
| `crates/queue-store/src/lib.rs` | 86 | `product_profile(product) -> Option<&ProductProfile>` | OK — used at `main.rs:421-423`, refusal built at 424-426 |
| `crates/guardrail/src/lib.rs` | 54, 67, 81, 111, 130 | `load_state`, `check`, `record`, `unwrap_model_text`, `build_prompt` | OK — all five called (`main.rs:436-439`, 468-472, 491) |
| `crates/agent-runtime/src/lib.rs` (validator) | — | `validate_assessment(output, product) -> (bool, Vec<String>)` | OK — called at `main.rs:569` |
| `eval/ignis/adapter.mjs` | 46, 194 | imports `assessWithModel` from `server/model.mjs` | **MISMATCH if read as this crate** — it calls the Node original, not the Rust port; the eval harness has no Rust binding |
| `tests/server*.test.mjs` | whole files | exercise `server/*.mjs` over HTTP and injected transports | **NOT this crate** — the Node server remains the production path; these tests do not cover the Rust binary |

## Flagged expectations

1. **"The Rust port is the assess server" is not true in the repo today.**
   `npm start` runs `server/server.mjs` (`package.json:start`); nothing starts
   the Rust binary. Every live caller — the web app, the native app, the eval
   harness — uses the Node process. The Rust crate is a port that compiles and
   tests, not a deployed replacement.
2. **`BATCHES.md` calls B05 built, but the port is missing four routes and the
   four prompt/queue behaviours listed in `assess-server-gaps.md`.** A reader
   who takes "built" as "parity" will be wrong; the gap record is the
   correction.
3. **The guardrail caller contract is weaker than the JS one.** JS
   `recordBudgetCall` throws and the model call fails if the ledger cannot be
   written (`server/model.mjs:210-224`); Rust `guardrail::record` ignores the
   write (`crates/guardrail/src/lib.rs:64-69`). `assess_with_model` therefore
   cannot honour "uncounted spend fails the request" (`main.rs:468-472`).
4. **`agent-runtime::validate_assessment` is the only contract gate.** If that
   function is widened, `assess-server` silently widens with it; there is no
   local copy (deliberate, per the dedup note at `OPENCODE_FINISH_REPORT.md:46`).
   This is a shared-ownership risk, not a bug.
5. **No Rust caller means the `pub` surface is untested as a library.** See
   `assess-server-surface.md`; the only consumers are the crate's own `main`
   and tests.
