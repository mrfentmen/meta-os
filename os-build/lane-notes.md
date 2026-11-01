# OS shell lane notes (Hana — shell and experience)

Branch: `hana/os-shell`. This file is the lane's notes file:
what was wired, what was not, and what is still owed.

## Status

UNCOMPILED — and, for this branch, nothing to compile: this
branch contains specs, formats, walkthrough drafts, and tests
only. No kernel code, no service code, no program code was
written here. Any future kernel or service code from this lane
is UNCOMPILED until the boss's Mac builds it, and UNPROVEN
until a QEMU boot log shows its behavior (KERNEL_SPEC.md
rules 2 and 3). No boot log is claimed anywhere in this lane.

## MCP and docs wiring — honest results

The lane file says to wire MCPs and docs tooling for your
languages before deep work, and to smoke test them. Here is
exactly what happened:

- Rust docs MCP: NOT WIRED. There is no MCP gateway on this
  VM (`~/workspace/mcp-gateway/` does not exist), no rustdocs
  MCP server available in the sandbox, and no Rust toolchain
  here (`rustc` and `cargo` are both absent). No MCP smoke
  call is claimed, because none happened.
- Fallback used instead: the in-repo docs were read directly
  from `origin/main` — `KERNEL_SPEC.md` (full text),
  `OS_BUILD_TASKS.md` (Hana section), `OPENCODE_OS_BUILD.md`
  Section O, `kernel/src/main.rs` (K1 source),
  `kernel/README.md`, and `kernel/Cargo.toml`. The
  availability check that DID run is: those files exist on
  `origin/main` and were read in this session. That is a docs
  read, not an MCP smoke test, and it is not presented as one.
- Goose docs: NONE EXIST to wire. Goose is the boss's own
  language (KERNEL_SPEC.md: its own language, not Go). There
  are no public docs, no toolchain, and no MCP for it. This
  lane invents no Goose syntax and quotes no Goose docs.
- Lobster docs: same as Goose. The boss's own agent layer
  language, no public docs, nothing to wire. No Lobster
  syntax is invented here.
- What would unblock real wiring: a gateway on this VM (or a
  Mac-side MCP host) plus published Goose and Lobster docs.
  Until then, the in-repo specs above are the docs, and this
  file says so.

## Linux reference — read and refer, never copy or port

Per del's correction, this is a from-scratch complete rewrite,
not a Linux port. Linux behavior is used here only as
reference for what to describe and beat: boot lines for humans,
status answers in the style of `uname` / `uptime` / `free`,
and log lines in the style of `dmesg`. The beat is stated in
`shell-spec.md`: Meta OS emits the same facts for eyes and
for agents at the same time, so agents never scrape text.

No Linux source tree on this VM was read for this lane, and
no Linux code was copied or ported into this branch. The
reference is behavioral only. Ours stays from scratch per
KERNEL_SPEC.md.

## H5 — programs stay warm, not hot

No program features were added in this branch. The diff
touches only `os-build/*`, `tests/os-shell-formats.test.mjs`,
and the one test-script line in `package.json`. No program
paths, no Trio surfaces, no Musica files were modified here.
Programs resume after the OS passes K2, per the boss's
sequencing — not in this lane.

## Timeline note

The boss wants this build in less than 12 hours. This lane
delivers what is real on that clock: a boot spec for both
citizens, exact banner/status formats as data, a NOT BUILT
home-surface status, and first-minute walkthrough drafts —
all testable by the suite. Kernel boot milestones (K1 proof
and beyond) stay with Rowan's kernel lane, OpenCode's
Mac-side build, and the Mac compile + QEMU boot log. This
lane promises no booted OS on any clock.

## Parked

The cybersecurity program is PARKED by the boss's order. It
was not started here.

## Still needed

- Milo gate-1 on this branch (gate rotation: Milo gates Hana).
- The boss's word on any merge. No merge is done or assumed.
- Pax gates kernel merges personally until K2 lands. This
  branch has no kernel code, so that gate does not apply to
  it; it is noted here so the distinction is explicit.
- Real MCP/docs wiring when a gateway and Goose/Lobster docs
  exist (see wiring section above).
