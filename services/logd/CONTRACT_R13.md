# Contract note — R13-019, logd file writes list

Status: **AUDITED — 2 gaps filed**.
Facet: every file or block target `logd` writes, and whether rotation is connected to them.

## Evidence

Commands:

```sh
grep -nE 'sys_[a-z_]+|storage_|write_file|open|path' services/logd/*.goose
grep -nE '^fn rot_|^struct |^let ' services/logd/rotate.goose
grep -n 'rot_' services/logd/logd.goose services/logd/entry.goose
```

Relevant output:

```text
logd.goose:159  let n = sys_write_serial(rec[off..rec.len]);
logd.goose:164  sys_yield();
entry.goose:31  sys_yield();
```

`logd.goose` and `entry.goose` contain no file, path, storage or rotation call. `rotate.goose`
defines `rot_new`, `rot_append`, `rot_current`, `rot_seal`, `rot_prune`, `rot_shift_out`,
`rot_segment_name`, `rot_export_name` and `rot_stats`, but nothing in `logd.goose` invokes them.

## Corrected contract

`logd` writes **one target**: the serial port, through `sys_write_serial`. Its retention ring is
160-byte slots × 64 in static memory, not a file. There is no `open`, `write_file`, `storage_write`
or path string in the service. Flush writes queued records to serial; a short write is retried
with `sys_yield` and a 1,000-iteration guard.

`rotate.goose` is a separate, unwired segment model. It builds segment names and counts bytes, but
it has no file writer and no caller in `logd`.

## Mismatches

- **R13-019-G1** — there is no file-writes list because there are no file writes; the README's
  “Storage” section can be read as disk storage.
- **R13-019-G2** — the rotation module is dead code from `logd`'s perspective: no call site. See
  `services/logd/GAPS_R13.md`.
