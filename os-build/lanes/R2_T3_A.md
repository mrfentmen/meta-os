# R2-T3 Section A — Local message bus (tasks 1–24)

Worktree `/tmp/agent-r2-t3`, branch `agent-r2-t3` (base `047c1f16`).
No branch switches, no commits, no merge/push, no QEMU, no paid calls.
Secret values never printed (key/env names only).

## Files created / edited (ONLY these)

- NEW `server/bus.mjs` — the local bus (node stdlib only, no npm deps).
- NEW `server/bus.test.mjs` — selftest + negative tests (exits 0 / non-zero).
- `server/README.md` — appended "Local message bus" section (file existed).
- `.gitignore` — appended one data-dir entry + comment (read first, minimal diff).
- THIS file `os-build/lanes/R2_T3_A.md` — findings.

Untouched as ordered: `board/*`, `bus.html`, any app page,
`os-build/face/*`, `os-build/identity/*`, `provision.sh`, image units.
`git status --short` shows our two `M` entries plus other lanes'
untracked files (left alone):

```
M .gitignore
M server/README.md
?? server/bus.mjs
?? server/bus.test.mjs
?? agents/... (other lane, untouched)
?? server/queue/metaosd_store.mjs (other lane, untouched)
```

## Endpoint list (board shape kept)

Board-compat (same paths `js/site-chat.js` already uses on `:18935`):

- `GET /rooms/<room>/messages?since=<n>&limit=<k>` → `{ room, total, messages:[lines], items:[...] }`
- `POST /rooms/<room>/messages { nick, text, attachmentIds? }` → `201 { index, id, ts, delivery }`
- `POST /rooms/<room>/notify { severity, topic, text }` → `201 { index, id (ntf-…), seq }`

Additive (reads open, writes need the local token):

- `GET /` → `{ ok, service, board_compat, dataDir, rooms }`
- `GET /health` → `{ ok, store:"file", dataDir, rooms, count, counts, lastWrite, uptimeSec, pageSize, maxLimit, ... }`
- `GET /rooms` → `[{ room, count }]` (`general` auto-exists)
- `POST /rooms { room }` → create (200 exists / 201 created)
- `GET /rooms/<room>/history?cursor=<id|seq>&limit=<k>` → paged items + `nextCursor` (PAGE_SIZE=50, MAX 200)
- `GET /rooms/<room>/search?q=&limit=` → accent-insensitive hits
- `GET /rooms/<room>/presence` / `POST .../presence { nick, action: join|leave|heartbeat }` (60 s TTL)
- `POST /rooms/<room>/join { nick }` (presence-join alias)
- `POST /rooms/<room>/attachments { filename, mime, dataBase64 }` → `201 { id, path, ... }`
- `GET /rooms/<room>/attachments/<id>` → raw bytes
- `POST /rooms/<room>/prune { before, keep_last? }` → retention-guarded
- `GET /rooms/<room>/events?cursor=` → SSE (`data:` JSON + `: heartbeat`; `Last-Event-ID` honoured)

Default port 18935 (`BUS_PORT`, else `BOARD_PORT`, else 18935); binds
`127.0.0.1` only (`server/bus.mjs:1140`).

## Task ticks + pasted proof (one command+output per claim)

### (1) Inventory: every Upstash/remote-service requirement touching the bus path

```
$ grep -rn "import relay_common" --include="*.py" os/intel/ | head
os/intel/spark_client.py:97:import relay_common as rc
os/intel/store.py:140:import relay_common as rc
os/intel/ingest.py:34:import relay_common as rc
os/intel/brief.py:91:import relay_common as rc
os/intel/notify.py:49:import relay_common as rc
os/intel/spark_agent.py:65:import relay_common as rc
os/intel/join.py:377:    import relay_common as rc
os/intel/integration.py:86:    from relay_common import bus_key
... (+ e2e1:149, e2e2:136, e2e3:177, load_check:231, spoof_dispatch:75, drills)
```

