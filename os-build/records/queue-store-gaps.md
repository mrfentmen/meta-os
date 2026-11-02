# Gaps — Python behaviours the Rust `queue-store` port does not carry

Read against `server/queue/trio_store.py` and
`server/queue/trio_repo.py` on `main`, 2026-11-02. These are **tasks,
not ports**: nothing here was implemented by this pass. Each names the
Python source lines so a later slice can pick it up.

## Transport and configuration

1. **The Upstash HTTP backend is absent.**
   `trio_store.py:152-243` (`class UpstashStore`) implements the whole
   Redis-REST command surface, including URL quoting (`_q`, lines
   143-144) and the three-attempt retry with a one-second sleep (lines
   178-215). The Rust crate has only `InMemoryStore` and `SqliteStore`.
2. **`open_store()` selection and honest fallback are absent.**
   `trio_store.py:354-371` tries Upstash, pings it, falls back to local
   SQLite, and returns `(store, fell_back)`. Nothing in Rust chooses a
   backend, and nothing reports "fell back".
3. **`TRIO_STORE=local` is not read.**
   `trio_store.py:357` forces the local path for proving it works.
   `TRIO_STORE` appears nowhere in the Rust crate.
4. **`RELAY_URL` base-URL override is not read.**
   `trio_store.py:160-176` lets a full base URL win over the derived
   host and refuses an unparseable one. Rust resolves a host only.
5. **Credential-record host resolution is not ported.**
   `trio_store.py:63-97` reads `rest_url` / `url` / `base_url` /
   `host` / `hostname` from the `custom.upstash` credential record via
   `dynamic_credentials`. `resolve_upstash_host_from_env`
   (`lib.rs:164-166`) passes `None`, so the Rust crate can only be
   configured by the env var.
6. **The missing-helper refusal is not ported.**
   `trio_store.py:196-200` raises `TrioStoreConfigError` when the
   dynamic-credential helper is unavailable, naming `TRIO_STORE=local`.
   Rust has no Upstash call path, so it has no such refusal.

## Data-shape differences

7. **Unknown product: exception vs `None`.**
   `trio_repo.py:49-54` raises `KeyError`; `lib.rs:90-92` returns
   `Option`, and `product_ids` returns `HashMap<String, ()>`
   (`lib.rs:86-88`) where Python returns a `set`
   (`trio_repo.py:45-46`).
8. **Product loading is embedded, not live.**
   `trio_repo.py:28-43` spawns node to import `js/products.js` and
   raises `RuntimeError` when that fails. `lib.rs:37-84` embeds the
   three records; drift detection against the JS source is a manual
   check, not a runtime one.
9. **Missing `id` is an exception in Python, an empty key in Rust.**
   `trio_store.py:382` (`envelope["id"]`) vs `lib.rs:386`
   (`unwrap_or("")`).
10. **Missing `job_id` is an exception in Python, an empty key in
    Rust.** `trio_store.py:455` vs `lib.rs:439`.
11. **Namespace capture time differs.**
    `trio_store.py:47` binds `NS` at import; `lib.rs:102-104` reads the
    env on every call, so a mid-process env change silently moves the
    namespace.
12. **Expiry precision differs.** Python stores `time.time() + lease`
    as a float (`trio_store.py:305-306`, `312-313`); Rust stores
    integer seconds (`lib.rs:317-330`). The difference is sub-second
    only, but it is not byte-identical behaviour.

## Error reporting

13. **`release_claim` swallows errors in Python; Rust cannot report
    one at all.** `trio_store.py:446-451` catches transport failures;
    the Rust trait's `delete` returns a count and has no error channel
    (`lib.rs:173-189`).
14. **`SqliteStore` writes swallow SQL errors.** `lib.rs:302` ignores
    the result of `INSERT OR REPLACE` and returns `"OK"`. Python's
    `set_body` calls `commit()` (`trio_store.py:292-298`), which raises
    on failure.

## Crate hygiene finding

15. `Cargo.toml` declares `serde` and `urlencoding`, but
    `src/lib.rs` uses neither (`serde_json` is used; `serde` derives
    are not). Either they are for the unported Upstash path or they are
    dead dependencies. Reported here; not removed, because removing
    them would change the build while the Upstash port is still owed.
