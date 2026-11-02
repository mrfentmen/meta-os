# Live cameras for Imperium — NYC DOT source (Del's order, 2026-11-02)

**What was asked:** "add ip cams like earth cam."

**What shipped:** `server/queue/livecams.py` — a live public-camera source
for the Imperium patrol, plus offline tests
(`tests/queue-python/test_livecams.py`, 12 tests).

## The source decision

- **NYC DOT traffic cameras: IN.** The city publishes its camera network
  as public data: a JSON list at `https://webcams.nyctmc.org/api/cameras`
  (id, name, latitude, longitude, area, isOnline, imageUrl — shape
  verified live by Pax on 2026-11-02) and a refreshing JPEG still per
  camera at its `imageUrl`. Hundreds of cameras across the five
  boroughs, including Brooklyn streets. Polling stills is the patrol's
  native shape: fetch a frame, assess it, record it.
- **EarthCam / SkylineWebcams / Windy: embed-only, never pulled.** Those
  feeds are licensed for the networks' own players. Embedding a
  sanctioned player in the face is fine; scraping the raw feed into the
  pipeline is against their terms and is not built.

## How it plugs in

- `LiveCamSource.frame()` returns `(camera, image_bytes, timestamp)` —
  the patrol's snapshot shape. Round-robin across the selected cameras;
  a dead camera is skipped; if every camera fails, it raises and the
  caller records the failure. No frame is ever invented.
- `fetch_snapshot` refuses non-image bytes: an error page can never
  become a patrol frame.
- CLI: `--list` (online cameras, filterable by `--area` / `--name`),
  default mode saves snapshots + records (sha256, fetch time, camera
  identity) to `server/queue/livecam_records/`, and `--assess-one`
  runs one live frame through the production assessment
  (`spark_gen.generate`, the same path as the staged evals) and records
  the reading as `live-reading.json`, labelled live with its camera.

## Verification state (honest)

- Unit tests: 12/12 offline (parse, filters, deterministic pick,
  snapshot refusal, round-robin, dead-camera skip, all-dead raise).
- API shape: verified live on 2026-11-02 through a read of the real
  endpoint (the JSON above is quoted from it).
- **Live frame fetch + live reading: NOT yet run from Pax's sandbox.**
  The sandbox's direct egress to webcams.nyctmc.org is refused by the
  upstream (connection dropped for both curl and Python; the site's API
  was readable only through the browser fetcher). The stack runs on
  Del's Mac, where the one-command proof is:

  `python3 server/queue/livecams.py --assess-one --area Brooklyn`

  Its output (`livecam_records/live-reading.json` + `live-frame.jpg`)
  is the live-path proof artifact; until it exists, the live reading
  claim is UNPROVEN and the staged-eval labels stand as they were.