- `bus.html` — user-supplied Upstash REST URL + token (`localStorage`
  `relay-url`/`relay-token`, `Authorization: Bearer`), shapes
  `/lrange/` (:411), `/rpush/` (:528, :3076), `/smembers/` (:398, :2629),
  `/mget/` (:401, :1363, :1374); hint at :226-228 "enter your Upstash
  `REST URL` and `REST token`". No first-party server involved.
- `os/intel/*` via `relay_common` (module absent from tree — `find`
  returns nothing; `import relay_common` raises `ModuleNotFoundError`):
  `store.py:3-4` (prefix `muse-bus`, override `MUSE_RELAY_KEY_PREFIX`),
  `spark_client.py:97,359,365` (`MUSE_RELAY_URL + token file`),
  `join.py:27,282,321,330,373-375` (`MUSE_RELAY_URL` into
  `secrets.env`, `MUSE_RELAY_TOKEN_FILE`), `redis_down_drill.py:119-120`
  (drill sets `MUSE_RELAY_URL`/`MUSE_RELAY_TOKEN_FILE`),
  `alerts.py:3` (`muse-bus:intel:alert`), `integration.py:28-36,82,86`
  (`muse-bus:room:build-int`, `bus_key()` delegation).
- `os/admin.py:27,53` — `PREFIX = os.environ.get("MUSE_RELAY_KEY_PREFIX", "muse-bus")`.
- `server/queue/trio_store.py` — `TRIO_UPSTASH_HOST` (:108, :118),
  `RELAY_URL` override (:163), `custom.upstash` credential (:56),
  `open_store` fallback (:359-367, labelled `local-sqlite-FALLBACK`).
- `server/queue/trio_agent.py:39-46,86-119` — OPTIONAL `TRIO_RELAY_URL`
  hook `POST {base}/rooms/main/notify` (2 s fire-and-forget, swallowed).
- Firstboot/image docs — `crates/os-boot/assets/os/README.md:147`,
  `README-FIRSTBOOT.md:9`, `os/plan/META_OS.md:132` prompt once for the
  Upstash bus token; `os/plan/MASTER_PLAN.md:22` (Upstash Redis lists,
  default `muse-bus`, rooms `muse-bus:room:<name>`).
- `os-build/layer1/secret_counts.py:48` — the Upstash-shaped reference
  used elsewhere (counts only, never values):
  `upstash-style token pattern` (R13-157 scope 2026-10-29..30).

### (2) Default bus = local file-backed store under ONE documented data dir

```
$ env -u BUS_DATA_DIR -u METAOS_STATE node --input-type=module \
    -e "import { defaultDataDir } from './server/bus.mjs'; console.log(defaultDataDir())"
/Users/test/.local/state/metaos/bus
```

`server/bus.mjs:127-136` — `$BUS_DATA_DIR`, else `$METAOS_STATE/bus`,
else `~/.local/state/metaos/bus`. Outside the git tree by construction
(`~/.local/...` vs repo `/tmp/agent-r2-t3`); selftest asserts it.

### (3) Keep the board HTTP shape (list every endpoint)

Done — endpoint table above. Compat proven by live curl (see demo
below): `POST {nick,text}` → 201, `GET ?since=-1` returns
`"demo: hello board-compat [ts:…]"`, `POST notify` returns `ntf-` id
and the `board: NOTIFY:…` line polls back.

### (4) Rooms create/list/join + default `general`

```
$ curl -s http://127.0.0.1:18999/rooms
{"rooms":[{"room":"general","count":0}]}
```

Selftest: `ok - default room general exists`,
`ok - rooms create/list/join (+ default general)`
(`POST /rooms {room:"test-room"}` → 201, `POST /rooms/test-room/join`
→ `online:["bob"]`).

### (5) Message create/list, stable ids + server timestamps

```
$ curl -s -X POST .../rooms/general/messages -H "x-bus-token: $TOK" \
    --data '{"nick":"demo","text":"hello board-compat"}'
{"index":0,"id":"msg-73c899eda43c0d26","ts":1793793452,"delivery":{"state":"stored","reason":"appended to room log"}}
$ curl -s ".../rooms/general/messages?since=-1"
{"room":"general","total":1,"messages":["demo: hello board-compat [ts:1793793452]"],"items":[{"id":"msg-73c899eda43c0d26","seq":0,...,"ts":1793793452,"tsMs":1793793452944,...}]}
```

