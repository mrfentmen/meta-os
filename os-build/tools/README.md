# os-build/tools — what each helper does, and how to prove it still works

BF4-22. Every script the services lane uses to turn source into a claim lives here or in
`os-build/layer1/`. This page is the index: one line on what a tool does, the command that runs it,
and what a green result actually means.

Nothing in this directory is required to build the OS. These are the instruments, and the rule for
all of them is the same: **a tool that cannot fail is not a check.** Each one exits non-zero on a
finding, prints the finding, and is run in the same invocation the document it feeds quotes.

`drive.py` (the Pax-12h driver harness) lives on `buffy/pax-12h-plan` and `main`, not on this
branch; it is listed at the bottom with its home branch so nobody hunts for it here.

## The two gates

| Tool | What it does | Run it | Green means |
|---|---|---|---|
| `layer1/run_native.sh` | Builds every test driver (Goose → C → clang) against `host/host_shim.c` and runs it. Writes `host/run_rows.txt` on a **full** run only. | `./os-build/layer1/run_native.sh` | `29 of 29 drivers, 0 FAILS`. Exit 0 only if every program built and exited 0. |
| `layer1/check_services.sh` | Typechecks the whole corpus as 6 roots + one generated root per test. | `./os-build/layer1/check_services.sh` | `typechecked: 35 ok, 0 failed`. Exit 0 only if every root passes. |

Both are safe to run repeatedly and neither touches the kernel. A filtered run
(`run_native.sh t65_fs`) writes `run_rows.last_filtered.txt`, so a spot-check cannot silently
shrink the table the documents are generated from.

## The generators (documents, not opinions)

| Tool | Writes | Run it | Green means |
|---|---|---|---|
| `layer1/gen_services.py` | `services.json` (manifest), `SERVICES_SYSCALL_MAP.md` | `python3 os-build/layer1/gen_services.py` | Every service's ABI class is derived from its imports and the frozen table; nothing hand-typed. |
| `layer1/gen_transcripts.py` | `TRANSCRIPTS.md` | `python3 os-build/layer1/gen_transcripts.py` | Seven sections, each embedding the program's own stdout. Exits 1 and prints the missing log name if a run is absent — a transcript file never quietly loses a section. |
| `layer1/gen_service_runs.py` | The table and summary in `SERVICE_RUNS.md` | `python3 os-build/layer1/gen_service_runs.py` | Row count, RUNS count, assertion count and the one-line summary all come from `run_rows.txt`. Idempotent. |
| `layer1/gen_demo_facts.py` | `DEMO_FACTS.md` | `python3 os-build/layer1/gen_demo_facts.py` | Every number carries the command that produced it. `--check` exits 1 when the committed copy has drifted from the tree. |
| `layer1/gen_limits.py` | `LIMITS.md` | `python3 os-build/layer1/gen_limits.py` | Every numeric limit constant listed, with the test that exercises it or the word UNPROVEN. The count at the top is the honest coverage number. |

## The audits

| Tool | What it checks | Run it | Green means |
|---|---|---|---|
| `layer1/source_audit.py` | Braces, defined-before-use, declared error codes, duplicate `let`, non-Goose keywords, unknown std symbols | `python3 os-build/layer1/source_audit.py` | `111 files audited, 0 finding(s)` |
| `layer1/error_audit.py` | One error vocabulary: every code used is declared, nothing redefines one locally | `python3 os-build/layer1/error_audit.py` | `clean: every code used is declared` |
| `layer1/size_audit.py` | Fixed storage declared in the source, sized from the type table | `python3 os-build/layer1/size_audit.py` | `resident: … KiB, unknown-element arrays: 0`. Says in its own output what it cannot measure (stack, padding, .rodata). |
| `layer1/bootorder_check.py` | Boot order is a DAG, every dependency earlier, names match directories | `python3 os-build/layer1/bootorder_check.py` | `boot order is consistent -- 22 services, no cycles`, and it prints what that does not prove. |
| `layer1/linkmap.py` | Service→service import edges, and drift against the previous map | `python3 os-build/layer1/linkmap.py` | `52 distinct edges across 26 services`; a note that an import edge is not a permission. |
| `layer1/callmatrix_audit.py` | Every import edge has a permission row; ids resolve; no duplicate edges | `python3 os-build/layer1/callmatrix_audit.py` | `clean on permissions`, with the dormant rows it reports every time (67). |
| `layer1/audit_status.py` | Every `// Status:` line in `services/` re-measured against the current run rows | `python3 os-build/layer1/audit_status.py` | `97 status lines checked, 0 stale`. `--fix` rewrites the stale ones; report mode is the audit. |
| `tests/hostile/hostile_check.py` | The hostile-input packs are well formed: known codes, no duplicate case names | `python3 services/tests/hostile/hostile_check.py` | `93 cases across 10 packs`. It says in its own output that this proves the cases are well formed, **not** that a parser refuses them — that is what `t72_hostile` and `t73_shell_hard` are for. |

## The instruments that are not scripts

| Thing | What it is | Proving command |
|---|---|---|
| `layer1/host/host_shim.c` | The ten `sys_*` externs for a host process, matching Goose's codegen ABI. Refuses five on purpose. | `./os-build/layer1/run_native.sh` — if the shim drifted from the ABI, every program would print garbage or crash |
| `layer1/host/run_rows.txt` | The machine-readable pass/fail row set (`label\|status\|pass\|fail\|note`) | `awk -F'\|' '$2!="RUNS"' os-build/layer1/host/run_rows.txt` — prints only the rows that are not green |
| `services/tests/harness/link.goose` | The in-memory link the protocol pack talks through | `./os-build/layer1/run_native.sh t68_proto` |
| `os-build/layer1/host/` build logs | `*.log` (stdout of the run), `*.log.gen` (Goose codegen), `*.log.cc` (clang) | `tail -20 os-build/layer1/host/build/t65_fs.log` |

## How to reproduce a whole gate, in order

```sh
./os-build/layer1/check_services.sh          # typecheck: 35 ok, 0 failed
./os-build/layer1/run_native.sh              # run: 29 of 29, 0 failed
python3 os-build/layer1/gen_service_runs.py  # table follows the run
python3 os-build/layer1/gen_transcripts.py   # transcripts follow the logs
python3 os-build/layer1/gen_services.py      # manifest + syscall map
python3 os-build/layer1/gen_limits.py        # limit coverage
python3 os-build/layer1/audit_status.py      # status words: 0 stale
python3 os-build/layer1/gen_demo_facts.py    # facts: every number re-measured
```

If one of those exits non-zero, the document it feeds is stale and the run is not a gate.

## Elsewhere

| Tool | Home | What it does |
|---|---|---|
| `os-build/tools/drive.py` | `main`, `buffy/pax-12h-plan` | Drives the Pax-12h checkpoint list. Not on this branch — do not look for it here. |
| `os-build/mcp/mcp_client.py` | this branch | The MCP client the lane used to wire its toolchain (`mcp/WIRING.md`). Not part of any build. |
