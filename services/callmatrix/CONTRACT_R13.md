# Contract note — R13-006, callmatrix state file shape

Status: **AUDITED — 1 gap filed**.
Facet: what state file the permission matrix reads or writes.

## Evidence

Command:

```sh
grep -nE 'fn cm_init|fn cm_set|file|path|save|load|persist' services/callmatrix/*.goose
```

Output includes:

```text
callmatrix.goose:97:fn cm_init() {
callmatrix.goose:104:    cm_set(SVC_BOOTLOG, ...);
callmatrix.goose:175:fn cm_set(caller: i64, allow: i64) {
```

No file, path, save, load, or persist symbol is declared.

## Corrected contract

There is no state file. The matrix is 31 static `i64` rows in process memory, filled by
`cm_init()` through `cm_set()`. Every process start rebuilds it from source. There is no export
format, no reload path, and no file permission to audit. A caller that skips `cm_init()` gets the
fail-closed zero table: every row is denied.

## Mismatches

- **R13-006-G1** — the requested state-file shape does not exist; the matrix is process memory
  rebuilt on every start. See `GAPS_R13.md`.
