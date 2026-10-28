# Meta Sentinel / Ember / Sanitas — Team First Response

(To the v2 master directive, 2026-10-28. Prepared by Pax, Agent 4 integration lane. Verified items are labeled; everything else is proposal.)

## 1. What currently exists in the repository

VERIFIED by inspection, 2026-10-28:
- Repo `mrfentmen/meta-sentinel` (public) created today. Contents: project README, BRIEF.md (the v1 Sentinel-only brief), and the Agent 1 UI first cut: index.html, styles.css, package.json, js/{app,camera,sampler,client,log,schema}.js, tests/ui.test.mjs, UI_README.md. Tip commit bbd3b5f.
- UI tests: 30/30 pass (node built-in runner), re-run by Pax.
- The UI is real but has NO model backend: it captures camera frames, samples every 3s (disclosed), POSTs to /api/assess, validates replies against the v1 brief schema, renders assessments, and exports a session log. With no backend it honestly shows "backend not connected". Zero hardcoded detections.
- Ember and Sanitas: nothing exists yet beyond this directive.
- No API credentials are in the repo or in any checked config. No secrets committed.

## 2. Meta AI capabilities available — verified vs unverified

- VERIFIED (Del's word, 2026-10-27): Del holds a confirmed Meta Model API key. The key has never been shared with the crew and must reach the server side via secure entry only.
- VERIFIED (hackathon Participant Guide): the Meta Model API family for this hackathon is Muse Spark, Muse Image, Muse Wonder, and SAM 3.1.
- NOT VERIFIED: that the Spark API accepts image input, its rate limits, or its structured-output behavior. No live Spark call has ever been completed by this team. Earlier stand-in tests proved only our own HTTP plumbing against a non-Meta endpoint — they say nothing about Spark.
- SAM 3.1: segmentation/identification only; no temporal reasoning. Adopt only if a measured comparison shows it improves the pipeline (directive section 7). Otherwise document and skip.
- Muse Image / Wonder: no meaningful role identified for this prototype. Not integrated, per the directive's rule against product-count padding.

## 3. Proposed architecture (all three products)

One static web app + one thin server endpoint. No framework, no build step (matches the existing UI).

- Browser app (shared): product switcher (Sentinel / Ember / Sanitas), camera + image input, frame sampler, assessment client, timeline, session log export. Per-product config object drives: product name, department, accent identity, categories, limitation notice, input mode (Sentinel = live camera; Ember = prerecorded footage/stills; Sanitas = still images).
- Server endpoint POST /api/assess: holds the API key server-side (never in the browser), receives {product, timestamp, image}, applies the product's prompt profile, calls the model, validates the reply against the unified v2 contract, returns it or an explicit error. Measured latency is stamped by the server, never invented.
- Evaluation harness (Agent 3): consumes exported session logs (Sentinel) and labeled image sets (Ember/Sanitas) and computes precision/recall/FP/FN/latency per product, separately.

## 4. Shared component reuse

Already built and shared as-is: camera.js, sampler.js, client.js, log.js, styles.css.
One deliberate contract change, coordinated here before parallel work: schema.js migrates from the v1 flat schema to the directive's unified v2 contract (adds product, nested assessment, processing). Agent 1 (Hana) executes the migration; Agent 2 builds the server to emit exactly that shape; Agent 3's harness reads exactly that shape. No other interface changes without Agent 4 sign-off on the bus.

## 5. Agent responsibilities and contracts (assignments ruled by Del)

- Agent 1 — Hana: shared frontend, product configs, schema v2 migration, responsive/error states.
- Agent 2 — Rowan: API verification first (image input? limits?), server endpoint, model adapter, structured responses, credential handling server-side.
- Agent 3 — Milo: scenario/ground-truth sets for all three products, evaluation scripts, metrics, failure analysis, baseline comparison.
- Agent 4 — Pax: architecture, contract freeze, integration, end-to-end verification by running it, demo prep, blockers list.
- Contract: client → server {product, timestamp ISO-8601, image dataURL}; server → client: the v2 assessment JSON or {error}. Both sides validate.

## 6. First end-to-end milestone

Sentinel live path: Del performs staged actions on a phone camera → frame sampled → REAL Spark assessment → validated v2 JSON → displayed with uncertainty and evidence. Ember/Sanitas follow on the same core once this path is proven.

## 7. Acceptance criteria for the milestone

1. A real model response is logged with the actual model identifier and server-measured latency.
2. The response passes v2 schema validation on both server and client.
3. Three staged scenarios (normal walking, dancing, staged altercation) produce assessments whose observations match ground truth as judged by Del.
4. At least one ambiguous case is shown with honest uncertainty text.
5. No fabricated fields: confidence stays null unless the model returns it; nothing is hardcoded.

## 8. Highest-risk assumptions

1. Spark API image support and limits are unverified — the entire critical path depends on them. Agent 2 verifies before anything else is built on it.
2. Del's standing Meta World ruling was "live Spark call at the very end". Sentinel needs a live call NOW to prove the path. This needs Del's explicit exception for Sentinel, plus the key via secure entry to the server side. This is the one decision that blocks Agent 2.
3. Round-trip latency vs the 3s sampling cadence; mitigated by the sampler's skip-while-in-flight rule (already implemented).
4. Ember/Sanitas labeled test imagery must be sourced (public/Wikimedia) and labeled before evaluation can run — Agent 3 starts this in parallel today.
5. Scope: three products, one shared core, 7 days. The core-first order is not optional; product-specific work that does not ride the shared core waits.

## 9. Schedule (all times ET, deadline Nov 4 21:00)

- Oct 28: contracts frozen (this document), schema v2 migration, product configs, Agent 2 API verification.
- Oct 29: Sentinel end-to-end proof against the acceptance criteria (needs item 8.2 decided).
- Oct 30: Ember + Sanitas on the shared core; labeled datasets complete.
- Oct 31 – Nov 1: evaluation runs, metrics, failure analysis, baseline comparison.
- Nov 2: feature freeze (major features). Fixes only after.
- Nov 3: demo rehearsals, prerecorded backup inputs, submission package.
- Nov 4: demo video, submit before 21:00. Del submits.
