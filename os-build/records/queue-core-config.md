# queue-core — config surface (B116)

## Environment variables, flags, files

None. The crate reads no environment variable, parses no flag, and
opens no file. `grep std::env crates/queue-core/src` has no match; the
module doc's "zero-dependency" claim (`lib.rs:8-12`) covers this.

| Surface | Owner | Default | Refusal when wrong |
|---|---|---|---|
| `TRIO_JOB_NS` | **not here** — `crates/queue-store/src/lib.rs:103` reads it | `trio` | none; any string becomes the prefix |
| `TRIO_UPSTASH_HOST`, `RELAY_URL`, `TRIO_STORE` | **not here** — `crates/queue-store` / Python `trio_store.py:354-371` | — | typed `TrioStoreConfigError` in the store crate |
| Product ids | caller parameter `product_ids` (`lib.rs:195`) | none | `unknown product '<id>'` when the list does not contain it |
| Namespace | caller parameter `ns` (`lib.rs:389`) | none | no validation; `""` yields `:jid` (`queue-core.md` edge test) |
| Clock | caller parameter `now: i64` on `submit`/`claim`/`finish` | none | no validation; a negative or zero `now` is stored as given |
| Lease | caller parameter `lease: u64` | none | no validation; `0` writes an expiry equal to now |
| Stored envelope / result JSON | caller strings | none | not parsed; any string is stored (`lib.rs:409-410`, `473-475`) |

## The one ambient input

`now_secs()` (`lib.rs:269-276`) reads `SystemTime` for lease expiry
inside `MemoryBackend`. If the clock is before the Unix epoch, it
returns `0` (`unwrap_or(0)`), so every lease is measured from zero.

No config file, no `.env`, no credentials. The crate cannot leak a
secret because it accepts none.
