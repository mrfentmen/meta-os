# Meta Trio assessment server

Rowan's lane: the server side of the frozen v2 contract
(`MASTER_DIRECTIVE_V2.md` §9), shared by Meta Vigiles, Meta Ignis, and
Meta Sanitas. Zero dependencies, no build step — plain Node, like the
rest of the repo.

## Run it

```sh
npm start            # node server/server.mjs
# or: PORT=8080 node server/server.mjs
```

Default port is **8080**, which is the native app's default endpoint
(`http://localhost:8080/api/assess`). The web app's default endpoint is
the relative `/api/assess`; this server also serves the static web app
from the repo root, so one process runs the whole demo stack locally.

## Routes

| Route | What it does |
| --- | --- |
| `POST /api/assess` | One frame in, one v2 assessment out (below). |
| `GET /api/health` | `{ ok, service, products, model: { configured, live_enabled } }`. Never exposes key material. |
| `GET /…` | Static web frontend (`index.html`, `styles.css`, `js/`). |

## The contract

Request body (exactly what both clients already send):

```json
{ "product": "vigiles" | "ignis" | "sanitas",
  "timestamp": "ISO-8601 with timezone",
  "image": "data:image/jpeg;base64,…" }
```

Success is HTTP 200 with the v2 assessment object from `js/schema.js`,
validated server-side against that same schema before it is sent.
Failure is an HTTP status plus the contract error shape
`{ "error": "…" }`, which both clients surface as the real error:

- `400` — request failed validation (product, timestamp, image envelope,
  JPEG magic bytes, 8 MB decoded-image cap). The model is never called.
- `413` — request body over the 12 MB envelope cap.
- `502` — the model call failed, or its response failed contract
  validation (off-contract output is never passed through).
- `503` — no model assessment is available right now (held / not
  configured / transport not wired — the message says which).

The server never fabricates an assessment. No model, no assessment —
only the honest error.

## Model wiring and the Spark rule

Del's ruling (2026-10-28): **Spark stays off until the build is complete
and Del green-lights the test phase. No live calls during the build.**

`server/model.mjs` is the only place a model call can leave this
server, and it refuses in layers:

1. `ASSESS_LIVE_MODEL` unset → every call refused as *held*, even with a
   key present.
2. Gate open, no key → refused as *not configured*.
3. Gate open, key present → refused as *transport not wired*: the Spark
   transport lands in the test phase, verified against the real API
   before use, instead of being guessed at now.

Configuration is environment-only, server-side:

| Variable | Meaning |
| --- | --- |
| `SPARK_API_KEY` | The model key slot. Never in a request, a commit, or a log. |
| `ASSESS_LIVE_MODEL` | `1` opens the test-phase gate. Leave unset during the build. |
| `PORT` | Listen port, default `8080`. |

Per-product prompt profiles (categories + limitations) are derived from
`js/products.js` in `model.mjs` (`PRODUCT_PROFILES`), so the server and
the clients cannot drift.

## Tests

`npm test` runs the whole repo suite, including `tests/server.test.mjs`:
request/image validation, every adapter refusal state, contract
validation of model output (via a labelled test double injected at the
handler boundary — tests only), and live HTTP checks of health, the
held state, bad JSON, wrong methods, and static serving.
