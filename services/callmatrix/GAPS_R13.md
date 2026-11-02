# Gap records — R13-006 callmatrix

## R13-006-G1 — no state file

- **Claim:** the permission matrix has a state-file shape.
- **Reality:** the README says "Static data, no file"; the source has no file/path/load/save
  function. `cm_init()` rebuilds 31 rows through `cm_set()`.
- **Evidence:** the grep in `CONTRACT_R13.md`.
- **Impact:** there is nothing to persist or restore; a start that skips `cm_init()` silently
  denies everything (fail-closed). Any external editor expecting a file will find none.
- **Owner:** callmatrix contract; registry startup ordering.