Selftest: `ok - send + list round trip (board line + stable id + server ts)`.

### (6) Pagination (documented page size + cursor)

`PAGE_SIZE=50`, `MAX_LIMIT=200` (`server/bus.mjs:118-119`);
`messages` keeps board cap 1000. Cursor = stable `seq` or `id`,
`nextCursor` returned. Selftest:
`ok - pagination: 50-item pages + seq cursor (60 msgs -> 50 + rest)`.

### (7) Case+accent-insensitive text search

`foldText` = NFD-strip + lowercase (`server/bus.mjs:146-151`).
Live: `GET /rooms/general/search?q=HELLO` → 1 hit for
`hello board-compat`. Selftest:
`ok - search is case+accent-insensitive (cafe matches café)`.

### (8) Presence join/leave/heartbeat, 60 s expiry

`PRESENCE_TTL_MS=60000` (`server/bus.mjs:122`); sweep every 10 s;
`liveNicks` GCs on read. Selftest:
`ok - presence join/heartbeat/leave (60s TTL configured)`.
60 s wall-clock expiry asserted by constant + sweep path, not by
sleeping 60 s (stated skip).

### (9) Delivery state sent/stored/failed + reason

Stored reply: `"delivery":{"state":"stored","reason":"appended to room log"}`;
refusals: `"delivery":{"state":"failed","reason":"<named code>"}`.
Selftest covers both (201 stored; 401/400 failed).

### (10–11) Attachments: cap + allowlist + named rejection; outside JSONL, relative paths

Cap `ATTACH_MAX_BYTES=1048576`, allowlist
`image/png,image/jpeg,text/plain,application/pdf`
(`server/bus.mjs:120-124`). Selftest:

```
ok - attachment stored outside JSONL with relative path attachments/test-room/att-…-note.txt
ok - attachment download returns stored bytes
ok - negative: oversized attachment 413 attachment_too_large; bad MIME 415
```

Disk proof: `attachments/<room>/<id>-<safe>` holds bytes;
`rooms/<room>.jsonl` does NOT contain the bytes (asserted in test);
record keeps relative `path` only.

### (12) Retention never silently deletes last 500

No auto-delete path exists in `server/bus.mjs` (grep `prune` hits only
the guarded endpoint). Guard `RETENTION_MIN_KEEP=500`:

```
ok - retention: prune refused below 500, allowed at boundary (500 remain)
```

(`POST /prune {before:5}` on 5 msgs → 409
`retention_would_leave_fewer_than_500`; on 505 msgs → 200, `total:500`.)

### (13) Local-only auth token file 0600; writes refused without it

```
$ stat -c "%a %n" /tmp/bus-demo/token
600 /tmp/bus-demo/token
$ curl -s -X POST .../messages --data '{"nick":"demo","text":"nope"}'
{"error":"missing bus token: ...","code":"bus_auth_missing","delivery":{"state":"failed","reason":"bus_auth_missing"}}
```

Selftest: `ok - POST without token refused (401 bus_auth_missing)`,
`ok - token file mode is 0600`.

### (14) Upstash path optional/off by default (prove default never imports/requires it)

Default has zero remote specifiers:

```
$ grep -n -i "require\s*(.*upstash\|from\s*['\"].*upstash\|import\s.*upstash" server/bus.mjs
(no upstash import/require lines)
$ grep -n "^import" server/bus.mjs
import { createHash, randomBytes } from "node:crypto";
import { appendFileSync, ... } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
```

Env gate (`server/bus.mjs:183`): `BUS_UPSTASH=1` refuses to start:

```
$ BUS_UPSTASH=1 BUS_DATA_DIR=/tmp/bus-refuse node server/bus.mjs; echo "EXIT=$?"
bus: bus: BUS_UPSTASH=1 requests the remote bus, which is not compiled into this local-only build; unset BUS_UPSTASH to run the file-backed bus
EXIT=2
```

