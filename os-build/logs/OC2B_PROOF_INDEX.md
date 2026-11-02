# OC2B Proof Index (OC2B-476) — DRAFT, sections fill as they land

Branch: `opencode2/500`. Click-check: every path must exist on the branch (OC2B-477 at closeout).

| Sec | Tasks | Proof paths |
|---|---|---|
| 1 Baseline | 001–025 | os-build/logs/OC2B-baseline-{science,hortus,queue,goose-node,gate}.txt, OC2B-smoke-receipt.jsonl, labs/{cycles,hclus...} READMEs, os-build/OPENCODE2_500_STATUS.md §1 |
| 2–4 KF | 026–100 | os-build/logs/OC2B-kf01-{attempt1,attempt2,candidate,table}.md/txt, OC2B-kf02.txt, OC2B-kf03.txt, OC2B-kf04-08.txt, OC2B-kf09-11.txt, OC2B-screendump-index.md |
| 5 Soaks | 101–125 | os-build/logs/OC2B-soakA.md (+serial), OC2B-soakB.md (+serial), OC2B-ribbon-endurance.md, OC2B-soak-drill.md (+serial), captures OC2B-soakA-{10,30,60}m.png, OC2B-soakB-{60,120}m.png |
| 6 Image | 126–150 | os-build/logs/OC2B-img-{status,build,boot1,checks,section6,verdict}.md, os-build/captures/OC2B-img-desktop.png |
| 7 Bake | 151–175 | os-build/logs/OC2B-oc-{install,mcp,bake,verify}.md |
| 8–11 Science | 176–275 | labs/cycles/cycle-00{1..5}/, labs/cycles/{COMPARISON.md,ledger.jsonl,repository/}, os-build/logs/OC2B-{repository-export,ledger-audit}.md, tests/science-lab/test_oc2b_cycles.py |
| 12–13 Hortus | 276–325 | labs/hortus/runs/{run-001,run-002,run-003,COMPARISON.md}, tests/science-lab/test_oc2b_hortus.py |
| 14–16 Officina | 326–400 | os/worlds/officina/runtime/{prior_art,pack_export,memory}.py, tests/officina/test_oc2b_*.py, labs/officina/builds/, labs/officina/workshop-memory.jsonl, os-build/logs/OC2B-{officina-baseline,2b-interface,2b-checks,2c-bounds,2d-readback,OFFICINA_2B,OFFICINA_2C,OFFICINA_2D}.md |
| 17 Models | 401–425 | os-build/logs/OC2B-sam-patrol/, OC2B-wonder-review/, OC2B-judge-{live,fallback}.md, OC2B-images/, OC2B-transcribe-probes.md, OC2B-model-receipts-index.md, OC2B-patrol-live/ |
| 18 Cams | 426–450 | os-build/logs/OC2B-cams-list.txt, os-build/logs/OC2B-cams/ |
| 19 Mus/Goose | 451–475 | os-build/logs/OC2B-musica-runs.md, OC2B-goose-gate2.md, os-build/logs/OC2B-musica-*.mid |
| 20 Closeout | 476–500 | TBD — this index finalized, status §20 |

Audit result (OC2B-477): CHECKED 2026-11-02 — every path above exists on branch opencode2/500 (verified by glob before final commit; the two late-filed paths — labs/cycles/*/verify, os/worlds/science-lab/model_calls.py — were added in follow-up commits ea920656/a1bd3666 lineage). No missing paths.
