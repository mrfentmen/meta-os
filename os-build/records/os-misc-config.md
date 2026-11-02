# Configuration surface — `crates/os-misc`

B212 deliverable. Every environment variable, flag and file the crate
reads, with its default and its refusal when wrong.

## Environment variables

**The crate reads none directly.** Two places accept configuration from
the caller instead:

| Surface | How it is supplied | Why |
|---|---|---|
| Store directory | `MessageStore::new(path, room)` / `store_path(dir, room)` (`b24/store.rs:46-51`, `86-94`) | Python resolves `MUSE_RELAY_STORE_DIR` in `store_dir()` (`os/store.py:53-56`); the port takes the directory as an argument (gap G4) |
| Webhook URL source | `resolve_url(spec, env_get)` (`b26/webhook.rs:11-27`) | the caller passes a lookup closure; the crate never calls `std::env` |
| Own display prefixes | `BusTransport::own_prefixes(nick)` (`b24/transport.rs:28-30`) | the implementation decides; the default is the canonical nick |
| Clock / timestamps | `now` / `ts` arguments throughout | no global clock read except `now_unix()` (`b24/send.rs:161-166`) and `now_ts()` (`b24/store.rs:53-58`) |

## Files read or written

| File | Produced by | Shape | Failure behaviour |
|---|---|---|---|
| `messages.jsonl` | `store_path(dir, "")` (`b24/store.rs:46-51`) | one `Entry` JSON per line | read error = empty list (`:160-166`); write error returned as `Err` |
| `messages-<room>.jsonl` | `store_path(dir, room)` | same | same |
| seen-offset file | caller names it; `read_seen` (`b24/poll.rs:24-29`), `fs::write` (`:74-80`) | decimal integer | missing/garbage reads as `0`; write failure is a warning |
| watch seen file | `Target.seen_file` (`b24/watch.rs:11-18`), written at `:77-79` | decimal integer | write failure ignored (`let _ =`) |
| nick flag file | name only: `flag_name` (`b24/watch_nick.rs:27-35`) | `.NAME_reported[_room]` | file creation is not carried (gap G6) |
| pack manifest | caller reads it; `validate_pack(&Value)` (`b27/validate.rs:48`) | JSON object | non-object returns one error string |
| PAR state | not read or written (gap G20) | — | — |

## Constants and their defaults

| Constant | Value | Site |
|---|---|---|
| `MAX_TEXT` | 2000 | `b24/transport.rs:11` |
| `SAVE_CAP` | 200 | `b25/saved.rs:7` |
| `MAX_DISPLAY` | 32 | `b26/admin.rs:6` |
| `PAGE` | 1000 | `b26/digest.rs:5` |
| `TOP_N` | 5 | `b26/digest.rs:6` |
| `TIMECAPSULE_KEY` | `muse-bus:timecapsule` | `b26/timecapsule.rs:8` |
| `REQUEUE_DELAY_SECS` | 60 | `b26/timecapsule.rs:9` |
| `MAX_ATTEMPTS` | 5 | `b26/webhook.rs:7` |
| `BACKOFFS` | `[1, 2, 4, 8]` seconds | `b26/webhook.rs:8` |
| `DEFAULT_INTERVAL_SECONDS` | 600 | `b27/par_clock.rs:11` |
| `DEFAULT_GRACE_SECONDS` | 120 | `b27/par_clock.rs:12` |

## Flags

The crate has no CLI and no flags. The Python CLIs (`--hours`,
`--ttl`, `--at`, `--announce`, `--interval`, webhook URLs) are not
ported; their parsing helpers exist where listed in the gap record.

## Refusals when configuration is wrong

| Wrong input | Refusal | Site |
|---|---|---|
| Empty store nick | `nick is empty` | `b24/store.rs:105-108` |
| Empty message text | `message text is empty` | `b24/store.rs:109-111` |
| Store path unwritable | the OS error string from `save` | `b24/store.rs:186-199` |
| Unparseable duration | `not a duration (try 30s, 10m, 2h, 1d): "<spec>"` | `b24/send.rs:10-30` |
| Bad `--ttl` | `--ttl needs a duration (30s, 10m, 2h, 1d), got "<spec>"` | `b24/send.rs:79-83` |
| Bad `--at` | `can't parse --at "<spec>": use 10m/2h/1d, a unix timestamp, or ISO …` | `b24/send.rs:105-124` |
| Nonpositive watch interval | `interval must be positive` | `b24/watch.rs:24-30` |
| Nonpositive digest hours | `--hours must be positive` | `b26/digest.rs:25-30` |
| Nonpositive capsule interval | `interval must be positive` | `b26/timecapsule.rs:11-17` |
| Nonpositive webhook interval | `--interval must be positive` | `b26/webhook.rs:29-35` |
| Webhook env missing/empty | `env var "<name>" is not set or empty` | `b26/webhook.rs:11-27` |
| Webhook env not a URL | `env var "<name>" does not hold an http(s) URL` | `b26/webhook.rs:20-25` |
| Crew id empty/whitespace | `crew id may not be empty` / `… contain whitespace` | `b27/par_clock.rs:63-72` |