Selftest: `ok - default path has no upstash/redis import or require`.

### (15) Health endpoint (store path, count, last write)

```
$ curl -s http://127.0.0.1:18999/health
{"ok":true,"service":"metaos-bus","store":"file","dataDir":"/tmp/bus-demo","rooms":1,"count":0,"counts":{"general":0},"lastWrite":null,"uptimeSec":1,"pageSize":50,"maxLimit":200,"presenceTtlMs":60000,"retentionMinKeep":500}
```

Selftest: `ok - GET /health reports file store + dataDir + count + lastWrite`.

### (16) SSE stream — two clients see one message

Selftest (two concurrent `http.get /events?cursor=` readers, one POST):

```
ok - SSE: two concurrent readers saw the same message
```

### (17) Reconnect with cursor

`GET /events?cursor=<seq|id>` replays missed then streams;
`Last-Event-ID` also honoured (`server/bus.mjs`, events block).
Selftest: `ok - reconnect with cursor replays missed items (history cursor)`.

### (18) Concurrent-write safety — 50 parallel sends

Single-writer promise chain (`enqueueWrite`, `server/bus.mjs`).
Selftest: `ok - concurrent safety: 50 parallel sends stored exactly once, seqs contiguous`.

### (19) Selftest: random port, send/list/search, exit 0

```
$ node server/bus.test.mjs > /tmp/bus-selftest-full.txt 2>&1; echo "EXIT=$?"
EXIT=0
bus selftest: 23 passed, 0 failed
```

Port is `listen(0, "127.0.0.1")` → kernel-assigned
(`got 127.0.0.1:59421`, second run `:59155`, …). Full 23-line `ok`
list in `/tmp/bus-selftest-full.txt` (all lines quoted above).

### (20) Negative tests (malformed message, oversized attachment)

```
ok - negative: 4 malformed messages refused (400 + failed delivery)
ok - negative: oversized attachment 413 attachment_too_large; bad MIME 415
```

(Empty nick/text, 2001-char text, embedded newline → 400
`bus_bad_nick`/`bus_bad_text`; 1 MiB+1 attachment → 413
`attachment_too_large`; `application/x-msdownload` → 415
`attachment_mime_not_allowed`.) Test exits non-zero on any failure
(`process.exit(1)`; crash → 2).

### (21) Bind 127.0.0.1 only

```
$ cat /tmp/bus-demo.log
metaos-bus listening on http://127.0.0.1:18999 (store: file, dataDir: /tmp/bus-demo)
$ lsof -iTCP:18999 -sTCP:LISTEN -P -n
node  34499  ...  TCP 127.0.0.1:18999 (LISTEN)
$ grep -n 'listen(port, "127.0.0.1"' server/bus.mjs
1140:  server.listen(port, "127.0.0.1", () => {
```

Selftest binds `listen(0, "127.0.0.1")` and asserts
`server.address().address === "127.0.0.1"`:
`ok - bind is 127.0.0.1 (got 127.0.0.1:59421)`.
No `0.0.0.0`/`::` listener exists (lsof shows the single 127.0.0.1
row; remote check is the hardcoded host + lsof, no network device needed).
After kill: `nothing listening on 18999 (clean)`.

### (22) Structured logs room+id+result, never body

```
$ cat /tmp/bus-demo.log
metaos-bus listening on http://127.0.0.1:18999 (store: file, dataDir: /tmp/bus-demo)
{"ts":"2026-11-04T11:57:32.944Z","room":"general","id":"msg-73c899eda43c0d26","result":"stored"}
$ grep -c "hello board-compat" /tmp/bus-demo.log
0
```

Logger call site passes only `{ ts, room, id, result }`
(`logWrite`, `server/bus.mjs`). Selftest plants
`PLANTED-LOG-PROBE-…-xyzzy`, asserts absence from the log array and
presence of `{ room:"general", result:"stored" }`:
`ok - structured logs: room+id+result, planted body absent`.

### (23) On-disk format + migration from old relay

Documented in `server/README.md` ("Local message bus" section) and in
the `server/bus.mjs` header. Live layout proof:

