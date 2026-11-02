# README AUDIT — Bond, wave 2, 2026-11-02

Measured on clean clone `c7aeb16` (node + packs + loop) and working tree
`78862a5` (Python). Commands and logs under `os-build/bond-evidence/logs/`.

## 65-66. Every number in README, checked

| README claim | Line context | Measured here | Verdict |
|---|---|---|---|
| Node badge: 1877 passing | top badges | 2033 tests, 1978 pass, 55 fail | STALE |
| Node table: 1933 run, 1877 pass, 56 fail | Test numbers | 2033 / 1978 / 55 | STALE |
| Rust workspace: 1412 pass | Test numbers | 2108 pass measured on `51e9c80` in wave 1; not re-run after `78862a5` | STALE (last measured) |
| Python job queue: 110 pass | Test numbers | 277 pass | STALE |
| Python Officina: 49 pass | Test numbers | 49 pass | CURRENT |
| Worlds packs: 9 of 9 valid | badge + table | 12 packs, validator exit 0, 12 OK | STALE |
| OS loop harness: 12 of 12 | Test numbers | 11 passed, 1 failed (`green cycle`) | STALE / FAILING |
| Kernel ~5,700 lines | OS section | 5,833 lines across 13 files | STALE (close) |
| Rust OS layer: 18 crates | OS section | 19 crates | STALE |
| Services: 25 over 18 libraries | Services layer | not re-run; no `.go`/`.gos` files under `services/` in this tree | UNVERIFIED |
| 33 programs, 1,253 checks | Services layer | not re-run here | UNVERIFIED |
| OS side ~122,000 lines | OS section | not measured | UNVERIFIED |

## 67. Programs named with no directory or code

- **Meta Faber** — "Working in main" in the systems table. No `faber/`,
  no `os/faber/`, no source file. One document mention only. UNIMPLEMENTED.
- Every other named system has a home: Imperium (`js/`, `server/`),
  Scientia (`os/worlds/science-lab`, `hortus-rung3`), Officina
  (`os/worlds/officina`), Custos (`os/worlds/custos`), Musica
  (`os/worlds/musica`), Aegis (`aegis/`), Nervus (`nervus/`), Hands-Free
  (`handsfree/`), Relay (`relay/`), kernel (`kernel/`).

## 68. Directories that look like programs but are not in README

`lobster/`, `intel/`, `hortus-rung3/` (named indirectly), `mcp-gateway/`,
`oc-proofs/`, `plan/`, `hackathon/`, `batches/`, `labs/`.
Not all are programs; the README map omits them.

## 69. Systems line check

README says "The systems" then lists **seven** rows plus the kernel, not
six. Custos appears as "Built and gate checked … waits on a merge fix",
**not retired**. If the standing rule is that Custos appears only as
retired, the README and the table violate it.

## 71. MODEL_INTEGRATION.md against Section 3 evidence

- Model ids and surfaces: match `server/queue/models.py`.
- Live-call claims (11 calls, $0.0047): no receipt artifact. UNVERIFIED.
- SAM patrol wiring, Wonder review swap, Muse Image concept art: named as
  future/next in the same document; no code. UNIMPLEMENTED.
- Voice seam: honestly marked unresolved. Consistent with `transcribe()`
  raising.

## 72. Boot / run / model-call claims with no log or receipt

| Claim | Where | Why it fails |
|---|---|---|
| 42 matched, 46 unsure, 0 misses | README Imperium numbers | no eval log for this run in the repo; not reproduced here |
| 12 of 12 loop scenarios | README Test numbers | measured 11/12; the "green cycle" scenario fails |
| 33 programs / 1,253 checks | README services layer | transcript files exist but were not re-run; no fresh log |
| 11 model calls, judge smoke $0.0047 | `MODEL_INTEGRATION.md` spend note | no `model_receipts.jsonl` anywhere |
| 61,660 frames | `KERNEL_STATUS.md` K4 | conflicts with `K1-boot.txt` / `SCOREBOARD.md` 127,199 (wave-1 finding, still open) |
| K6 proven | README kernel row vs `KERNEL_STATUS.md` | README says K6 "proven except no Goose process"; status table says PROVEN. Wording conflict. |

## Bottom line

The README's own rule is "if a number cannot be shown, it does not get
printed." Six printed numbers are stale, one is contradicted by a re-run,
one program is claimed working with no code, and Custos is not shown as
retired.
