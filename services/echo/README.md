# `echo` — the dev-carrier echo program

**Status: WRITTEN, entry only.** `echo.goose` is a standalone `main`, not a service library: it
imports `os` for stdio, reads a line, writes `echo: <line>`, and loops until end of input. Nothing
imports it, and it is not in `services/MANIFEST.md` or the call matrix.

## Run it by hand

```
goose echo.goose
```

There is no `svc_entry`, no host driver and no test: the corpus builds one program per test, and a
test that imported this file would link a second `main`. That is why Round 11 records it as
`NOT IMPORTABLE` rather than forcing a driver (`os-build/layer1/r11/echo.md`).

## What it does not prove

- Not booted on the kernel; the dev-carrier contract in `os-build/research/goose-ipc.md` is the
  stdio carrier today and the kernel syscall channel when K6 lands.
- No permission check: the program has no `SVC_*` id, so nothing can ask whether a caller may
  reach it.
