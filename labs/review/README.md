# labs/review/ — read-only review tools

Small pages that read the product's own outputs and draw them. Nothing
here edits the repo: `js/schema.js` and `js/products.js` are imported or
read, never written. Sample data is ours and every sample is SIMULATED.

- `bolo.html` — paste an incident JSON (or Load sample), renders the BOLO
  card: description + visible marks only, ID line UNIDENTIFIED, no name
  field anywhere. Serve the folder (`python3 -m http.server`) and open it.
- `timeline.html` — file picker or sample button loads a records JSONL,
  draws patrol → review → investigate → dispatch in timestamp order.
- `cannot-do.html` — renders the limits straight from `js/products.js`
  (displayName + limitations). Same server, open the page.
- `tier-counter.mjs` — `node labs/review/tier-counter.mjs <records.jsonl>`
  prints yellow/red/none/other counts.
- `sample-records.jsonl` — 6 SIMULATED records (3 yellow, 2 red, 1 none).
- `sample-incident.json` — record 001 alone, for the BOLO page.
- `tests/` — node:test suites (run: `node --test labs/review/tests/`).
