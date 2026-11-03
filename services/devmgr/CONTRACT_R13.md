# Contract note — R13-010, devmgr retry policy

Status: **AUDITED — 1 gap filed**.
Facet: how the device manager retries failed operations.

## Evidence

Command:

```sh
find services/devmgr -maxdepth 1 -type f -print
grep -nE '.' services/devmgr/*.goose
```

Output:

```text
services/devmgr/README.md
grep: services/devmgr/*.goose: No such file or directory
```

The README says: "There is no .goose file in this directory and nothing imports devmgr. The device
table was implemented as services/devices/devices.goose."

## Corrected contract

There is no devmgr and no retry policy. `devmgr` is a retired name pointing at `devices`; the
device table has state transitions but no retry loop. Any retry contract here would be invented.

## Mismatches

- **R13-010-G1** — the task's input does not exist: no source, no retry policy. See
  `GAPS_R13.md`.
