# sockets — Round 11 record

Source: none — `services/sockets/` contains only `README.md` · Test: none · Status: README ONLY

## 1. Limits — NOT APPLICABLE

There is no module here, so there is nothing to import and no limit to cross. This directory is
the old plural name for the socket contract; the implementation is `services/socket/socket.goose`
(singular) and its Round 11 record is `r11/socket.md`.

Not importable: no `.goose` file exists in the directory.

## 2. Refusals — NOT APPLICABLE

No code, so no refusal path exists here.

## 3. Restart — NOT APPLICABLE

No process, no state, nothing to restart.

## 4. Contract — NOT APPLICABLE, with a finding

- **FINDING: the manifest still carries this name.** `services/MANIFEST.md` row 16 is `sockets`,
  status NOT BUILT, and there is no row for `socket`. The work order named this directory; the
  work landed one directory over. Removing the row is the manifest owner's change, not a service
  worker's, so it is recorded here instead of edited.
- The last edit to this README already said "NOT A SEPARATE SERVICE ... should be removed by
  whoever owns the manifest". It was accurate and nobody acted on it. This round makes the
  directory's own status truthful rather than repeating a wish.

## 5. Load — NOT APPLICABLE

No test, so no run and no `LOAD` line. Fabricating one would be the failure this round exists to
remove.

## 6. README truth pass — PROVEN

The README said `WRITTEN (not COMPILED). Source exists; nothing in it has been compiled or run.`
No source exists. It now says so in the first line: retired name, no code, real implementation in
`services/socket/`, and the one action left (delete the manifest row) with its owner named.
