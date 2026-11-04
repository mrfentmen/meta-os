# Meta OS — four-lane OS work (no desktop, no QEMU)

Buffy owns the **native desktop rewrite** (dock, top bar, window chrome,
wallpaper, login art). These four lanes own everything **under** it: identity,
boot, userland defaults, build and proof.

- `plan/AGENT_OS_1.md` — identity, naming, the Ubuntu-to-Meta sweep
- `plan/AGENT_OS_2.md` — bootloader, splash, installer
- `plan/AGENT_OS_3.md` — user session, defaults, launcher, desktop entries, fonts
- `plan/AGENT_OS_4.md` — build, verification tooling, dead code, repo hygiene

---

## The one rule that applies to all four

**Do not run QEMU.** No boot, no `show_os.sh`, no `proof_boot.sh`, no
`frames_boot.sh`, no raw `qemu-system-*`.

Why: the machine must stay quiet while this work happens, and a boot proves
nothing another lane can read. Every lane proves its work with a parsing or
staging check it writes down. OS-4 additionally makes the guard real in code, so
this cannot be forgotten later.

Also for all four: **no sudo, no loop mount, no docker, no apt.** If a task
seems to need one, that task is wrong — prove it another way and write down why.

---

## How the four lanes cannot collide

Each lane works in **its own git worktree and its own branch**:

```sh
git worktree add /tmp/agent-os-1 -b agent-os-1 main
git worktree add /tmp/agent-os-2 -b agent-os-2 main
git worktree add /tmp/agent-os-3 -b agent-os-3 main
git worktree add /tmp/agent-os-4 -b agent-os-4 main
```

Never switch branches in `/Users/test/Desktop/meta-os` — last round two agents
shared one checkout, one commit landed on the wrong branch, and the repair cost
an hour. Worktree per lane makes that impossible.

Rules: commit only your own files, only on your branch. **No merge, no rebase,
no push, no `--force`.** Buffy merges after reading the four reports.

### File ownership — no overlaps

| Path | Owner |
|---|---|
| `os-build/identity/**`, `payload-theme/identity/**` | OS-1 |
| `os-build/iso/{plymouth,splash,calamares}/**`, `payload-theme/grub/**`, `iso/grub-fix.sh`, `face/plymouth/**`, `metaos-theme/splash/**` | OS-2 |
| `payload-theme/{terminal,fonts,apps}/**`, `metaos-theme/{terminal,fonts,apps}/**`, `os-build/face/launcher.py`, `agent-layer/desktop-entries/**` | OS-3 |
| `os-build/iso/build_iso.sh`, `build-arm64-inner.sh`, `finalize-iso-tree.sh`, `merge-layers.sh`, `metaos-install.sh`, `os-build/tools/**` | OS-4 |
| `os-build/face/**` (except `launcher.py`), `face/**`, `payload-theme/{gtk,xfwm4,dock,panel,icons,wallpapers}/**` | **Buffy** |

If a lane needs a change outside its list, it writes the exact line in its
report as a **request**. It does not make the edit. That is the difference
between a merge that takes ten minutes and one that takes a night.

### Shared contracts — so nothing waits on anything

Lanes must not block each other, so these three values are fixed up front and
everyone codes against them:

1. **Identity:** `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `NAME="Meta OS"`,
   `ID=metaos`, `ID_LIKE=debian`, `VERSION_CODENAME=ribbon`, hostname `metaos`,
   user `meta`, product name `Meta OS`.
2. **Allowlist file** (`os-build/identity/ALLOWLIST.tsv`, written by OS-1, read
   by OS-4): tab-separated `path<TAB>pattern<TAB>verdict<TAB>reason`, verdict
   ∈ `compat | attribution | generated`. OS-4 must treat a missing file as
   `absent (owned by OS-1)`, never as a pass.
3. **Offline checks** are scripts with a `--check` mode that exit non-zero on
   failure. OS-4's `verify_tree.sh` calls them by path and treats a missing one
   as `absent`.

That is the whole coordination surface: three contracts, one file each.

---

## Paste-ready prompts

Give each agent one of these, in its own chat, in the repo.

**Agent 1**
> You are OS-1 on Meta OS. Read `plan/AGENT_OS_1.md` and `plan/AGENT_OS_INDEX.md`
> in full, then execute the 50 tasks in order. Create your own worktree and
> branch `agent-os-1` as the index says. Do not run QEMU, do not mount anything,
> do not edit any path outside your ownership list. Commit only your own files
> on your branch, never merge or push. Finish by writing
> `os-build/lanes/AGENT_OS_1_REPORT.md` and report back with: commits, what you
> proved by running it, what you skipped and why, and every request for another
> lane.

**Agent 2**
> You are OS-2 on Meta OS. Read `plan/AGENT_OS_2.md` and `plan/AGENT_OS_INDEX.md`
> in full, then execute the 50 tasks in order. Create your own worktree and
> branch `agent-os-2` as the index says. Do not run QEMU, do not mount, do not
> touch `os-build/face/` or `os-build/iso/build_iso.sh`. Commit only your own
> files on your branch, never merge or push. Finish by writing
> `os-build/lanes/AGENT_OS_2_REPORT.md` and report back with: commits, what is
> proven by parsing only, what would need a boot, and every request for another
> lane.

**Agent 3**
> You are OS-3 on Meta OS. Read `plan/AGENT_OS_3.md` and `plan/AGENT_OS_INDEX.md`
> in full, then execute the 50 tasks in order. Create your own worktree and
> branch `agent-os-3` as the index says. Do not run QEMU, do not mount, do not
> edit the desktop files listed as Buffy's. Commit only your own files on your
> branch, never merge or push. Finish by writing
> `os-build/lanes/AGENT_OS_3_REPORT.md` and report back with: commits, the three
> judge-visible Ubuntu leftovers you found, and every request for another lane.

**Agent 4**
> You are OS-4 on Meta OS. Read `plan/AGENT_OS_4.md` and `plan/AGENT_OS_INDEX.md`
> in full, then execute the 50 tasks in order, starting with the QEMU guard
> because it protects the other three lanes. Create your own worktree and branch
> `agent-os-4` as the index says. You own the tools that boot VMs — read and edit
> them, run none of them except the one refusal test. Do not mount, do not master
> an ISO. Commit only your own files on your branch, never merge or push. Finish
> by writing `os-build/lanes/AGENT_OS_4_REPORT.md` and report back with: the
> refusal transcript, the full `verify_tree.sh` table, and every request for
> another lane.

---

## What Buffy does while they work

The native desktop port, in this order: extract the tokens from `face/face.css`
into one source of truth, then panel, then window chrome, then dock, then
wallpaper and login art. Buffy does not touch any lane's paths either. When the
four reports land, Buffy merges in lane order 4 → 1 → 2 → 3 (guard first, then
identity, then boot, then userland) and re-runs `verify_tree.sh` after each
merge.
