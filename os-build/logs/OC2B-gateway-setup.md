# OC2B live MCP gateway setup record

Branch `opencode2/500`, tip `8a115f4e`. Gateway left RUNNING (nohup, PID file
`/tmp/oc2b-gateway.pid`). Committed files untouched: `backends.json` restored
byte-identical (sha256 `8b7be5b909bec7900a3aede3659208515e75fee59dc7d7954867d89ac63bc281`,
`git diff --stat` empty at end). No commits, no pushes, no status-file edits.

## 1. Venv (`mcp-gateway/.venv/`)

- System `python3` is 3.9.6 — too old (`mcp` requires `>=3.10`). Venv built with
  Homebrew `/opt/homebrew/bin/python3.14` (3.14.8), NOT the README's `python3`.
- `pip install mcp starlette uvicorn` first pulled **mcp 2.3.0**, which broke the
  committed `gateway.py`: 2.x lowlevel `Server` dropped the `list_tools()` /
  `call_tool()` decorator API (constructor `on_list_tools=`/`on_call_tool=`
  instead) — gateway crashed at startup with
  `AttributeError: 'Server' object has no attribute 'list_tools'`.
  Fix (no repo file touched): pinned `mcp==1.30.0` (last 1.x, decorator API + 
  `StreamableHTTPSessionManager` present).
- Recorded versions: **mcp 1.30.0, starlette 1.10.0, uvicorn 0.54.0**
  (+ httpx 0.28.1, pydantic 2.x). Node v24.21.0, npm 11.19.0.
- `.venv/` does NOT pollute git: the venv ships its own `.gitignore` (`*`).

## 2. Lab server installs (`mcp-gateway/lab-servers/`, single `npm install`)

Per-server package decision (bare name preferred to mirror Pax's paths; scoped
`@mrfentmen/*` only where bare fails the SERVER_SPECS tool contract):

| server | installed | rejected alternative + reason |
|---|---|---|
| openalex | `@mrfentmen/openalex-mcp@1.1.0` | bare `openalex-mcp@0.1.8`: no `get_work` (has `get_entity` instead); scoped has exactly `search_works`+`get_work` |
| archiveorg | `archive-org-mcp@1.0.6` | — (`search_items`+`get_item` OK, `dist/index.js`) |
| openlibrary | `open-library-mcp@1.0.2` | — (`search_books`+`get_work` OK) |
| gbif | `gbif-mcp@1.0.1` | — (`match_species`+`get_species` OK) |
| wikidata | `@mrfentmen/wikidata-mcp@1.0.3` | bare `wikidata-mcp@1.0.1`: `bin/` is a remote-SSE proxy (`npx mcp-remote` to a third-party URL), not a local server; scoped has `search_entities`+`get_entity` |
| wikisource | `wikisource-mcp@1.0.3` | — (`search_texts`+`read_text` OK) |
| ietf | `ietf-mcp@1.0.2` | — (`search_documents`+`get_document` OK) |
| fedreg | `@mrfentmen/federal-register-mcp@1.0.4` | bare `federal-register-mcp@0.1.0`: wrong tools (EO-only `search_executive_orders` etc., needs Node 25+ `node:sqlite`); scoped has `search_documents`+`get_document` |
| osv | `osv-mcp@1.0.2` | — (`check_package`+`get_vulnerability` OK) |

Note: the three rejected bare packages remain unused inside `node_modules/`;
`lab-backends.json` references only the 9 chosen builds. Scoped entry points are
`node_modules/@mrfentmen/<pkg>/dist/index.js`; bare (except openalex→`build/`)
are `node_modules/<pkg>/dist/index.js`.

## 3. Trimmed config (`mcp-gateway/lab-backends.json`)

9 backends, prefixes exactly matching SERVER_SPECS
(`openalex archiveorg openlibrary gbif wikidata wikisource ietf fedreg osv`),
absolute local paths, `port 8931`. Committed `backends.json` left byte-identical.

## 4. Start (config-swap dance)

