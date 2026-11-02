# `sockets` — retired name, no code

**Status: README ONLY. There is no module here.** The socket contract was implemented as
`services/socket/socket.goose` (singular); this directory is the old plural name and holds
nothing but this file.

- **No source, no test, no entry point.** `os-build/layer1/r11/sockets.md` records the
  directory's real status and why there is no `LOAD` line.
- **The implementation:** `services/socket/` — status RUNS, driven by `t77_gaps` and
  `t132_socket_r11`. Its limits, refusals and generation wrap are in `r11/socket.md`.
- **One action left, for the manifest owner:** `services/MANIFEST.md` row 16 still lists
  `sockets` as NOT BUILT and has no row for `socket`. Deleting the row is a manifest edit,
  not a service edit, so it is named here and in the record rather than done by a worker.

Nothing in this directory may be described as a service, and no status word above WRITTEN
applies to it: WRITTEN would imply source.
