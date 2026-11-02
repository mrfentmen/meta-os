# Gap records — R13-021 mcp-host

## R13-021-G1 — no exit-code table

- **Claim:** `mcp-host` documents its exit codes.
- **Reality:** `main` has no explicit return and no exit call. EOF breaks the loop and the
  function ends, which is exit 0 by convention. All four request failures are JSON replies and
  leave the process alive.
- **Evidence:** `services/mcp-host/host.goose:23-61`.
- **Impact:** a supervisor cannot distinguish “finished cleanly” from “crashed before answering”
  by status alone; it must inspect stdout. There is no non-zero code to document.
- **Owner:** mcp-host process contract.

## R13-021-G2 — no host driver or assertions

- **Claim:** the four failure replies are tested.
- **Reality:** the file is entry-only (`fn main`), so `run_native.sh` cannot import it. There is no
  `entry.goose`, no host driver, and no test reference to `host.goose` outside the call-matrix
  exclusion list.
- **Evidence:** `services/mcp-host/README.md` “Not verified”; `grep -RIn 'host.goose'
  services/tests os-build/layer1` returns only `callmatrix_audit.py` program lists.
- **Impact:** `parse`, `no tool`, `no text`, `unknown tool` and the zero exit are all unasserted.
  The Lobster subprocess test covers the caller, not this program.
- **Owner:** mcp-host host driver; Lobster integration.
