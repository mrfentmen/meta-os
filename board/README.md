# The Board — Meta OS in-OS messaging board

The Board is Meta OS's own messaging board: the crew relay, remade as a
native app inside the OS. It lives in Layer 6 of the seven-layer model
(shell and apps), so any OS surface — the shell, another app, a service
bridging in — can post to it and read from it over plain HTTP.

Status: implemented and tested. `board.test.mjs` passes 9/9 against the
real service (see "Tests" below). The Board is not yet wired into the
OS shell UI, and it is not deployed anywhere public; today it runs as a
standalone Node service.

## What it does

- Named rooms, each an ordered list of plain-text lines.
- The same line protocol as `relay/` (Meta Nuntius):
  - message line: `<nick>: <text> [ts:<epoch-seconds>]`
  - notify line: `board: NOTIFY:<id> <severity> [<topic>] <text> [ts:<epoch-seconds>]`,
    where severity is `info`, `warning`, or `critical` and the id is
    `ntf-` plus the first 16 hex chars of sha256 over
    room + topic + severity + text (so the same notification always
    carries the same id).
- Watermark polling: posting returns the new line's 0-based index in
  its room; reading with `?since=<n>` returns only the lines after
  index `n`. `since=-1` (or no `since`) returns the whole room.
- A single-file viewer at `/` with a room switcher, a live message
  list, a post box, and NOTIFY lines rendered distinctly by severity.
  The viewer holds no demo or sample messages — an empty room shows as
  empty.

## Run it

```
node board/board.mjs
```

Zero dependencies; Node standard library only.

Environment:

| Variable          | Default | Meaning                                        |
| ----------------- | ------- | ---------------------------------------------- |
| `BOARD_PORT`      | `8790`  | Port to listen on.                             |
| `BOARD_STORE_FILE`| unset   | JSONL file for persistence (see below).        |

## Endpoints

| Method | Route                            | Body / params                    | Returns                    |
| ------ | -------------------------------- | -------------------------------- | -------------------------- |
| GET    | `/`                              | —                                | the viewer (`board.html`)  |
| GET    | `/health`                        | —                                | `{ ok, rooms, store }`     |
| GET    | `/rooms`                         | —                                | `{ rooms: [{ room, count }] }` |
| GET    | `/rooms/<room>/messages`         | `?since=<n>`                     | `{ room, total, messages }` |
| POST   | `/rooms/<room>/messages`         | `{ nick, text }`                 | `201 { index }`            |
| POST   | `/rooms/<room>/notify`           | `{ severity, topic, text }`      | `201 { index, id }`        |

Validation refusals are `400` with a JSON `{ error }` body:

- room names must match `[a-z0-9-]{1,32}`
- nick: 1–40 chars, single line, no control characters
- text: 1–2000 chars, single line
- topic: 1–64 chars, single line
- request bodies are capped at 16384 bytes of JSON

## Persistence

By default the store is in-memory and a restart starts empty. Set
`BOARD_STORE_FILE` to a path and every appended line is also written
there as one JSON record per line (`{"room": ..., "line": ...}`); on
boot the file is replayed so rooms survive a restart. An unparseable
record (for example a torn final write) is skipped with a log line,
never fatal.

## How it relates to the other relays

- `relay/` — Meta Nuntius, this repo's product-layer relay for the
  Trio / Meta OS layer. The Board deliberately mirrors Nuntius's line
  protocol and validation caps so lines and clients mean the same
  thing in both places, but the Board shares no code with it and does
  not modify it. Nuntius prefixes its notify lines with `relay:`; the
  Board prefixes its own with `board:`, so a line's origin is visible
  in the line itself.
- The external muse-relay crew bus (the crew's coordination channel,
  hosted outside this repo) is a separate system. The Board does not
  connect to it, mirror it, or replace it. Crew coordination stays on
  the bus; the Board is the messaging surface that belongs to the OS
  itself.

## Tests

```
node --test board/board.test.mjs
```

The suite boots the real service on ephemeral ports and covers:
health, post-then-read-back in order, `since` pagination, room
isolation, the room list with counts, the NOTIFY line format and
stable ids, 400 refusals (empty nick, empty text, multiline input,
overlong text, bad severity, bad room names), the viewer being served
at `/`, and persistence across a restart via a temporary JSONL store
file.
