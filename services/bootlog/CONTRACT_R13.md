# Contract note — R13-004, bootlog error envelope

Status: **AUDITED — 1 gap filed**.
Facet: what a failed boot record reports to its caller.

## Evidence

Command:

```sh
grep -nE 'fn record|fn stage|return false|return n|sys_write_serial|LEVEL_ERROR' services/bootlog/*.goose
```

Output:

```text
bootlog.goose:44:let LEVEL_ERROR = 3;
bootlog.goose:59:fn record(buf: u8[>..]&, cap: i64, level: i64, msg: const u8[:]) -> bool {
bootlog.goose:62:    if need > room_left(buf, cap) { return false; }
bootlog.goose:70:    return n >= 0;
bootlog.goose:79:fn stage(level: i64, msg: const u8[:]) -> bool {
```

## Corrected contract

The error envelope is a single boolean, not a code and not a structure. `record()` returns
`false` for two different failures: the formatted record does not fit the caller's cap, or
`sys_write_serial` returns a negative value. `stage()` propagates that boolean. The caller cannot
tell "too long" from "serial write failed" without reconstructing the inputs, and no error code is
written on the failed path. The buffer is empty after a cap refusal because the width check runs
before formatting.

## Mismatches

- **R13-004-G1** — there is no error envelope; two independent failure causes collapse to
  `false`. See `GAPS_R13.md`.
