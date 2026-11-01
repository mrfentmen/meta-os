# Goose and Lobster ecosystem watch

Lane: Buffy, research and tools. Task B3. First entry 2026-11-01.
RESEARCH. Links and dates are the evidence; re-check them, do not trust the
summary.

How to read this: every claim carries the URL and the date it was checked.
Where a source was weak (a community comment rather than the project's own
docs) it says so. Nothing here is a compile claim, a build claim or a boot
claim: no Goose or Lobster binary has been installed by this lane.

## 1. What the two layer names actually are

This is the finding that changes Section K and Section L, so it goes first.
Both names resolve to real, existing languages, and both are by the same
person: Wouter van Oortmerssen (GitHub `aardappel`, previously of Game
Labs/Google, the author of FlatBuffers and of the languages Lobster and Goose).

| Layer | Language | Repo | License | Age |
|---|---|---|---|---|
| Layer 1, services | Goose | github.com/aardappel/goose | Apache-2.0 (verified, `LICENSE`, 202 lines, 2026-11-01) | New. Public work around Oct 2026. |
| Layer 2, agents and apps | Lobster | github.com/aardappel/lobster | Apache-2.0 (verified 2026-11-01, README and strlen.com both state it) | Mature-ish. Years of development, game oriented. |

So the boss's "Goose is its own language, not Go" (KERNEL_SPEC) is correct in a
stronger sense than he may have meant: there is an actual Goose language, it is
not Go, and it is designed as a memory-safe systems language with no heap, no
GC and no lifetime annotations, compiled to C. Lobster is a statically typed,
Python-esque, game oriented language with compile-time memory management.

**What that means in practice:** we are not inventing two languages. We are
adopting two young, single-author languages as the two upper layers of an
operating system. That is a real architectural bet with a real single-source
risk, and Section K's "if the toolchain is thin, say exactly how thin" was the
right question. It is not thin. It is *small and young*, which is a different
and more manageable problem, and both halves of that need saying.

## 2. Goose: what the toolchain actually is

