# `crates/relay` — config surface (B188)

The binary takes no flags (`crates/relay/src/main.rs:11` starts from env only).
Everything it reads is in this table.

## Environment variables

| Var | Read at | Default | Wrong-value behaviour |
|---|---|---|---|
| `RELAY_PORT` | `main.rs:12-16` | `8787` | empty, non-numeric, negative, or `> 65535` → silently 8787. `0` is accepted by `parse::<u16>` and binds an ephemeral port. |
| `RELAY_STORE_FILE` | `main.rs:17-21`, `http.rs:389-401` | unset → memory | empty string is treated as unset (`filter(!is_empty)`). A path that exists but cannot be read as UTF-8 → panic at boot. A path that does not exist is created on first append. |
| `RELAY_VIEWER_FILE` | `http.rs:404-417` | unset → `relay/viewer.html` in the cwd | empty is ignored. A set-but-missing path makes `GET /` a 500 text/plain; it does not refuse boot. |

## Files

| Path | When | Rule |
|---|---|---|
| store file (`RELAY_STORE_FILE`) | boot + every append | JSONL, one `{"room","line"}` per line (`store.rs:35-58`, `store.rs:60-78`). Blank lines skipped; unparseable records skipped with a stderr note. |
| viewer (`RELAY_VIEWER_FILE` or `relay/viewer.html`) | every `GET /` | read fresh per request (`http.rs:437-455`); missing → 500 text. |

## Constants (not configurable)

| Constant | Value | Source |
|---|---:|---|
| room max | 32 | `validation.rs:24` regex in `validation.rs:10-20` |
| nick max | 40 | `validation.rs:25` |
| text max | 2000 | `validation.rs:26` |
| topic max | 64 | `validation.rs:27` |
| body max | 16384 bytes | `validation.rs:24` |
| default port | 8787 | `main.rs:16` |
| bind address | `0.0.0.0` | `main.rs:24` |

## Refusals that are not "config refusals"

- Port already in use → panic
  `Meta Nuntius: failed to bind port <p>: <err>` (`main.rs:24-26`).
- Store file unreadable → panic
  `Meta Nuntius: failed to read store file <path>: <err>`
  (`http.rs:395-401`).
- `serve` returning `Err` → panic `Meta Nuntius: serve failed`
  (`main.rs:28`).

## The upstream config, for comparison

`relay/README.md:35-38` documents exactly two vars, `RELAY_PORT` and
`RELAY_STORE_FILE`. `RELAY_VIEWER_FILE` is a Rust-side addition
(`http.rs:404-411`); upstream resolves the viewer beside `relay.mjs`
(`relay/relay.mjs:49-50`). Upstream's invalid port throws at `listen`
(`relay/relay.mjs:271-272`); this port falls back to 8787.