```
$ find /tmp/bus-demo -type f | sort
/tmp/bus-demo/meta.json
/tmp/bus-demo/rooms/general.jsonl
/tmp/bus-demo/token
```

Migration rule (README + header): Upstash `muse-bus` /
`muse-bus:room:<r>` `<nick>: <text>` lines (newest-500 trim) and
`board/...jsonl` `{ room, line }` records → bus items by parsing the
line, `seq` in order, `id = msg-<16 hex>`, `ts` from `[ts:…]` (else
mtime), `BLOB:` side keys → `attachments/` with the relative path
recorded.

### (24) No required-Upstash-token in default startup (grep proof)

Default `process.env` reads are exactly four names:

```
$ grep -n "process\.env\." server/bus.mjs
128:  if (process.env.BUS_DATA_DIR && ...
131:  const base = process.env.METAOS_STATE
183:  if ((process.env.BUS_UPSTASH || "").trim() === "1") {
1132:  const port = Number(process.env.BUS_PORT || process.env.BOARD_PORT || DEFAULT_PORT);
```

No `MUSE_RELAY_URL` / `TRIO_UPSTASH_HOST` / `UPSTASH_TOKEN` reads.
Env is clean at startup:

```
$ env | grep -E "MUSE_RELAY|UPSTASH|TRIO_UPSTASH|RELAY_URL|BUS_UPSTASH"
(no remote-bus env set)
```

Selftest: `ok - default startup needs no Upstash token (env sweep clean)`.

## Report-back

- Files created: `server/bus.mjs`, `server/bus.test.mjs`,
  `os-build/lanes/R2_T3_A.md`; edited: `server/README.md` (append),
  `.gitignore` (one entry + comment).
- Endpoint list: table above (3 board-compat + 12 additive).
- Test outputs: selftest `23 passed, 0 failed`, `EXIT=0`
  (`/tmp/bus-selftest-full.txt`); `BUS_UPSTASH=1` startup `EXIT=2`;
  live curl demo on `:18999` (health/rooms/send-refused/send/list/
  search/lsof) pasted above.
- Skipped + why: no edits to forbidden paths (board/bus.html/app
  pages/face/identity/provision.sh/image units); no QEMU (lane bans
  it); no 60 s wall-clock presence-expiry sleep (constant + sweep path
  proven, sleep would stall the lane); no WebSocket (SSE satisfies
  "SSE or WebSocket"); no full `npm test` sweep (other lanes' files in
  flux + Section E scope — bus selftest + curl proofs run instead).
- No daemon left running (lsof clean after kill; selftest closes its server).

## Cross-lane requests (file:line)

1. T4 (pages): `js/site-chat.js:185-196` POSTs messages with no auth
   header — writes to the bus need `x-bus-token` (or Bearer). Request:
   have the desk chat read the local token (or a T4-owned proxy) and
   send it on POST/notify/presence; reads stay open so polls are
   unaffected. Same for `board/board.html:288-315` composer.
2. Image/provision: `os-build/face/provision.sh:480-483` runs the
   Board with `BOARD_PORT=18935`. The bus defaults to the same port
   (`server/bus.mjs:125,1132`). Request: pick the split (bus takes
   18935 and board retires, or bus takes e.g. 18937 and T4 repoints
   `site-chat.js:12` default + `notify.js:16`), owned outside this lane.
3. Agent/intel migration: 18 files still `import relay_common`
   (`os/intel/spark_client.py:97`, `store.py:140`, `ingest.py:34`,
   `brief.py:91`, `notify.py:49`, `spark_agent.py:65`, `join.py:377`,
   `integration.py:86`, plus e2e/load/spoof drills) but the module is
   absent from the tree. Request: repoint these callers at the bus HTTP
   shape in a follow-up (this lane ships the server, not the callers).
4. Queue hook needs no change: `server/queue/trio_agent.py:94,112-115`
   already POSTs `{ severity, topic, text }` to
   `{base}/rooms/main/notify` — set `TRIO_RELAY_URL` to the bus base
   URL and notifies land.
