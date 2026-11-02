# Contract note — R13-015, echo metrics line

Status: **AUDITED — 2 gaps filed**.
Facet: the metrics line `echo` emits, its fields and where it is written.

## Evidence

Command:

```sh
nl -ba services/echo/echo.goose
```

Complete source body:

```text
8   fn main() {
9       var line: u8[>..] = [];
10      loop {
11          write_stdout("> ");
12          flush_stdout();
13          line.clear();
14          guard read_line(line) else { break; }
17          write_stdout("echo: ");
18          write_stdout(line);
19          write_stdout("\n");
20          flush_stdout();
21      }
22  }
```

There is no counter, no `metrics`, no `stats`, and no `svc_entry`/`service_main`. The README
already says “Status: WRITTEN, entry only” and “No permission check”.

## Corrected contract

`echo` has no metrics line. It emits a prompt `"> "`, then for each input line emits
`"echo: " + line + "\n"`. The only structured observation is the process's line stream; there
are no fields, no counts, no interval and no metrics sink. It is a standalone `main` importing
`os`, not a service library, and it is absent from `services/MANIFEST.md` and the call matrix.

## Mismatches

- **R13-015-G1** — the requested metrics line does not exist in any form.
- **R13-015-G2** — there is no service entry or service id to attach metrics to; the README
  records this as intentional. See `services/echo/GAPS_R13.md`.
