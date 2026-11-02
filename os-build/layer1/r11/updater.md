# updater — Round 11 record

Source: `services/updater/{updater,delta,signature}.goose` · Test: `services/tests/t138_updater_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `MF_MAX_FILES` | `8` | `updater.goose:43` | driven here and by `tests/t79_limit_drivers` | a ninth `file =` line returns `E_BAD_MANIFEST`; the first eight parse |
| `MF_PATH_MAX` | `32` | `updater.goose:44` | driven here and t79 | a 32-character path is refused (`>=` is the bound) |
| `MF_DIGEST_HEX` | `64` | `updater.goose:45` | driven here | a 63-character digest is refused |
| `MF_ORIGIN_MAX` | `64` | `updater.goose:47` | driven here and by `tests/t80_limit_drivers2` | an empty origin is refused; t80 drives the length bound |
| `MF_VERSION_MAX` | `16` | `updater.goose:48` | driven here and t79 | a 16-character version is refused |
| `UPD_CONTENT_MAX` | `4096` | `updater.goose:324` | driven by `tests/t103_limits_rest`, not here | the content table's per-slot cap; `t138` uses the size mismatch path instead |
| `UPD_REC_KEEP` | `4` | `updater.goose:468` | driven here | five pushed records leave `upd_record_count() == 4` |
| `DL_OPS_MAX` | `4` | `delta.goose:43` | not a limit | the ops array is `[..4]`; the type is the enforcement |

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| unknown key | `E_BAD_MANIFEST` | `t138`: `license = mit` |
| line without `=` | `E_BAD_MANIFEST` | `t138` |
| duplicate path | `E_BAD_MANIFEST` | `t138`: two entries for `a` |
| path containing `..` | `E_BAD_MANIFEST` | `t138`: `../etc/passwd` |
| path at 32 chars | `E_BAD_MANIFEST` | `t138` |
| digest not 64 hex | `E_BAD_MANIFEST` | `t138`: 63 chars |
| size not decimal | `E_BAD_MANIFEST` | `t138`: `12x` |
| missing slot / version / file | `E_BAD_MANIFEST` | `t138`, three documents |
| version at 16 chars | `E_BAD_MANIFEST` | `t138` |
| empty origin | `E_BAD_MANIFEST` | `t138` |
| ninth file | `E_BAD_MANIFEST` | `t138` |
| zero-byte file at plan time | `E_BAD_MANIFEST` | `t138`: parses, then `upd_plan` refuses |
| plan targeting the active slot | `E_STATE` | `t138`: `upd_plan(m, SLOT_B)` |
| active slot neither A nor B | `E_INVAL` | `t138`: `upd_plan(m, 7)` |
| verify index past the count | `E_INVAL` | `t138` |
| wrong size before hashing | `E_VERIFY` | `t138`: 3 bytes for an 18432-byte file |
| record without magic | `E_CORRUPT` | `t138`: first byte zeroed |
| record with one changed header byte | `E_CORRUPT` | `t138`: CRC catches the torn write |
| record shorter than 512 | `E_CORRUPT` | `t138`: a 100-byte block |

**Not driven, and why:** `upd_record_decode`'s `E_UNSUPPORTED` format branch needs the CRC
recomputed after the format word is changed; `t138` does not import `common.hash` and does not
recompute it, so a format bump currently reads as `E_CORRUPT`. Also untested: a signature that
fails, because `sig_verify_manifest` returns `E_UNSUPPORTED` unconditionally (`SIG_DESIGNED`).

## 3. Restart — NAMED GAP

`rec_history`, `rec_count` and `rec_next_seq` are process memory. The 512-byte record is the
designed authority, but nothing in this tree writes it to storage — the encode/decode pair exists
and the storage binding does not — so a restart loses the history and `upd_record_safe_slot()`
returns `SLOT_NONE`. The loss is named, not softened: until the record is written, an A/B update
cannot survive the crash it exists for.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `socket` | fetch the manifest/content | declared on `SVC_UPDATER`, dormant |
| out | `storage` | read/write the inactive slot and the record block | declared, dormant |
| out | `audit` | record applied/rolled back | declared, dormant |
| out | `log`, `time` | records and stamps | declared, dormant |
| in | `updater_client` | check/apply | declared on `SVC_UPDATER_CLIENT`'s row, dormant |

**FINDING:** the apply path verifies a manifest's digest and *not* its signature:
`sig_verify_manifest` returns `E_UNSUPPORTED` and `sig_status_name()` honestly says `DESIGNED`.
`SVC_UPDATER`'s row is therefore a permission set for a service whose central security property
is absent; it is stated in the README and in `signature.goose`, and it is a room-1 finding because
it is a contract-level hole, not a bug in a function.

## 5. Load — NAMED GAP

The load loop parses 100 manifests, half of them one bad line, and requires 50 accepted and 50
refused. That is ten times a normal manifest batch; it approaches no quota (there is none) and
exercises allocation-free parsing at the table's edge.

RUNS pass=47 fail=0 · `LOAD updater ops=100 ok=50 refused=50`

## 6. README truth pass — PROVEN

- The status line said **WRITTEN (not COMPILED — no Goose toolchain on this Mac)**; the host
  corpus has run `tests/t58_updater` and `t79`/`t80`/`t103` drive its limits. Changed to `RUNS`,
  with `t58` and `t138` named.
- The task table marked all three rows WRITTEN; they are `RUNS` (the logic runs on the host, and
  nothing boots it on the kernel). Rewritten.
- The closing line "Not compiled, not run." contradicted the run rows. Replaced with what is
  true: run on the host corpus, not booted, and no signature verifier.
- The refusal table was already accurate; it gained the plan-time zero-byte and record-header
  refusals this round proved.
