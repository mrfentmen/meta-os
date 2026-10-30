# RUNBOOK — loading up the Meta Trio stack

One command starts the whole demo stack. This is the sequence for
Del's Mac; everything below runs locally on that machine.

## 1. Get the code

```sh
git clone https://github.com/mrfentmen/meta-sentinel.git
cd meta-sentinel
# (or, on an existing checkout: git pull)
```

## 2. Set the model key — Del's hands only

In the same terminal that will start the stack:

```sh
export SPARK_API_KEY=<the Meta Model API key>
```

The key lives only in that shell's environment. Never in a file, a
commit, an envelope, or a log. With the key set, the resident agent
uses the production direct transport to Muse Spark.

(The app server's built-in *direct* fallback also reads this key, and
additionally sits behind the `ASSESS_LIVE_MODEL=1` gate — the queue
path below is the primary route and does not need that gate. Open the
gate only if you want the fallback armed.)

## 3. Start the stack

```sh
./run-stack.sh
# (if a fresh clone refuses to run it: chmod +x run-stack.sh once,
#  or invoke it as: bash run-stack.sh)
```

It starts four processes and waits for each to answer its health
check before printing the URLs:

| Piece | URL |
| --- | --- |
| Meta Nuntius viewer | http://127.0.0.1:8787/ |
| Queue service health | http://127.0.0.1:8935/health |
| Resident agent | (no URL — it polls the queue and posts NOTIFY lines to Nuntius) |
| Web console + API | http://127.0.0.1:8080/ — `POST /api/assess` |

## 4. Open the products

- **Web console:** http://127.0.0.1:8080/ — pick Vigiles, Ignis, or
  Medicus and assess a frame or the live camera.
- **Native app:**

  ```sh
  cd native && ./Scripts/make-app.sh
  open MetaTrio.app        # first time: right-click -> Open
  ```

  The native app's default endpoint is `http://localhost:8080/api/assess`,
  which is the app server started in step 3 — no reconfiguration.

## 5. What a healthy boot looks like

- run-stack prints `up:` for the relay, the queue service, the
  resident agent, and the app server, then the four URLs.
- http://127.0.0.1:8080/api/health answers `{ ok: true, ... }`.
- The queue service health names its store honestly
  (`upstash-redis`, or the labelled SQLite fallback).
- Assess a frame in any product: an assessment comes back (the queue
  path answers in roughly 5–20 seconds), and a matching
  `NOTIFY ... [trio-result] ...` line appears in the Meta Nuntius
  viewer at http://127.0.0.1:8787/.

## 6. Stop

Ctrl-C in the run-stack terminal. The script kills all four
processes on exit.

## Honest status (2026-10-30)

- **Queue leg end to end — VERIFIED LIVE.** The app server's
  `/api/assess` with the queue enabled, the queue service on the live
  store, and the resident agent answering: proven live, most recently
  as the full run-stack composition — steam test frame in,
  HTTP 200 with a contract-valid assessment (category
  **"steam or fog"**, independently re-validated), the queue result
  envelope and the Nuntius NOTIFY line both naming the same job id,
  spend delta exactly +1 guarded call.
- **DEV helper transport (`TRIO_SPARK_VIA_HELPER=1`) — VERIFIED
  LIVE**, and it is what every sandbox proof above ran on. It exists
  only in Pax's sandbox (a connector helper with a vaulted key).
  If `SPARK_API_KEY` is missing, run-stack.sh warns and selects it —
  on the Mac that path is not the production route, so set the key
  (step 2) instead of relying on the fallback.
- **Production direct transport (`SPARK_API_KEY`) — STUB-TESTED
  ONLY.** The request shape (endpoint, model `muse-spark-1.3`, text +
  `image_url` parts, key only in the `Authorization` header) mirrors
  the verified server transport and is covered by stubbed-HTTP unit
  tests, but it has never run against the real API with a real key —
  the sandbox holds no raw key by design. **The Mac run in this
  runbook is its first live verification.**
- **Native app — builds and runs on the Mac only.** The sandbox has
  no Swift toolchain, so `make-app.sh`, the camera, and the native
  round trip verify on the Mac too.
