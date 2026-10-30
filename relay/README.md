# Meta Nuntius — the Trio / OS layer relay

**Meta Nuntius** (Latin: "messenger") is the message relay for the
Meta Trio / Meta OS layer, built fresh inside this repository during
the hackathon. It gives the OS-operates-the-Trio layer its own
standalone bus: the queue service, the resident agent, and the
product consoles exchange plain-text lines and structured NOTIFY
lines through it, with no external service involved.

It is a small, clean-room reimplementation of the line protocol the
crew already uses — plain-text lines, named rooms, send-time stamps,
NOTIFY lines — written from scratch in Node with **zero external
dependencies** (stdlib `node:http` / `node:fs` / `node:crypto`
only), so it runs anywhere Node runs, with no install and no build
step.

**Honest status:** this relay serves the product/OS layer in this
repo. The crew's operational bus (muse-relay) is a separate,
pre-existing external service; Meta Nuntius does not replace it and
shares no code with it.

## Run

```sh
node relay/relay.mjs
# Meta Nuntius relay listening on port 8787 (store: memory)
```

Open <http://127.0.0.1:8787/> for the viewer: room switcher (`main`
and `1` quick buttons), 2-second watermark polling, and a
Notifications strip that surfaces NOTIFY lines newest-first.

Environment:

| Var | Default | Meaning |
| --- | --- | --- |
| `RELAY_PORT` | `8787` | Port to listen on. |
| `RELAY_STORE_FILE` | unset | If set, lines are appended to this JSONL file (`{"room": ..., "line": ...}` per record) and reloaded on boot. Unset = in-memory only. |

## Wire format

Message line (one per room entry):

```
<nick>: <text> [ts:<epoch-seconds>]
```

NOTIFY line (appended by the `/notify` endpoint, as nick `relay`):

```
relay: NOTIFY:<id> <severity> [<topic>] <text> [ts:<epoch-seconds>]
```

- `id` = `ntf-` + the first 16 hex chars of the SHA-256 of
  `room + "\n" + topic + "\n" + severity + "\n" + text` — the same
  payload in the same room always yields the same id.
- `severity` is one of `info`, `warning`, `critical`.
- Every line is stamped at send time with the trailing
  ` [ts:<epoch-seconds>]` marker.

## Endpoints

| Method & path | Body / params | Returns |
| --- | --- | --- |
| `POST /rooms/<room>/messages` | `{nick, text}` | `201 {index}` — the line's 0-based position in the room |
| `POST /rooms/<room>/notify` | `{severity, topic, text}` | `201 {index, id}` |
| `GET /rooms/<room>/messages?since=<n>` | `since` = last index seen | `{room, total, messages}` — the lines after index `n`; `since=-1` (or omitted) returns the whole room |
| `GET /health` | — | `{ok: true, rooms: <count>, store: "memory" \| "file"}` |
| `GET /` | — | the viewer (`viewer.html`) |

## Validation caps (refusals are `400` JSON errors)

- room name: `[a-z0-9-]{1,32}`
- nick: single line, 1–40 chars, no control characters
- text: single line, 1–2000 chars
- topic: single line, 1–64 chars
- request body: at most 16384 bytes of JSON

## Who posts here

- Consoles and tools post operator lines via `/messages`.
- The resident queue agent (`server/queue/trio_agent.py`) posts a
  NOTIFY line for every job it finishes when `TRIO_RELAY_URL` points
  at this relay: topic `trio-result`, severity `info` for a completed
  assessment (naming the job id, product, and category), `warning`
  for a failure (naming the job id, product, and error). The hook is
  fire-and-forget — a relay outage never fails a job.

## Tests

```sh
node --test relay/relay.test.mjs
```

Offline; the tests bind an ephemeral localhost port and also cover
the JSONL file store. Note: the repo's `npm test` enumerates its
test files explicitly in `package.json`, and `relay/relay.test.mjs`
is not in that list yet — wiring it in is a one-line `package.json`
addition, deliberately left to the integrator so this change stays
additive.
