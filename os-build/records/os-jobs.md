# Record — `crates/os-jobs`, from the code

Scope: the whole crate (`crates/os-jobs/src/lib.rs`, 4,348 lines on
2026-11-02). The Python original is `os/jobs.py`; this record describes
the Rust port as it is written, not the Python as it was planned.
Every claim cites a line range. Where the port deliberately differs
from Python, that is in **Findings** or in `os-jobs-gaps.md`.

Status word: **PORTED, tested in-crate**. The crate has 102 `#[test]`
cases in its own `mod tests` (lines 2604-4347) and compiles with no
dependencies (`Cargo.toml` has none).

## What it is

A queues-as-a-service command layer for the bus. One `JobQueue<S>`
(942-949) owns:

- a `JobStore` (state backend seam, 151-176),
- a `Clock` (102-140),
- a namespace, a nick, and a host identity,
- a list of wire announcements it *would* send (958).

Every command returns `CmdOutcome { code, out, err }` (847-864), the
same (exit code, stdout, stderr) triple the Python CLI prints. There
is no argv parser and no HTTP client in the crate; those are named
gaps, not hidden work.

## State it writes

Keys are built by the pure helpers at 401-427 and namespaced by the
`ns` constructor argument:

| Key | Shape | Written by | Meaning |
|---|---|---|---|
| `{ns}seq` | string integer | `post` (1414-1421) | job-id counter |
| `{ns}:{jid}` | hash | `post` (1422-1460), `claim` (1833-1844), `done`/`blocked`/`cancel`/`requeue` | the job record |
| `{ns}:{jid}:spec` | string | `post` (1436) | the full spec text |
| `{ns}:{jid}:claim` | string with TTL | `claim` (1816-1823), `heartbeat`/`progress` (1252-1283) | the claim mutex |
| `{ns}index` | zset (score = post time) | `post` (1441-1445) | the job index |
| `muse-bus:nickclaim:{quoted nick}` | string with TTL | `nick_claim` (1073-1101) | nick reservation |

The job hash carries: `title`, `room`, `branch`, `base`, `accept`,
`status`, `lease`, `created_by`, `created_host`, `created_at`,
`files`, `deps`, `attempts`, `artifacts`, `req`, `max_attempts`
(1423-1435); after a claim: `status=claimed`, `claim`, `claim_host`,
`claimed_at`, `lease_until`, `lease` (1833-1844); after done/blocked:
status plus `result_commit`/`note`/`done_at` or `note`/`blocked_at`
(1955-1985); after cancel: `cancelled` + `note` + `cancelled_at`
(2071-2079); an optional signature block adds `sig`, `sig_v`,
`sig_kid`, `signed_by`, `nonce`, `expires_at` (1465-1495).

## Commands, in the order the code defines them

| Command | Lines | Exit 0 means | Refusals (exit code) |
|---|---|---|---|
| `post` | 1343-1496 | job hash + spec + index written, `JOB {id}` | empty spec, bad room, lease < 60, malformed artifact (2, before any write); store failure (2); bad secret file / unknown kid / non-positive expiry / signing write failure (2, **after** the job is written) |
| `list` | 1498-1616 | text table, `NO_JOBS`, or one JSON array | index read failure (2) |
| `show` | 1618-1651 | fixed field order + `--- spec ---` | unknown id (2) |
| `attach` | 1653-1697 | refs appended, deduped against stored list | unknown id, malformed ref, write failure (2) |
| `claim` | 1699-1862 | mutex won + claim fields written | unknown id, bad/expired signature (1), malformed expiry (2), not open, lease < 60, mutex write failure, lost race, claim-record failure with rollback (2) |
| `heartbeat` | 1864-1898 | lease renewed | unknown id, not the claimer, lost lease (2) |
| `progress` | 1900-1937 | note + timestamp stored, lease renewed | unknown id, not the claimer, lost lease, note write failure (2) |
| `done` | 1939-1991 | status `done`, commit stored, claim released | unknown id, not the claimer, write failure (2) |
| `blocked` | 1993-2044 | status `blocked`, claim released | unknown id, not the claimer, write failure (2) |
| `cancel` | 2046-2086 | status `cancelled` (open jobs only) | unknown id, not open, write failure (2) |
| `requeue` | 2088-2179 | attempts+1, status open, claim cleared | unknown id, not claimed, lease still active, max attempts reached (marks `failed-final`), attempts write failure, requeue write failure (2) |
| `sweep` | 2181-2251 | requeues expired claims, reports `DEP_DEAD`, else `SWEEP_CLEAN` | index read failure (2); a failed requeue is a warning, not a failure |
| `verify` | 2253-2275 | prints `OK` (exit 0) | prints `BAD`/`UNSIGNED`/`EXPIRED` (exit 1); unknown id, unreadable secret, malformed expiry (2) |

