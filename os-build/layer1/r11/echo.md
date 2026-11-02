# echo — Round 11 record

Source: `services/echo/echo.goose` · Test: none (not importable) · Status: WRITTEN

## 1. Limits — NOT IMPORTABLE

`echo.goose` declares `fn main()` and imports `os` for stdio (`write_stdout`, `read_line`,
`flush_stdout`). It is an entry program, not a library: a test root that imported it would link a
second `main`, and the corpus typechecker builds one program per test with its own `main`. So no
`t<NNN>_echo_r11.goose` exists, and inventing an import to make one appear would test a shim
instead of the service.

The file declares no numeric limit. Its only bound is the line builder, which grows as needed and
is cleared per line; there is no cap to drive. `services/MANIFEST.md` does not list echo among the
24 services, so this directory is outside the counted corpus — that is the finding in section 4,
not a limit.

## 2. Refusals — NAMED GAP

The program has one refusal path: `read_line` failing ends the loop and the process exits 0. That
is an end-of-input, not a policy refusal, and it cannot be driven from this worker (no terminal,
no host shim entry for a standalone stdio program). Nothing else is refused: any line is echoed,
including an empty one.

## 3. Restart — NOT APPLICABLE

Echo holds one line buffer and no other state. A restart loses at most a partially read line,
which is the same loss as the input stream ending. There is no supervisor entry for it, so no
restart was run and none is claimed.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | none | `import os` only (stdio carrier) | — |
| in | any | a line on stdin, or a dev-carrier connection | no: echo has no `SVC_*` id in `callmatrix.goose` |

**FINDING: echo is not in the call matrix and not in `services/MANIFEST.md`.** It is a real
program (OS-159, the dev-carrier echo) with no id, no manifest row, and no caller declared. That
is acceptable for a host-side dev tool and is a problem the moment anything treats it as a
service: it cannot be permission-checked, and the boot order cannot name it. Recorded for room 1.

## 5. Load — NOT APPLICABLE

There is no callable surface to load: the program reads until EOF and exits. A load number here
would measure the host terminal, not the service.

## 6. README truth pass — PROVEN

- There was no `README.md` at all. Created one that states what the file is, that it is
  entry-only and not importable, that it is outside the 24-service manifest, and how to run it
  by hand (`goose ... echo.goose` against a terminal). No claim of a test or a boot.