Best documented of the two. Its own docs, checked 2026-11-01:
[tutorial](https://github.com/aardappel/goose/blob/master/docs/tutorial.md),
[reference](https://github.com/aardappel/goose/blob/master/docs/reference.md),
[specification](https://github.com/aardappel/goose/blob/master/docs/goose_spec.md),
[command line](https://github.com/aardappel/goose/blob/master/docs/command_line.md),
[packages](https://github.com/aardappel/goose/blob/master/docs/packages.md),
[stdlib](https://github.com/aardappel/goose/blob/master/docs/stdlib.md),
plus `samples/` (thirty-one complete programs) and `bench/results.md`.

**One binary does everything.** `goose` is the compiler, the in-process runner,
the build tool, the package fetcher, the formatter, and the language server:

| Command | What it does |
|---|---|
| `goose run file.goose` | Compiles to C, compiles that C in memory with bundled **TinyCC**, runs in process. No build step, no files. |
| `goose build file.goose` | Writes C, compiles with a real C compiler on the machine, links an executable. |
| `goose check` | Parses and typechecks, writes and runs nothing. |
| `goose fetch` | Fetches declared packages for an offline session. |
| `goose format` | Rewrites files to the standard layout. |
| `goose toolchain` | Reports the C compiler, cmake and git it found, and `GOOSE_HOME`. |
| `goose version` | Compiler version and runtime version. |
| `goose lsp` | Language Server Protocol over stdio. |
| `goose completion <shell>` | bash, zsh, fish, PowerShell. |

**Packages** are git repositories pinned by tag or commit, declared only in the
program's root file, flat and single-version per program. Blessed packages
(`gfx`, `audio`, `ui`, `physics`, from `goose_gfx` and `goose_physics`) can be
compiled into the compiler; fetching any other package needs `git`, `cmake` and
a C compiler the first time.

**Install paths for the Mac (this is OS-154's actual answer):**

1. **Prebuilt release, recommended.** Prebuilt compilers for Windows x64, Linux
   x64, macOS Apple silicon and Intel, on the
   [releases page](https://github.com/aardappel/goose/releases). Unpack
   anywhere, put the directory on `PATH`; the compiler finds the stdlib, the
   TinyCC runtime and the packages beside itself, and keeps build output under
   `~/.goose` (`GOOSE_HOME`). The archive also contains the docs, the samples,
   and a **VS Code extension** (`vscode/goose-language.vsix`).
2. **Build from source.** CMake 3.27+, a C++20 compiler (MSVC, clang or gcc)
   and Python 3 for the test and sample runners. TinyCC is in tree.
   `-DGOOSE_BUILTIN_LIBS=all` fetches the graphics packages with git; on Linux
   SDL needs X11 or Wayland dev packages, and without them the build drops the
   `gfx` module and tells you what to install.

**Hard requirements, and the traps:**

- **Linux prebuilt needs glibc 2.35 or later** (project's words: Ubuntu 22.04,
  Debian 12). This is why Alpine cannot be a carrier: no glibc at all. Our
  Debian 12 carrier is fine, by luck of the boss's order.
- **macOS prebuilt needs macOS 13.3 or later**, and a downloaded archive will
  not run until `xattr -dr com.apple.quarantine` is run on the unpacked
  directory. Expect this to look like "the binary is corrupt" on the Mac.
- **`goose run` needs the C library headers** on Linux (`libc6-dev` or
  `glibc-devel`) and the Xcode command line tools SDK on macOS, even though it
  needs no C compiler.
- **`goose run` refuses threads.** TinyCC cannot place the thread-local storage
  each worker's data stacks live in, so any program that starts threads must be
  `goose build`-ed. **This bites Section K directly:** OS-156 is a daemon with a
  heartbeat, and the natural Goose way to write a heartbeat is a thread or a
  timer on one. If it uses workers, `goose run` will refuse it and only
  `goose build` will run it. Decide that at OS-156, not after the script is
  written.
- **TinyCC does not optimize**, so any timing claim is only meaningful on a
  `goose build`. Our prove-it rules already say no unmeasured claims; this is
  the same rule applied to the services layer.
- **The compiler is about 30 thousand lines of C++** in the project's own
  description, which is small enough to be readable and small enough to be one
  person.

## 3. Lobster: what the toolchain is

Home: [strlen.com/lobster](https://strlen.com/lobster/), docs at
[aardappel.github.io/lobster](https://aardappel.github.io/lobster/), source at
github.com/aardappel/lobster. Apache-2.0.

- **Getting it:** prebuilt 64 bit binaries for Windows, Mac and Linux are
  attached to the repo's **GitHub CI runs** (click the latest green run, the
  artifacts are at the bottom), not primarily the releases page, which the docs
  themselves call "usually way behind". An AUR package `lobster-language`
  exists (Apache-2.0, checked 2026-08-28) for Arch users. There is no Debian
  package, no Homebrew formula and no package manager of its own.
- **Building it:** Linux needs git, CMake, a C++17 compiler and Mesa dev files
  (`mesa-common-dev`); macOS needs Xcode and CMake via `sh build_osx.sh`;
  Windows uses the checked in solution. Then `bin/lobster samples/pythtree.lobster`.
- **The runtime is graphics oriented.** It is a game language with an engine
  attached, so a "run a script with no window" mode is the first thing Section L
  will need and the first thing to test. **Not verified by this lane.** Flagged
  in section 6 as an open question rather than assumed either way.
- **Execution model:** a closed world ahead-of-time compiler to bytecode for its
  own VM, with no JIT. Community sources (a Reddit thread, weak) also say no
  REPL; treat that as likely, not confirmed.
- **Embedding:** the interpreter is C++ and the project is structured as a
  library plus a driver, so embedding is plausible, but I did not verify an
  embedding guide. **OS-167 owns that answer**; this lane did not duplicate it.

## 4. The name collision, which is operational and will bite

There are now **three** things called `goose` that a developer might mean, and
two of them install a binary with that exact name:

1. **The Goose language** (ours, `aardappel/goose`). Homebrew core formula
   `goose`, described as "Open source programming language to build
   simple/reliable/efficient software".
2. **Block's goose AI agent** (`aaif-goose/goose`, Apache-2.0, Rust, MCP client
   with 70+ extensions, donated to the Agentic AI Foundation in April 2026).
   Homebrew formula `block-goose-cli`. Its docs are at goose-docs.ai.
3. **pressly/goose**, a Go database migration tool, which also ships a binary
   named `goose`.

**Homebrew states the conflict explicitly:** formula `goose` "Conflicts with:
block-goose-cli (because both install `goose` binaries)", and the
`block-goose-cli` page says the same in reverse (checked 2026-11-01,
[formulae.brew.sh/formula/goose](https://formulae.brew.sh/formula/goose)).

Practical consequences for this build, all cheap to prevent:

- **Never install Goose with `brew install goose` on a crew VM and assume it
  worked.** On a machine that already has Block's agent, brew will refuse or
  replace, and either way `which goose` stops being an answer.
- **Put the language binary somewhere explicit** (the unpacked release
  directory, added to `PATH`) and record the absolute path plus
  `goose version` and `goose toolchain` output in the install log. That is the
  only evidence that survives a machine rebuild.
- **When searching for docs, "goose" alone returns the AI agent.** Always search
  `aardappel goose` or the repo URL. This lane's own first search for a Goose
  language had to be steered that way.
- The same class of problem exists for Lobster (there is a `lobster`-named
  package in some distros that is unrelated, and the AUR entry declares
  conflicts with `lobster` and `lobster-language-bin`), but it is quieter.

## 5. MCP: the honest answer for both layers

**There is no MCP server for Goose the language, and none for Lobster, as of
2026-11-01.** Section M (OS-183, OS-184) tells the OpenCode lane to say plainly
which case it is, so here it is plainly:

- **Goose:** no MCP. What exists instead is *better for coding and useless for
  agents*: `goose lsp` (a real Language Server) and the VS Code extension that
  ships inside the release archive. Those are the right wiring for Section M's
  docs-and-editor need, and they should be written up as the substitute rather
  than described as an MCP.
- **Lobster:** no MCP, and no LSP found. Editor support is syntax highlighting
  plus running the binary. The substitute is the docs plus a build/run note.
- **Do not confuse the layers.** Block's goose *is* an MCP client with dozens of
  extensions. That is a different program with the same name and it says nothing
  about our Layer 1.
- The one MCP that genuinely matters for us is the one OS-163 builds **in**
  Goose: the MCP host. That is us serving tools, not us consuming docs, and it
  is the piece that makes the OS agent native.

## 6. Open questions this lane is handing over, not guessing

| Question | Who owns it | Why it matters |
|---|---|---|
| Does a Lobster script run with no window/GPU in a headless session? | OpenCode, OS-168/OS-169 | If not, the whole agent layer needs a headless path decided at OS-170, not discovered at OS-173. |
| Does `goose build` produce a binary that runs inside our image, or only on the dev carrier? | Section K, after K6 | Cross compilation is not in the Goose docs; a `no_std` kernel with no libc changes the answer completely. |
| Lobster embedding: is there a documented C++ embedding API? | OpenCode, OS-167 | Decides whether Lobster is a process we spawn or a library we link. |
| Can Goose packages be vendored for an offline build? | OS-154, `goose fetch` + `--offline` | The docs say yes (`goose fetch`, `--offline`). Verify it, because an air gapped build is the only honest one. |

## 7. How this file gets updated

Add a dated entry at the top of this section, do not rewrite history in the
body. A new entry needs: the URL, the date, what changed, and which of the two
layers it affects. Anything that changes an install step gets copied into
`os-build/TOOLS_MANIFEST.md` and the install script, or it did not happen.

Next scheduled re-check: when K2 lands, and after any Goose or Lobster version
bump. Both projects are young enough that a two month old note is a rumour.

### Change log

- **2026-11-01** — first entry. Established: both layers are real existing
  languages by one author; Goose is Apache-2.0 with a complete single binary
  toolchain, prebuilt for our three platforms, glibc 2.35+ on Linux, threads
  only under `goose build`; Lobster is Apache-2.0 with a CI artifact install and
  a CMake/C++17 build; no MCP exists for either; `goose` the binary name
  collides with two other projects including an official Homebrew conflict.
