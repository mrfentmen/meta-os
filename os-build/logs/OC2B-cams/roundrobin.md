# OC2B-438/439/440/446/447/448 — round-robin, staleness, exclusion, JPEG, by-id, delta

Date (UTC): 2026-11-02. All fetches via `server/queue/livecams.py` (module unedited).

## OC2B-438 — round-robin: 5x LiveCamSource.frame() (no area filter, default fetch)

1. ` Belt Pkwy @  Guy R Brewer Blvd ` [Queens] id f4633287-e3eb-463e-a73c-0917e6243c5b (23123 bytes)
2. ` WEBSTER AVE @ NEREID AVE` [Bronx] id 6a841f4c-93ef-4f51-b38d-80e70053ff8d (35070 bytes)
3. `1 Ave @ 110 St` [Manhattan] id f2b94b32-fc41-42b6-935d-8330374ca05a (25347 bytes)
4. `1 Ave @ 124 St` [Manhattan] id 38c07664-0329-471e-997f-6a9015a5bcef (20713 bytes)
5. `1 Ave @ 14 St` [Manhattan] id 23994d9e-7e59-4808-8d47-405f779d19cf (21549 bytes)

Verdict: 5 calls rotated across 5 distinct cameras (Queens -> Bronx -> Manhattan x3);
no repeats. Rotation follows the source's deterministic name-sorted order.

## OC2B-439 — staleness: same camera twice, 5+ min apart

Camera: `3 Ave @ 60 St` [Brooklyn], id 88278063-8891-4144-9295-f5dc9a94d2ea
- t1 2026-11-02T16:07:02.824930+00:00 sha256 05ac7f595f3cec821afef8bb323e45a368107cd2bd0a4c4f7a328c74d66c6f0a (15797 bytes)
- t2 2026-11-02T16:13:26.868287+00:00 sha256 5d0962b892f55c80b26bee6b353f3c37df6298b580066a1fb3cfb647fea9a95 (16012 bytes)
- Interval: 384 s. Verdict: BYTES CHANGED — the still refreshes; the feed is live, not stale.

## OC2B-440 — offline-camera exclusion

- Live payload on 2026-11-02 contains ZERO isOnline=false entries (976/976 true;
  raw saved to /tmp/cams-raw.json during the run, not committed).
- Exclusion is proven through the production gate `livecams.parse_cameras`:
  an injected entry `cam-offline-demo` ("Offline Demo @ Nowhere", isOnline "false",
  same field shape as the DOT API) is absent from the parsed result
  (976 parsed, injected id not present).
- Repo's own offline fixture id `cam-off` (tests/queue-python/test_livecams.py,
  isOnline "false") is likewise filtered by the same gate (covered by the 12/12 suite).

## OC2B-446 — JPEG verification (Brooklyn frame)

- File: brooklyn/88278063-8891-4144-9295-f5dc9a94d2ea_2026-11-02T16-07-02.110613p00-00.jpg
- Magic bytes: ffd8ffe0 (JPEG SOI). `livecams.is_image_bytes` -> True.
- PIL 11.3.0: format JPEG, size 352x240, decodes clean (verify + reopen).
- Size audit: largest frame in OC2B-cams/ is 35070 bytes (Bronx); zero files >1 MB,
  so no recompression was needed and none was applied.

## OC2B-447 — direct by-id fetch (id quoted from the §18 list output)

- Chose the 2nd Brooklyn entry from `pick(area=Brooklyn)`: `3 Ave @ 63rd St`,
  id 7faf5dd7-7f16-48c2-a35e-fee36f3da7d4
  (imageUrl https://webcams.nyctmc.org/api/cameras/7faf5dd7-7f16-48c2-a35e-fee36f3da7d4/image,
  quoted from OC2B-cams-list.txt).
- Fetched with `livecams.fetch_snapshot` directly (not via round-robin):
  19534 bytes, JPEG magic OK.
- Saved: brooklyn/byid_7faf5dd7-7f16-48c2-a35e-fee36f3da7d4_2026-11-02T16-07-04.075837p00-00.jpg

## OC2B-448 — online count vs committed livecam_records (main)

- §18 live online-camera count (this run): 976 (all isOnline true; 377 Manhattan /
  211 Queens / 207 Brooklyn / 100 Staten Island / 81 Bronx).
- Committed `server/queue/livecam_records` on main: 2 files = 1 frame
  (live-frame.jpg, 28402 bytes, Bay Pkwy @ 78 St) + 1 reading (live-reading.json).
- Delta: 976 live vs 1 committed frame = +975 (the committed dir is a single
  proof capture from 2026-11-02, not a census; the list endpoint is the census).
