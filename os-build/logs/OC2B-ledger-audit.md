# OC2B ledger audit (§11, OC2B-270/271)

Lab ledger file: labs/cycles/ledger.jsonl (filed via
os/worlds/science-lab/ledger.py append_record; chain verified with
ledger.verify_chain).

## Audit table (5 entries, levels match records)

| cycle | ledger entry id (short) | level (ledger) | level (record) | verdict | id quoted in record |
| cycle-001 | feb64da4… | 3 | 3 | MATCH | yes |
| cycle-002 | d51e60f4… | 3 | 3 | MATCH | yes |
| cycle-003 | 5b681bd0… | 3 | 3 | MATCH | yes |
| cycle-004 | 96ceecf8… | 3 | 3 | MATCH | yes |
| cycle-005 | 1bff1209… | 2 | 2 | DIFFER | yes |

Chain check: True, ok: 5 entries verified (hash linkage intact,
ordered cycle-001 … cycle-005, recorded_at non-decreasing).
Full ids are quoted in each labs/cycles/<cycle>/record.md.

## Ladder audit (no export or summary states a level above an earned one)

- grep -rni for level/Level 4, 5, 6 across labs/cycles/cycle-00*/
  and labs/cycles/repository/: NO MATCHES.
- Repository export levels: claims 3/3/3/3/2, cycles 3/3/3/3/2 —
  identical to earned levels; no pointer claims higher.
- Earned maxima are 3 (MATCH + bit-for-bit reproduction, automated
  ceiling) and 2 (cycle-005 DIFFER, mismatch cap). Nothing in any
  summary, score, export, or claim exceeds its cycle's earned level.
