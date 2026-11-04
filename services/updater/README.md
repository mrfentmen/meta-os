# updater — manifest, verification, apply plan, rollback record

Status: **COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/updater/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — the host corpus runs `tests/t58_updater`, and `tests/t79_limit_drivers`,
`t80_limit_drivers2`, `t103_limits_rest` and `tests/t138_updater_r11` drive its limits and
refusals. Layer 4, service 18. Nothing boots it on the kernel yet.

| Task | Section | State |
|---|---|---|
| B-L1-34 manifest | `upd_parse_manifest` | RUNS (`t58`, `t138`) |
| B-L1-35 verify + apply plan | `upd_verify_file`, `upd_plan` | RUNS (`t58`, `t138`) |
| B-L1-36 rollback record | `upd_record_*` | RUNS (`t58`, `t138`); not yet written to storage |

## Why a line format and not JSON

B-L1-120 builds a JSON subset and B-L1-122 the delta manifests. An updater that needed
a parser nobody has written yet could not be reviewed, so this reads a format a person
can read, diff and sign:

```
# meta-os update manifest v1
version = 0.2.0
origin  = https://updates.example.invalid/meta-os
slot    = b
file    = bin/console.c  9f86d081... 18432
```

The size is not redundant with the hash: a truncated download has a **different hash and
a different size**, and the size mismatch is the cheap check that says "the transfer
stopped" instead of "the bytes changed".

## What parsing refuses

| Refusal | Why |
|---|---|
| **unknown key** | silently ignoring a field is how v2 adds a signature and v1 clients install unsigned updates — they "ignore" the protection |
| **duplicate path** | two entries for one file leave the installer to pick, so whoever can add a line chooses the winner |
| **more files than the table** | refused, not truncated: a truncated manifest is a half-updated system reporting success |
| **digest not exactly 64 hex chars** | short digests are how verification degrades into a prefix compare |
| **path containing `..`** | the manifest names files inside the update, not places on the disk |
| **no version / no slot / no files** | an empty manifest is not an update |

Any single bad line rejects the whole document: an installer that proceeds with the
lines it understood installs half an update and reports success.

Digests are parsed from hex into **bytes** at parse time. Comparing hex text is how the
first implementation of every updater gets prefixes wrong.

Run on the host corpus; not booted on the kernel. The rollback record encodes and decodes but
nothing writes it to a slot yet, so the A/B history is process memory (named in
`os-build/layer1/r11/updater.md` §3). No signature verifier exists: `sig_verify_manifest`
returns `E_UNSUPPORTED` and `sig_status_name()` says `DESIGNED`.
