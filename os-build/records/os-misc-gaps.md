# Gap list — Python behaviours `crates/os-misc` does not carry

B209 deliverable. These are tasks, not ports: the Rust module that exists
is named, and the Python source lines that hold the missing behaviour are
cited so the next pass can start without re-reading the tree.

## B24 — bus messaging core

| # | Behaviour not carried | Python source | Rust today |
|---|---|---|---|
| G1 | Posting a message (`bus_push`), nick reservation, `--blob` source reading, scheduled and ephemeral sends | `os/send.py:157-185` (nick), `187-266` (blob/schedule/ephemeral), `281-321` (post), `322+` (CLI) | `b24/transport.rs:14-31` has no write method; `b24/send.rs` ports parsing only |
| G2 | The poll loop and its error logger | `os/poll.py:34-79`, `81+` (CLI) | `b24/poll.rs:32-91` is one iteration |
| G3 | The watch loop, interval sleep, announce-only mode, seen-file helpers used by the loop | `os/watch.py:35-49` (seen), `51-108` (loop), `109+` (CLI) | `b24/watch.rs:32-89` is one iteration; `validate_interval` only |
| G4 | Store-dir resolution from `MUSE_RELAY_STORE_DIR` / `open_store` | `os/store.py:53-78` | `b24/store.rs:46-51` takes the directory as an argument |
| G5 | Presence CLI (Redis read of heartbeats) | `os/presence.py:22-40` | `b24/presence.rs:10-35` renders given data only |
| G6 | Nick-watch flag-file writing and exit codes | `os/watch_nick.py:21+` | `b24/watch_nick.rs` returns the decision and name only |

## B25 — messaging extras

| # | Behaviour not carried | Python source | Rust today |
|---|---|---|---|
| G7 | Announce get/set in Redis and its CLI | `os/announce.py:40-47`, `64-92` (mods/gate), `93+` | `b25/announce.rs:7-46` keeps key, filter and gate |
| G8 | Executing clipboard tools and reading/writing real clipboards | `os/clipboard.py:43-84` | `b25/clipboard.rs:7-45` keeps the ordered tables and the error text |
| G9 | Applying an edit through the store, recording incoming edits, rendering edited lines | `os/edits.py:52-133` | `b25/edits.rs:9-51` parses, validates and classifies only |
| G10 | Forward write path and CLI | `os/forward.py:85-110`, `111+` | `b25/forward.rs:4-57` is pure parsing/rendering |
| G11 | Clip chunk reassembly and CLI | `os/paste.py:30-47`, `48+` | `b25/paste.rs:8-98` verifies and hashes only |
| G12 | Save/unsave/list against Redis, blob encoding | `os/saved.py:40-118` | `b25/saved.rs:7-46` keeps key, label, shape, render, filter |

## B26 — bridges, digest, admin

| # | Behaviour not carried | Python source | Rust today |
|---|---|---|---|
| G13 | Secret file, HMAC sign/verify, audit log, every admin subcommand | `os/admin.py:66-147` (secret/admins/signing), `148-365` (commands), `366+` (CLI) | `b26/admin.rs:6-38` validates display/rekey and renders the canonical envelope |
| G14 | Room listing, paged room digest, hourly formatting from real data | `os/digest.py:34-105`, `110+` | `b26/digest.rs:5-36` computes stats from supplied lines |
| G15 | Streaming the store, local-time formatting, export CLI | `os/export.py:33-53` (stream), `54-60` (time), `83+` | `b26/export.rs:14-50` takes entries; time is a `ts:<n>` placeholder |
| G16 | Reading real CPU/memory/disk/uplink stats | `os/health.py:22-49`, `63+` | `b26/health.rs:7-26` formats supplied values |
| G17 | Due/recurring capsule sweep, race-safe ZREM claim, failure requeue | `os/timecapsule.py:31-75`, `76-135`, `136+` | `b26/timecapsule.rs:8-26` keeps constants and pure helpers |
| G18 | Webhook delivery with backoff, offset files, bridge loop, CLI | `os/webhook.py:51-70` (offsets), `71-104` (deliver), `105-141` (bridge), `142+` | `b26/webhook.rs:7-49` resolves the URL, validates the interval, shapes the payload |

## B27 — world packs

| # | Behaviour not carried | Python source | Rust today |
|---|---|---|---|
| G19 | `validate_pack_at` (read a file, resolve its directory), default path discovery, CLI | `os/worlds/validate_pack.py:286-306`, `307+` | `b27/validate.rs:48-322` validates a `serde_json::Value` and compares a name |
| G20 | PAR-clock state load/save, argparse CLI, exit codes | `os/worlds/fdny/runtime/par_clock.py:301-321` (state), `322-362` (CLI), `363+` | `b27/par_clock.rs:63-251` is the pure core; no file or process I/O |

## B28–B30 — carried, not ported

No code gap to port: these batches are inventories of documents, crew
READMEs, audio assets and lane plans (`b28/mod.rs:9-26`,
`b29/mod.rs:8-30`, `b30/mod.rs:7-20`). The only executable surface is
`is_logic_free()`, which is a constant `true` (F6 in the behaviour
record). If a carried file ever gains logic, it must bounce to Pax for
re-batching; nothing in this crate can detect that today.
