# `crates/relay` — worked record examples (B186)

Every shape the crate writes, taken from the formatter or `format!` that
produces it. `ts` is a placeholder for the whole-second epoch stamp.

## 1. Message line

Produced by `message_line` (`crates/relay/src/notify.rs:17-19`), appended by
`POST /rooms/<room>/messages` (`crates/relay/src/http.rs:492-494`).

```text
pax: first line [ts:1793350000]
```

| Field | Where it comes from | Rule |
|---|---|---|
| nick | body `nick` | 1–40 UTF-16 units, single line |
| text | body `text` | 1–2000 UTF-16 units, single line |
| ts | `now_secs()` at append time | whole epoch seconds |

## 2. NOTIFY line

Produced by `notify_line` (`crates/relay/src/notify.rs:23-30`), appended by
`POST /rooms/<room>/notify` (`crates/relay/src/http.rs:523-530`).

```text
relay: NOTIFY:ntf-27c8a8f20499356d info [trio-result] trio job trio-abc product ignis completed: category steam or fog [ts:1793350000]
```

| Field | Source | Rule |
|---|---|---|
| `relay` | literal | fixed nick for machine notices |
| id | `notify_id(room, topic, severity, text)` | `ntf-` + 16 hex |
| severity | body `severity` | exact set of three |
| topic | body `topic` | 1–64, single line |
| text | body `text` | 1–2000, single line |
| ts | `now_secs()` | whole epoch seconds |

## 3. NOTIFY id (deterministic)

`notify_id` (`crates/relay/src/notify.rs:9-13`):

```text
ntf-27c8a8f20499356d
```

Basis string, field by field:

```text
main\ntrio-result\ninfo\ntrio job trio-abc product ignis completed: category steam or fog
room  topic        sev   text
```

Same four fields in the same order always yield the same id; changing any one
changes the digest.

## 4. JSONL store record

`record_line` (`crates/relay/src/json.rs:29-35`), one per line, appended by
`RoomStore::append` (`crates/relay/src/store.rs:60-78`).

```json
{"room":"main","line":"pax: first line [ts:1793350000]"}
```

| Key | Type | Rule |
|---|---|---|
| `room` | string | the room the line was appended to |
| `line` | string | the already-stamped wire line, verbatim |

On reload the inverse is `parse_record` (`crates/relay/src/json.rs:215-260`):
string `room` + string `line` required, extra keys ignored, unparseable
records skipped.

## 5. `POST /messages` 201 body

`crates/relay/src/http.rs:493`.

```json
{"index":0}
```

`index` is the new line's 0-based position in that room.

## 6. `POST /notify` 201 body

`crates/relay/src/http.rs:526-530`.

```json
{"index":1,"id":"ntf-27c8a8f20499356d"}
```

## 7. `GET /messages` 200 body

`crates/relay/src/http.rs:539-552`.

```json
{"room":"main","total":2,"messages":["pax: first line [ts:1]","del: second line [ts:2]"]}
```

| Field | Rule |
|---|---|
| `room` | the requested room, escaped |
| `total` | all lines in the room, not just the slice |
| `messages` | lines after `since`; empty array when caught up |

## 8. `GET /health` 200 body

`Relay::health_body` (`crates/relay/src/http.rs:419-427`).

```json
{"ok":true,"rooms":2,"store":"memory"}
```

`store` is `"file"` exactly when a store path was supplied
(`crates/relay/src/store.rs:104-110`).

## 9. Error body

`error_body` (`crates/relay/src/http.rs:558-560`).

```json
{"error":"not found"}
```

The message is JSON-escaped with the same `escape` the store uses.

## 10. Boot line (stdout)

`crates/relay/src/main.rs:26`.

```text
Meta Nuntius relay listening on port 8787 (store: memory)
```
