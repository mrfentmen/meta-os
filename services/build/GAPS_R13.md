# Gap records — R13-005 build

## R13-005-G1 — no build service exists

- **Claim:** `services/build` emits build log lines in a defined format.
- **Reality:** the directory contains only `.gitignore` and `README.md`. There is no `.goose`
  source, no entry point, no `SVC_BUILD` id, and no log format.
- **Evidence:** `find services/build -maxdepth 1 -type f` and the failed `*.goose` glob in
  `CONTRACT_R13.md`; the README says it is generated output, not a service.
- **Impact:** the task's input does not exist. The correct action is this gap record, not a fabricated
  format or a test over generated files.
- **Owner:** manifest owner; Round 11 already recorded the same mismatch in
  `os-build/layer1/r11/build.md`.
