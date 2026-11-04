# os-build/logs/ — what the evidence proves, and when it was made

674 files, ~15 MB, all written 2026-11-01…03. Generated output kept as
evidence (round reports, serial logs, receipts, captures), NOT source: no
build script reads this directory. Do not delete; do not import from it.

Per-directory index (counts + sizes measured with `find … | wc -l` and
`du -sh`; "proves" from each directory's own headers):

| Directory | Files | Size | What it proves |
|---|---|---|---|
| `demo-beats/` | 6 | 36K | demo-beat serial transcripts (`META OS 0.1 (K6)` era) |
| `face-medicus/`, `face-medicus-wave2/` | 4+4 | 24K+24K | Medicus sim receipts (`receipt_id=sim-…`) |
| `oc1b-chain/` | 1 | 4K | live-baseline chain JSON |
| `oc1b-imperium/` | 7 | 36K | dispatch fence refusals (e.g. emergency.example.gov refused) |
| `oc1b-model-proofs/` | 13 | 192K | model-client error contract (`EndpointUnresolvedError`) |
| `oc1b-musica/` | 2 | 8K | Musica keeper overnight run notes |
| `OC2B-cams/` | 18 | 196K | camera round-robin / staleness / JPEG checks (OC2B-438…) |
| `OC2B-images/` | 3 | 656K | image magic-byte checks (OC2B-413/415) |
| `OC2B-patrol-live/` | 3 | 20K | live patrol dry run — PASS (OC2B-419/420) |
| `OC2B-sam-patrol/` | 11 | 428K | patrol wiring check (OC2B-406) |
| `OC2B-wonder-review/` | 4 | 16K | Wonder vs deterministic combine() (OC2B-407–410) |
| `OC2P-kf01-corrected/` | 7 | 152K | OC2P boot log + corrected artifacts |
| `oc3b-desktop/` | 12 | 48K | desktop drop-in files (e.g. galculator/pavucontrol .desktop) |
| `oc3b-dropins/` | 10 | 40K | OC1 copy manifest (sha-pinned) |
| `oc3b-help/` | 2 | 12K | help/about page fixtures |
| `R5-imperium/`, `R6-imperium-ignis/` | 4+4 | 28K+28K | Imperium sim receipts |
| `wave3-imperium-gaps/` | 4 | 16K | cleared drill/incident records |
| `wave3-model-proofs/` | 12 | 152K | model proof receipts (`receipt_id=sim-…`) |

Largest top-level files (where the megabytes are): `oc1b-hortus-run.jsonl`
3.2M, `K3-doublefault.txt` 3.2M, `K4-guard.txt` 492K, `OC1B-readme-node*.txt`
~360K each, `OC1B-closeout-node.txt` 360K, `K3-fault.txt` 180K.

Regeneration: most files are single-run outputs (re-running the round
recreates its own directory). Nothing in the build reads them; a stale log
cannot break a build, it can only mislead a reader — check the embedded
timestamps before quoting one.
