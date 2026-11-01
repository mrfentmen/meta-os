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

MCP status per the rule's own wording, so it cannot be misread later:
**Rust: not wired (no server, no config). Goose: not wired (no MCP exists).
Lobster: not wired (no MCP exists).** The Goose LSP (`goose lsp`) and the VS
Code extension shipped in the release archive are the real tooling that exists,
and Section M should treat them as the substitute rather than describing them
as an MCP.

## Deliverables

| Task | File | State |
|---|---|---|
| B1 tools manifest research | `os-build/research/tools-candidates.md` | done. Nine Section J categories, five candidates each, license gated. |
| B2 other distros notes | `os-build/research/distros/` (8 files: nixos, arch, alpine, steamos, chromeos, redoxos, serenityos, haiku) | done. One system per file, borrowable idea plus license position, GPL marked. |
| B3 Goose and Lobster ecosystem watch | `os-build/research/ecosystem-watch.md` | done. Dated links, install requirements, name collision, MCP absence, open questions handed to their owners. |

### Report line

`B1-B3 RESEARCH  files=10  code=none  gate1=na  gate2=na  sources=checked-2026-11-01  mcp=not-wired(none-exists)`

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