## What it refuses, in one list

Every refusal is a `CmdOutcome` with a non-zero code and a written
message; nothing panics on bad input.

- Bad identity/hash input: `valid_id` rejects empty, non-digit, and
  all-zero ids (934-940); `job_get` then reports `(None, "")` (1035-1057).
- Bad room: a non-empty room that cleans to nothing (375-388).
- Bad artifact: `parse_artifact_ref` rejects a missing prefix, bad job
  id, empty/absolute/`.`/`..`/backslash/NUL name, and `v0` (672-709);
  `validate_artifact_refs` names the first bad ref (722-733).
- Bad keyring: empty file, a line with more than one colon, empty kid
  or secret, whitespace in a kid, multiple secrets without kid lines
  (759-799).
- Bad signature: v1 with no `default` key, v2 with no matching kid,
  any digest mismatch → `BAD`; expired v2 → `EXPIRED` (1189-1245).
- Bad store: every command maps `StoreError` to `RELAY_ERROR: …` with
  exit 2 and does not invent state. `claim` rolls the mutex back when
  the claim-record write fails (1846-1857).

## What it writes down (records, not side effects)

- Announcements are recorded as `(bus key, "nick: text")` tuples
  (1156-1168): `JOB:`, `CLAIM:`, `PROGRESS:`, `DONE:`, `BLOCKED:`,
  `REQUEUE:`, and `REJECTED:` on a refused signature. There is no
  transport: `pushes_to` is how a test reads them (974-981).
- The brief environment surface: `environment_jobs_record` (2318-2355)
  and `environment_lines` (2479-2597) render only claimed jobs with a
  nick and a title; a missing quarter reads "not reported in this
  snapshot", never a guess.
- Signatures: canonical JSON is sorted-key JSON (588-602); v1 covers
  six fields (609-621), v2 adds jid/kid/created_at/expires_at/nonce
  (623-643). HMAC-SHA256 is implemented in-crate (511-530); SHA-256 is
  from scratch (429-509).

## Deliberate limits stated in the crate

The module header (44-70) already names the port's approximations:
no `relay_common` nick-claim cache, no bus send/poll/watch/presence,
no brief composer, u64-only artifact versions, and a non-CSPRNG nonce.
Those are repeated with task-shaped detail in `os-jobs-gaps.md`.

## Findings (B028 — docs vs code)

1. **The crate header was stale and duplicated.** Lines 1-11 and
   12-23 were the same B00 skeleton paragraph twice, and it claimed
   "Skeleton only: no logic yet" while the file contains the port and
   102 tests. Fixed in this lane (the header now states the port
   status); the code is the authority.
2. **`DEFAULT_NS` is defined and never read** (78). Python reads
   `MUSE_RELAY_JOBNS` (`os/jobs.py:82-84`); Rust takes the namespace
   as a constructor argument and reads no environment at all. The
   constant is therefore a public surface with no consumer. Named, not
   removed (removing a public const is a breaking change).
3. **`PRESENCE_TTL` is defined and never read** (87). It documents the
   Python invariant that presence and nick-claim TTL are equal; only
   `NICKCLAIM_TTL` is used (1078, 1093). Kept so the equality is
   visible.
4. **Two Python deviations are deliberate and load-bearing:**
   non-numeric `attempts`/`max_attempts` are treated as 0/unlimited
   (2135-2172) where Python's `int()` raises and `cmd_requeue` would
   traceback (`os/jobs.py:855-861`); and artifact versions are `u64`
   where Python accepts any integer (`os/jobs.py:150-173`). Both are
   recorded in `os-jobs-gaps.md`.
5. **A post can leave an unsigned job behind.** The spec/room/lease/
   artifact checks run before the first write (1349-1364), but the
   secret file, kid, and expiry checks run after the job hash, spec,
   and index are written (1462-1476). A bad key path returns exit 2
   with a job already in the queue. Python has the same order
   (`os/jobs.py:397-492`); the behaviour is pinned by
   `tests/error_paths.rs::post_with_a_missing_secret_file_reports_after_the_job_is_written`.
