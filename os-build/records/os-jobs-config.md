# `os-jobs` — configuration surface

B032. Everything this crate can be configured with, where it comes
from, its default, and the refusal when it is wrong. There are **no
environment variables read by the crate**: a search for `std::env`
finds one use, `std::env::temp_dir()` in the tests (2651). The Python
original reads `MUSE_RELAY_JOBNS` (`os/jobs.py:82-84`); the Rust port
does not (G2).

## Constants

| Name | Value | Line | Read by |
|---|---:|---|---|
| `LEASE_DEFAULT` | 1800 | 76 | `PostArgs::default` (894), heartbeat fallback (1887) |
| `DEFAULT_NS` | `"muse-bus:job"` | 78 | **nothing** — the namespace is a constructor argument (finding in `os-jobs.md`) |
| `SIG_VERSION` | `"2"` | 80 | `post` when signing (1488) |
| `NICKCLAIM_TTL` | 120 | 84 | `nick_claim` (1078, 1093) |
| `PRESENCE_TTL` | 120 | 87 | **nothing** — documents the Python equality invariant |

## Constructor — `JobQueue::new(store, clock, ns, nick, host)` (952)

| Parameter | Type | Default | Wrong value / refusal |
|---|---|---|---|
| `store` | any `JobStore` | none | a store error becomes `RELAY_ERROR: <command> failed (…)`, exit 2 (never a panic) |
| `clock` | `Rc<dyn Clock>` | none | a clock that goes backwards only affects TTL tests; production uses `SystemClock` (108) |
| `ns` | `&str` | none | an empty namespace produces keys like `:1` and `seq` at the top level; no validation is performed. Callers must pass a real prefix |
| `nick` | `&str` | none | empty nick is written as `created_by=""` and skipped by the empty-field rule; no validation |
| `host` | `&str` | none | empty host likewise; no validation |

`set_nick(nick, host)` (964-967) replaces the identity mid-run; it is
how the tests simulate a second worker.

## `PostArgs` (866-904) — the `post` flags

| Field | Default | Refusal when wrong |
|---|---|---|
| `title` | `""` | none — an empty title is allowed and is not stored (empty fields are skipped) |
| `spec` | `""` | empty/whitespace → `ERROR: --spec is empty`, exit 2, before any write (1349-1353) |
| `accept` | `""` | none |
| `branch` | `""` | none |
| `base` | `""` | none |
| `room` | `""` | `""` is the legacy `muse-bus` room; a non-empty room that cleans to nothing → `ERROR: invalid room name: '…'`, exit 2 (1354-1362, 375-388) |
| `lease` | `1800` | `< 60` → `ERROR: --lease needs at least 60s`, exit 2 (1363-1366). Negative values also fail this check |
| `files` | `""` | none; stored comma-joined exactly as given |
| `deps` | `""` | none; a missing dep only warns (1461-1476) |
| `req` | `""` | none; normalized by `normalize_req` (lowercase, trim, dedupe, order kept, 921-932) |
| `max_attempts` | `None` | none; `Some(0)` means the first requeue marks `failed-final` |
| `artifacts` | `""` | any malformed ref → `ERROR: malformed artifact reference: …`, exit 2, before any write (1367-1372, 722-733) |
| `secret_file` | `None` | unreadable/empty keyring → `ERROR: …`, exit 2, **after** the job hash/spec/index are written (1462-1467) |
| `kid` | `""` | `""` selects the first key; an unknown kid → `ERROR: unknown kid '…' (keyring has: …)`, exit 2 (1470-1484) |
| `expires` | `None` | `Some(n)` with `n <= 0` → `ERROR: --expires needs a positive number of seconds`, exit 2 (1479-1487) |

## Files read

| File | Format | Default | Refusal |
|---|---|---|---|
| `secret_file` (post/claim/verify) | UTF-8; either one legacy secret line, or `kid:secret` lines | none (only read when a path is given) | empty file → `secret file '…' is empty`; a line with more than one colon, empty kid/secret, or whitespace in a kid → `bad keyring line…`; multiple secrets without kid lines → `'…': multiple secrets need kid:secret lines` (759-812) |

The keyring is read fresh on every command; no caching, no file watch.
A key rotation is "add a `kid:secret` line"; the first line signs by
default, all lines verify (750-757).

## Command parameters that are not flags

| Command | Parameter | Default | Refusal |
|---|---|---|---|
| `list` | `status_filter` | caller supplies; Python's CLI default is `all` | an unknown status is not rejected; it simply matches nothing and prints `NO_JOBS` (G5) |
| `list` | `json` | `false` | none |
| `claim` | `room_override` | `""` (falls back to the job's room) | none; a bad room only warns during announce |
| `claim` | `lease` | caller supplies; `PostArgs`-style default is not applied here | `< 60` → `ERROR: --lease needs at least 60s` (1801-1804) |
| `claim` | `secret_file` | `None` | unreadable → `ERROR: …`; BAD/EXPIRED → exit 1 (1745-1799) |
| `heartbeat` | `lease_opt` | `0` means "keep the stored lease" (1864-1898) | a non-zero value is used verbatim; no `>= 60` check |
| `progress` | `room_override` | `""` | none |
| `done`/`blocked` | `room_override` | `""` | none |
| `cancel` | `reason` | caller supplies (Python default `"cancelled"`) | none; empty reason is not stored (empty-field rule) |
| `requeue`/`sweep` | `room_override` | `""` | none |

## What is deliberately not configurable

- No transport URL, no token, no TLS setting — there is no transport
  (G1). `url_quote` exists for a future one.
- No log level, no output format switch beyond `list --json`, no retry
  count, no poll interval. The crate is synchronous.
- No time zone: timestamps are Unix seconds; only the brief lines
  render US Eastern (`eastern_offset_secs`, 2436-2450).
