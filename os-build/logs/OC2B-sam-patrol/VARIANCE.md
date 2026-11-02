# OC2B SAM variance record (OC2B-405)

Three live `models.segment` calls (sam-3.1, POST /v1/responses), one
attempt each, no retries. Receipts: scratch file
`receipts-sam.jsonl` (4th wiring call in `receipts-wiring.jsonl`);
copied lines appended at the end of this file's source group in
`OC2B-model-receipts-index.md`.

| frame | prompt object | box? | coordinates |
|---|---|---|---|
| frame1 `ignis-fire-1.jpg` | visible flame region, left side of structure | NO | n/a — Responses call succeeded (receipt `images_processed: 1`, 643 ms) but `output` carried empty text; `parse_sam_text` raised `ValueError`, recorded as-is |
| frame2 `ignis-fire-2.jpg` | burning vehicle, engine compartment in flames | YES | box_px x1=381 y1=257 x2=1279 y2=538 on 1280x846; region x=298 y=304 w=702 h=332 (0-1000 scale); mask data 53,8xx chars (truncated to 200 chars + length in `parsed_box.json`, full text in `raw_response.json`); 1412 ms |
| frame3 `vigiles-knife-1.jpg` | knife in the person's hand | NO | n/a — call succeeded (572 ms), empty output text; `ValueError` recorded as-is |
| wiring re-run `ignis-fire-2.jpg` | flagged subject (burning vehicle) for the patrol record | NO | n/a — call succeeded (1468 ms, receipt in `receipts-wiring.jsonl`), empty output text; same frame returned a box minutes earlier under a different prompt |

Variance verdict: SAME frame (ignis-fire-2) returned a box once and
no box once under different prompts; two other frames returned no
box. Matches Pax's probe note and OC1's observation: SAM 3.1 output
varies run to run. No box was invented anywhere; every no-box is a
recorded `ValueError: SAM output carried no <|box;...|> segment`.

Per-frame dirs: `frame1/` (raw_response.json, parsed_box.json,
overlay.jpg stamped NO-BOX), `frame2/` (same trio, overlay.jpg with
red box), `frame3/` (same trio as frame1).
