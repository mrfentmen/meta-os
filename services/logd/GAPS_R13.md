# Gap records — R13-019 logd

## R13-019-G1 — no file target, only serial

- **Claim:** `logd` persists logs to files and therefore has a file-writes list.
- **Reality:** the only output syscall in `logd.goose`/`entry.goose` is
  `sys_write_serial` at `logd.goose:159`. The retention ring is static memory
  (`160 bytes × 64 slots`); there is no `open`, `write_file`, `storage_write` or path.
- **Evidence:** the write-target grep in `CONTRACT_R13.md`.
- **Impact:** logs do not survive a process restart, and a host that expects `/var/log`-style
  files gets nothing. The README says “Storage” without saying “serial only”.
- **Owner:** logd persistence contract.

## R13-019-G2 — rotation is implemented but not wired

- **Claim:** `logd` rotates its log.
- **Reality:** `rotate.goose` defines a full `RotStore` API, but `grep -n 'rot_'` in
  `logd.goose` and `entry.goose` returns no call sites. No flush path consults a segment, no
  `rot_append` is reached.
- **Evidence:** `services/logd/rotate.goose:55-205`; `services/logd/logd.goose` and
  `services/logd/entry.goose` (no `rot_`).
- **Impact:** the rotation tests exercise a module the sink never calls. Rotation cannot happen
  in a running logd.
- **Owner:** logd entry loop; rotation integration.
