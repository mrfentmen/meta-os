# Contract note — R13-005, build log line format

Status: **AUDITED — 1 gap filed**.
Facet: the log-line format emitted by the build service.

## Evidence

Command:

```sh
find services/build -maxdepth 1 -type f -print
grep -nE '.' services/build/*.goose
```

Output:

```text
services/build/.gitignore
services/build/README.md
grep: services/build/*.goose: No such file or directory
```

The README states: "This directory holds build artifacts ... It is **not** a Layer 4 service, it
has no *.goose source, no entry point, no matrix id and no test."

## Corrected contract

There is no build service and no build log-line format. `services/build/` is generated output
only; the compile recipe is documented in `services/BUILD.md`, and the corpus runner writes to
`os-build/layer1/host/build`. Any format claimed for this directory would be invented.

## Mismatches

- **R13-005-G1** — the task's input does not exist: no build service, source, or log format. See
  `GAPS_R13.md`.
