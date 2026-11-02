# Buffy lane notes — research and tools

Branch `buffy/research`. Started 2026-11-01 on the boss's order
(`OS_BUILD_TASKS.md`, § Buffy). All three tasks are research tasks: no code, so
no compile gate and no parity bar apply. Nothing here is a boot claim.

## Standing rule: MCP and docs tooling wired before deep work

The rule says wire MCPs and docs tooling for the language, smoke call it, and
write down what you wired. Here is the honest state, with evidence.

**What already exists in the repo: nothing.** Checked 2026-11-01 against
`origin/main`:

- No `.mcp.json`, no `mcp.json`, no `.vscode/mcp.json`, no `docs/MCP.md`
  (each: `fatal: path ... does not exist`).
- `rustdocs` appears only as prose, in `OPENCODE_OS_BUILD.md`,
  `OS_BUILD_TASKS.md` and `batches/B01..B17.md`. It is a *pattern named in a
  task*, not a server with a config file.
- `.gitignore` holds only `.sentinel-cron.lock` and
  `server/queue/crew-data/`.

**So the "rustdocs MCP pattern this project already does" does not exist as an
artifact.** OS-182 says "wire the Rust docs MCP the way this project already
does (rustdocs pattern)". There is no "already does" to copy: somebody has to
create the config. That is Section M's call (OS-181..OS-186, OpenCode lane) and
it is not mine to invent, so this lane did not create a config file or claim a
wiring it did not make.

**What this lane did wire instead:** the docs sources themselves, checked live
today, which is the substitute the rule asks for when no MCP exists.

| Layer | Docs source | Smoke result 2026-11-01 |
|---|---|---|
| Rust | docs.rs and the rust-lang book, as the target of the rustdocs pattern | reachable, but not wired as an MCP; no server exists to call |
| Goose | `github.com/aardappel/goose` README, `docs/tutorial.md`, `docs/reference.md`, `docs/goose_spec.md`, `docs/command_line.md`, `docs/packages.md`, `docs/stdlib.md`, `LICENSE` | **200, all fetched and read.** `LICENSE` is Apache-2.0. |
| Lobster | `strlen.com/lobster`, `aardappel.github.io/lobster/getting_started.html`, repo README, repo LICENSE | **200.** One wrong guess: `aardappel.github.io/lobster/command_line_arguments.html` returned **404**, which is a bad URL, not a missing feature. |
| Goose releases / install | releases page and README "Install a release" section | read; platform list and glibc/macOS floors recorded in `ecosystem-watch.md` |
| MCP availability | searched for an MCP server for both languages | **none exists for either.** Recorded as such, not faked. |

MCP status per the rule's own wording, so it cannot be misread later. Updated
2026-11-01 when the boss ordered the MCPs connected:

- **Rust: WIRED and verified.** `docs-rs` (`@nuskey8/docs-rs-mcp@1.0.1`, MIT).
  Proven by a direct stdio JSON-RPC conversation: `initialize` OK on protocol
  2024-11-05, four tools listed, and two real calls returning docs for the
  `bootloader` crate. One tool, `docs_rs_search_crates`, fails with a 403
  because the server sends no User-Agent and crates.io refuses those. Full
  detail and the workaround: `os-build/mcp/WIRING.md`.
- **Goose: no MCP exists.** Being built by the boss now; the config slot and the
  smoke procedure are written and waiting in `os-build/mcp/WIRING.md`. Until it
  lands, the real tooling is `goose lsp`, which is blocked on Goose not being
  installed on this machine.
- **Lobster: no MCP, no LSP.** Docs sources only.

Carried forward from the earlier check, still true: **`rustdocs` in the batch
and OS-build docs is a pattern named in prose, not a wired server**, and no MCP
config existed in this repo at all until this work added one.

## Deliverables

| Task | File | State |
|---|---|---|
| B1 tools manifest research | `os-build/research/tools-candidates.md` | done. Ten Section J categories, five candidates each, license gated. |
| B2 other distros notes | `os-build/research/distros/` (8 files: nixos, arch, alpine, steamos, chromeos, redoxos, serenityos, haiku) | done. One system per file, borrowable idea plus license position, GPL marked. |
| B3 Goose and Lobster ecosystem watch | `os-build/research/ecosystem-watch.md` | done. Dated links, install requirements, name collision, MCP absence, open questions handed to their owners. |

### Report line

`B1-B3 RESEARCH  files=11  code=none  gate1=na  gate2=na  sources=checked-2026-11-01  mcp=docs-rs-WIRED(verified) goose=none lobster=none`

## Findings that move another lane's work

These are the ones worth interrupting someone for, so they are at the top of
the file rather than buried:

1. **Goose and Lobster are both real languages by the same author**
   (Wouter van Oortmerssen). Goose is weeks old. That is a single-source risk
   for the entire Layer 1 and Layer 2 story, and it should be written into the
   OS build report rather than discovered in a month.
2. **`goose run` refuses programs that start threads** (TinyCC cannot place
   thread-local storage). OS-156's heartbeat daemon must be `goose build`-ed.
3. **The Linux Goose binary needs glibc 2.35+.** Debian 12 satisfies it.
   Alpine would not, so the carrier choice is load bearing for Layer 1.
4. **macOS prebuilt Goose needs `xattr -dr com.apple.quarantine`** after
   unpacking, or it looks like a corrupt binary.
5. **Homebrew's `goose` formula IS this language and officially conflicts with
   `block-goose-cli`.** Two different projects both install a binary named
   `goose`. Pin an absolute path, log `goose version` and `goose toolchain`.