`gateway.py` hardcodes `backends.json` (line 28, no env/flag override), so:
backup `backends.json` → copy `lab-backends.json` over it → start
`SCIENCE_LAB_MCP_GATEWAY_DIR=/Users/test/meta-os-500/mcp-gateway nohup
.venv/bin/python gateway.py` (ran the python directly: `start-gateway.sh` is not
executable) → all 9 backends logged `up` (openalex 10 tools, archiveorg 10,
openlibrary 10, gbif 3, wikidata 10, wikisource 10, ietf 10, fedreg 10, osv 10)
→ restored `backends.json` from backup (running process already holds config).
Gateway log: `/private/var/folders/r0/mc2kkvz94f32cfbmq91kj7p40000gn/T/oc2b-gateway.log`.

## 5. Smoke (via `mcp_call.py` → `http://127.0.0.1:8931/mcp`)

Searches — 9/9 pass, first attempt, exit 0:

- `openalex__search_works {"query":"CRISPR","limit":3}` → 378237 works; top
  "The Heroes of CRISPR" (Cell 2016, 493 citations).
- `archiveorg__search_items {"query":"prelinger","limit":3}` → items incl.
  `206151-home-movie-005641-master`.
- `openlibrary__search_books {"query":"dune frank herbert","limit":3}` → 121
  results; "Dune" `/works/OL893414W`.
- `gbif__match_species {"name":"Panthera leo"}` → usageKey 5219404, EXACT,
  confidence 99.
- `wikidata__search_entities {"query":"Marie Curie"}` → top Q7186.
- `wikisource__search_texts {"query":"Treaty of Versailles"}` → totalhits 688.
- `ietf__search_documents {"query":"http","limit":3}` → `total_count 0`,
  `objects []` (valid empty response, not an error).
- `fedreg__search_documents {"term":"climate"}` → count 10000; first doc
  `2026-22082` (EPA oil/gas NSPS reconsideration).
- `osv__check_package {"name":"lodash","ecosystem":"npm"}` → 10 vulns, incl.
  `GHSA-29mw-wpgm-hmr9` (CVE-2020-28500).

Reads — 6/9 pass first attempt; 3 needed one arg-shape correction (single retry
each, all then passing):

- `archiveorg__get_item` / `wikidata__get_entity(Q7186)` /
  `wikisource__read_text` / `ietf__get_document(rfc2616)` /
  `fedreg__get_document(2026-22082)` / `osv__get_vulnerability(GHSA-29mw-wpgm-hmr9)`:
  all genuine payloads (wikisource carries a server-side API warning
  `exchars 4000 > 1200` but returns the page; ietf returns `total_count 1`).
- `openalex__get_work {"id":"https://doi.org/10.1016/j.cell.2015.12.041"}` →
  exact error `Error: OpenAlex error 404` (DOI URLs not accepted); retry with
  `{"id":"https://openalex.org/W2239190724"}` (resolved via api.openalex.org) →
  "The Heroes of CRISPR" PASS.
- `openlibrary__get_work {"key":"/works/OL893414W"}` → exact error
  `ERROR: Input validation error: 'm0_key' is a required property` (server
  schema names the arg `m0_key`, not `key`); retry `{"m0_key":"/works/OL893414W"}`
  → "Dune" PASS. **FLAG for lab owner: `mcp_backends.py` SERVER_SPECS maps
  `locator→key`, but this server requires `m0_key` — live lab reads via the
  `MCP-GATEWAY` backend will fail validation until the map is updated.**
- `gbif__get_species {"key":5219404}` → exact error
  `ERROR: Input validation error: 5219404 is not of type 'string'`; retry
  `{"key":"5219404"}` → `"key": 5219404` PASS. **FLAG: gbif keys must be sent
  as strings; `build_wire_args` passes numbers through.**

## 6. Liveness / URL check

- PID file `/tmp/oc2b-gateway.pid` (PID 47073 at setup end), `kill -0` OK.
- Raw `curl POST http://127.0.0.1:8931/mcp` → `HTTP 307` redirect to `/mcp/`
  (Starlette Mount trailing-slash; direct curl without a client is not a valid
  MCP handshake). Authoritative check: `mcp_call.py list` + all 18 smoke calls
  through `http://127.0.0.1:8931/mcp` succeeded.

## 7. Wall time

~6 min venv+npm+boot (epoch 1793672163 → gateway up), plus ~1 min smoke/reads;
total ≈ 7 min.

## 8. Final tree state

Only new untracked files: `mcp-gateway/.venv/` (self-ignored, invisible to git),
`mcp-gateway/lab-servers/`, `mcp-gateway/lab-backends.json`, and this file.
`git diff --stat` empty. Gateway RUNNING on the trimmed config.
