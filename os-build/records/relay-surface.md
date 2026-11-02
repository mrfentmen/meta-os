# `crates/relay` — public surface inventory (B190)

One line per exported name. "Used" means reachable from `main.rs` or from a
route; "tests" means only the crate's own tests exercise it; "unused" means no
caller in this repo.

## `validation` (`crates/relay/src/validation.rs`)

| Name | Kind | Line | Used by |
|---|---|---:|---|
| `valid_room` | fn | 10 | `http.rs:467` — route guard |
| `valid_severity` | fn | 20 | `http.rs:508` — notify guard |
| `MAX_BODY_BYTES` | const | 24 | `http.rs:473,498,619`; tests |
| `MAX_NICK_CHARS` | const | 25 | `http.rs:482` |
| `MAX_TEXT_CHARS` | const | 26 | `http.rs:487,518` |
| `MAX_TOPIC_CHARS` | const | 27 | `http.rs:513` |
| `utf16_len` | fn | 30 | `is_single_line` only; tests |
| `is_single_line` | fn | 37 | `http.rs:476-488,503-522` |

## `notify` (`crates/relay/src/notify.rs`)

| Name | Kind | Line | Used by |
|---|---|---:|---|
| `notify_id` | fn | 9 | `http.rs:524`; unit tests |
| `message_line` | fn | 17 | `http.rs:485` |
| `notify_line` | fn | 23 | `http.rs:528` |

## `sha256` (`crates/relay/src/sha256.rs`)

| Name | Kind | Line | Used by |
|---|---|---:|---|
| `sha256` | fn | 21 | `notify::notify_id`; unit tests |
| `hex_digest` | fn | 90 | `notify::notify_id`; unit tests |

## `json` (`crates/relay/src/json.rs`)

| Name | Kind | Line | Used by |
|---|---|---:|---|
| `escape` | fn | 10 | `http.rs:534,546,552,558`; `record_line` |
| `record_line` | fn | 29 | `store.rs:65` |
| `parse_record` | fn | 215 | `store.rs:47` |

## `store` (`crates/relay/src/store.rs`)

| Name | Kind | Line | Used by |
|---|---|---:|---|
| `RoomStore` | struct | 17 | `http.rs:375` |
| `RoomStore::memory` | fn | 24 | `http.rs:391` |
| `RoomStore::with_file` | fn | 35 | `http.rs:394` |
| `RoomStore::append` | fn | 60 | `http.rs:487,530` |
| `RoomStore::messages` | fn | 80 | `http.rs:544`; `messages_since` |
| `RoomStore::messages_since` | fn | 87 | `http.rs:545` |
| `RoomStore::room_count` | fn | 99 | `http.rs:421` (health) |
| `RoomStore::store_kind` | fn | 104 | `http.rs:423` (health) |

## `http` (`crates/relay/src/http.rs`)

| Name | Kind | Line | Used by |
|---|---|---:|---|
| `percent_decode` | fn | 43 | `http.rs:458`; tests |
| `parse_since` | fn | 97 | `http.rs:538`; tests |
| `Relay` | struct | 374 | `main.rs:23`; `serve`; tests |
| `Relay::new` | fn | 382 | `main.rs:23` |
| `Relay::with_viewer` | fn | 389 | `Relay::new`; tests |
| `Relay::health_body` | fn | 419 | `handle` (`http.rs:458`); tests |
| `Relay::handle` | fn | 429 | `handle_connection` (`http.rs:627`); tests |
| `serve` | fn | 574 | `main.rs:28` |

## Exported but unused outside the crate

- Every `validation`, `notify`, `sha256`, and `json` name is `pub` but no other
  crate imports the module; all are used internally or by tests.
- `Relay::new` and `serve` are the only entry points a supervising process
  would need; there is no stop handle, so a supervisor has nothing to call on
  shutdown (see `relay-gaps.md` G12).
- No type in the crate is re-exported from `lib.rs`; callers must name the
  module (`crates/relay/src/lib.rs:91-97`).
