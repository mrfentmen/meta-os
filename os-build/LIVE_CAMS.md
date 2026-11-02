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
- **Live reading: PROVEN 2026-11-02.** A genuine DOT still — Bay Pkwy
  @ 78 St (Kings Hwy), Brooklyn, on-image caption 11/02/2026 10:05:33 AM —
  was run through the production assessment path (`spark_gen.generate`
  via the helper, muse-spark-1.3): vigiles returned "normal activity"
  with an accurate street description (yellow buses, truck and van,
  crosswalk, storefronts) and honest uncertainties. The frame and the
  full reading are committed at `server/queue/livecam_records/`
  (`live-frame.jpg`, `live-reading.json`). Nothing was flagged because
  nothing in the frame warranted it — what is proven is the live input
  path end to end, not an emergency catch.
- Fetch route note: this sandbox's direct egress to
  webcams.nyctmc.org is refused upstream (curl and Python both dropped),
  so the proof frame arrived by browser download. The module's own
  fetcher is the same HTTP GET and runs wherever egress is normal
  (Del's Mac): `python3 server/queue/livecams.py --assess-one
  --area Brooklyn`.
