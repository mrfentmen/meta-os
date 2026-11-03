# OC2B repository export (§11, OC2B-268/269)

Exported all five OC2B cycle packs through the lab's own repository
module (os/worlds/science-lab/repository.py), base labs/cycles/repository
(a cycles-local base, so the shared records/repository tree is untouched).

## Export paths

- labs/cycles/repository/cycles.jsonl — 5 cycle pointers
  (OC2B-cycle-001 … OC2B-cycle-005).
- labs/cycles/repository/claims.jsonl — 5 claim pointers
  (OC2B-cycle-001-claim … OC2B-cycle-005-claim).

Filed with repository.file_cycle / repository.file_claim; each cycle
pointer carries department, level, verdict, ledger entry hash, pack
path, and pack file count; each claim carries statement, level,
verification status (reproduced for MATCH, mismatch for DIFFER).

## Hash-check table (each exported pack vs its recorded pack hash)

Recomputed after the export; every file in each pack re-hashed and
compared with labs/cycles/<pack>/pack.sha256.

| pack | pack.sha256 lines | recomputed now | match |
| labs/cycles/cycle-001 | 16 | 16 | YES |
| labs/cycles/cycle-002 | 16 | 16 | YES |
| labs/cycles/cycle-003 | 34 | 34 | YES |
| labs/cycles/cycle-004 | 16 | 16 | YES |
| labs/cycles/cycle-005 | 18 | 18 | YES |

Result: all five exported packs still hash to their recorded pack
hashes. No pack file changed during the export.
