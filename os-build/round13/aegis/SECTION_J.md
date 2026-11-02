# Section J — OPSEC checks and ledger discipline (R13-226..250)

Run: `python3 os-build/layer1/opsec_checks.py`. Records:
`os-build/round13/aegis/OPSEC_CHECKS.json`, `os-build/round13/aegis/opsec_checks.txt`.

**25 / 25 addressed: 20 decided by a command, 3 not inspectable by any command, 2 not
applicable because the artifact does not exist. 4 failures, 6 finding-shaped observations.**

## Findings, sized

| # | finding | size | what makes it that size |
|---|---|---|---|
| J-1 | **1,422 of 1,896 commits are authored from a consumer mail domain** | **alarm** — medium | a personal address is exposed in public commit metadata on three quarters of the history. Not auto-fixed: rewriting history is destructive and a scanner must not do it |
| J-2 | **52 local filesystem paths in 4 committed log files** | quiet note — low | paths under a user home appear in `os-build/logs/*.txt`; the account name is exposed 52 times |
| J-3 | **branch `buffy/pax-12h-plan` names an internal plan** | quiet note — low | the branch name states a 12-hour internal plan exists; the name is public on the remote |
| J-4 | **5 email-shaped and 4 path-shaped strings in 2 test fixture files** | quiet note — low | fixtures carry real-looking data; harmless if fabricated, a leak if copied from a real run |
| J-5 | **findings ledger has no dedupe key** | quiet note — low | `aegis/findings.mjs` exposes `appendFinding`/`readFindings`/`summarize` and no fingerprint, so a re-sweep appends a second copy of every finding |
| J-6 | **findings ledger has no closure field** | quiet note — low | nothing in the entry shape can record that a finding was closed, so the ledger only grows and cannot say what is outstanding |

None of the six was fixed. J-1 and J-3 are not mechanical; J-5 and J-6 are code changes to a
security surface, and the rule is that those go to a human. J-2 and J-4 would be mechanical,
but deleting lines from committed logs rewrites history, which is the same destructive class
as J-1.

## All 25 rows

| task | check | status | detail |
|---|---|---|---|
| R13-226 | commit author metadata | **FAIL** | 1,896 commits, 7 identities, 1,422 from a consumer mail domain |
| R13-227 | file paths in screenshots | NOT_INSPECTABLE | 182 image files; pixels cannot be decided by a command |
| R13-228 | usernames in demo recordings | NOT_INSPECTABLE | 49 recordings |
| R13-229 | local paths in committed logs | **CHECKED → J-2** | 52 matches in 4 of 52 log files |
| R13-230 | timestamps that leak routine | INFO | commit-hour distribution recorded, no judgement attached |
| R13-231 | branch names that leak plans | **FAIL → J-3** | 2 of 127 branch refs flagged |
| R13-232 | status file wording | PASS | 0 `PROVEN` claims |
| R13-233 | README wording on unfinished features | INFO | 0 "not built"/"uncompiled" markers — recorded as a worry, not a pass |
| R13-234 | screenshot corners | NOT_INSPECTABLE | 182 image files |
| R13-235 | demo script wording | CHECKED | 0 home paths, 0 emails across 6 demo docs |
| R13-236 | receipt files in the repo | PASS | 14 receipt-named files, **0 purchase-shaped** (they are drill/hosted proof receipts) |
| R13-237 | test fixtures with real-looking data | **CHECKED → J-4** | 5 emails / 4 paths in 2 of 408 files |
| R13-238 | bus message wording | CHECKED | 2 email-shaped matches in the public viewer |
| R13-239 | site text on the live page | CHECKED | 0 home paths, 0 emails |
| R13-240 | store listing wording | CHECKED | 0 home paths |
| R13-241 | goal file wording | NOT_APPLICABLE | no goal file in the tree |
| R13-242 | skill file wording | NOT_APPLICABLE | `.agents/skills` is outside this repository |
| R13-243 | connector doc wording | CHECKED | 0 home paths, 0 emails across 16 docs |
| R13-244 | error messages printing local paths | CHECKED | 0 in 193 service and agent sources |
| R13-245 | ledger entries that print values | PASS | 7 entries, 0 with a value shape |
| R13-246 | alarm wording (small vs big) | PASS | QUIET/ALARM present; BIG = medium, high, critical |
| R13-247 | finding severity sizing | INFO | 7 entries: 3 medium, 3 low, 1 info |
| R13-248 | finding dedupe on re-sweep | **FAIL → J-5** | no fingerprint in `findings.mjs` |
| R13-249 | finding closure records | **FAIL → J-6** | no closure field |
| R13-250 | ledger append-only check | PASS | 7 lines added, **0 removed** across all history |

## Two checks corrected during the run, and why that is not scoring points

The first run reported `commit author metadata` as a failure for having 7 identities and
`receipt files` as a failure for having 14 receipts. Both were wrong for the same reason: the
check counted a shape instead of the risk. Six agents mean seven identities, and this tree's
"receipt" means a drill proof. The corrected checks count consumer mail domains (1422 → still a
failure, and a bigger one) and purchase-shaped artifacts (0 → pass). The failed rows did not
disappear; one got worse.

## What this section cannot claim

- That the 182 images and 49 recordings are clean. They are uninspected, and the record says
  `NOT_INSPECTABLE` rather than a zero that reads like a pass.
- That J-1 can be fixed without a decision. Filter-branching public history breaks every fork
  and every existing clone; that is the boss's call, not a scanner's.
- That re-sweep dedupe is broken in practice. The logic is absent, so a second sweep **would**
  duplicate; the count of duplicates was not measured because it needs two live runs.