6. **No MCP exists for either language**, so OS-183 and OS-184 should say "docs
   source plus LSP" for Goose and "docs source" for Lobster, not "MCP wired".

## Discipline notes

- No pull, no merge, no force push. This branch is `buffy/research` off
  `origin/main` at `7a5ec4b`, and it only adds files under
  `os-build/research/`. Nothing existing was edited, so nothing here can
  overwrite another lane's work. No path in this branch collides with
  `os-build/TOOLS_MANIFEST.md`, `os-build/gates.md`, `os-build/shell-spec.md`,
  `os-build/research/goose.md`, `os-build/research/lobster.md`,
  `os-build/research/others/` or `os-build/research/layer-map.md`, which are
  other lanes' targets.
- The cybersecurity program stays parked. The security tools in
  `tools-candidates.md` §8 are an inventory of what already exists on a normal
  image, with every row marked inventory only, no work started.
- Nothing in this lane needed the Mac. No build was attempted, so there is no
  UNCOMPILED caveat to add: there is no code.
- Stage boundary report: not posted to room 1. This lane had no bus access from
  where it ran, and I will not claim a post I did not make. The boss has it
  directly; Pax should relay if it belongs on the bus.

---

# L4 build lane — B-1 … B-6, measured (2026-11-01, post-Pax rulings)

Pax ruled F1–F4 and cleared this lane on B-1..B-6. Everything below was run on this Mac; the exit
status and the numbers are the tools' own output.

## What the pass changed, in numbers

| | Before this pass | After |
|---|---|---|
| `goose check` over the corpus | 7 of 95 files pass, **297 errors** | **31 programs, 0 errors**, exit 0 |
| Source audit | not runnable against a broken tree | 107 files, **0 findings** |
| Storage measured | 384.7 KiB | 372.7 KiB (34 services, re-measured after the split) |

The 297 were not noise. Three of them are permanent language facts, worth writing down once so
nobody re-derives them: **Goose has no `++`/`--`** (688 uses in the corpus, all mechanical);
**parameters are immutable** (`p.bytes = 0` in a parameter is a type error; copy to a local);
and **`T&` refuses an rvalue** (`f(g())` → "cannot pass P as P&", so verse the temporary).

## B-1 — the root

`import a.b.c;` resolves from the root file's directory, and a program may export `svc_entry` only
once. So the corpus is not one program: `services/root.goose` covers the libraries and the 16
non-entry services, `services/root_<svc>.goose` covers each of the six entry points, and each test
gets a generated one-line root. Adding `root.goose` alone killed ~225 of the 297.

The six entry points then collided with each other (`svc_entry` defined six times in one program),
which is why each service's entry lives in its own `entry.goose`: importing a service's *logic* no
longer drags a second `main` in. That split is a real structural decision, not a compile workaround.

## B-2 — the dialect

Eleven files, all mechanical once the root existed: `++`/`--` rewrites with indexed lvalues restored
by hand (`socks[slot].out_count++` had become `= out_count + 1`), reserved words (`block`, `guard`,
`fill`), `push` on a slice parameter instead of a local, `let` reassignment to `var`, `T[N]`
needing exact element counts where `[]` only fills `[..N]`, `format_int` taking `(out, v, base,
width, pad)` and returning nothing, `sys_exit` returning nothing, and `fmt.append_char` becoming a
bare `append_char` because Goose's namespace is flat.

Two of the errors were mine, found by re-reading my own rewrite: the blanket `++` substitution
broke indexed lvalues, and a blanket `let`→`var` touched prose inside comments. Both are fixed;
the prose-restore pass is why comments in those files still read as English.

## B-3 — the two documents

`BUFFY_REPORT.md` and `SIGNOFF.md` both opened with "no Goose toolchain" and "the kernel is at
K1". Both were true of the sandbox that wrote the sources and false here. Corrected to the
measured words, with a fifth status word this pass earned: **TYPECHECKED** — the front end accepts
the program and its imports; it is not COMPILED, because no object file, link or binary exists.
COMPILED stays at zero rows.

## B-4 — what "exercised" can honestly mean

The 25 test programs typecheck. **Not one has run**, because nothing in the tree can run them: no
Goose backend has produced a binary and no kernel service host exists to load one. The harness that
does exist is `os-build/layer1/check_services.sh`, which is now the typecheck gate.

## B-5 — `SERVICES_SCOPE.md`

Written because "Layer 4" meant three sizes in three documents: 5 Goose files on `main`, 95 in this
lane, and a scoreboard row that said DESIGNED. The page names them — the merged set, the corpus, and
the specified tier — and states which of them runs (none).

## B-6 — the gate harness, proven again

`drive.py` (on `main`) is the harness. Verified end to end today, not by reading it: booted the
8.2 MB image, typed `status` and `help`, and captured

```
HELLO FROM USERSPACE
INT user page-fault addr 0x0 err 0x4: task killed
STATUS tasks=7 ticks=380 heap_free_kb=31
commands: status help
```

That is the recipe `gate.sh` should wrap. `gate.sh` itself still does not exist — OpenCode's
deliverable, per Pax's O-1/O-3 rulings.

## What remains, and whose

- **COMPILED for one program** — needs a Goose backend. Q5 (`K6_NEEDS.md`) is answered the moment
  `example` produces an object file; either answer is progress.
- **RUN for one program** — needs that binary plus the K6 userspace pattern, which is proven here.
- **A runner in the kernel** (`svc_start` / `svc_ready`) — that is the milestone that makes L4 a
  tier instead of a library. Not this lane's to write; Pax gates it.
- **The start timeout** — `starting_since_ms` on the slot, checked by the supervisor tick.
- **67 dormant permission rows** — each a real call or a row to delete; printed on every run.
