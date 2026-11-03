# Gap records — R13-025 registry

## R13-025-G1 — no upgrade note

- **Claim:** `registry` has an upgrade note describing version changes and migration.
- **Reality:** `services/registry/` contains only `README.md`. The README says “NOT A SERVICE”,
  names the supervisor functions where the table actually lives, and lists no versions, no
  schema and no migration steps.
- **Evidence:** `ls -la services/registry`; `services/registry/README.md`.
- **Impact:** there is nothing to upgrade today. When the supervisor's handle encoding or
  `bootorder` registration changes, operators have no written procedure; a note must be created
  with the first real registry version.
- **Owner:** registry/supervisor owner; release notes.

## R13-025-G2 — restart loss is documented, upgrade migration is not

- **Claim:** the existing registry record covers lifecycle changes.
- **Reality:** `os-build/layer1/r11/registry.md` documents that a supervisor restart loses every
  name and handle and that boot re-registration is specified but unproven. It says nothing about
  upgrading a running system or changing the handle format.
- **Evidence:** `os-build/layer1/r11/registry.md:43-48`; `services/registry/README.md`
  “What is not proven”.
- **Impact:** the one lifecycle document answers restart, not upgrade. A future format change has
  no compatibility statement to test against.
- **Owner:** supervisor lifecycle; release notes.
