# AGENT OS-4 — Build, proof tooling, dead code and repo hygiene

**Branch:** `agent-os-4`
**Worktree:** `git worktree add /tmp/agent-os-4 -b agent-os-4 main`

Read this whole file before your first command.

---

## Mission

Three jobs, in this order:

1. **Make the build honest.** One command that produces the ISO tree from the
   checkout, and one command that says whether the tree is sane — both
   runnable without booting anything.
2. **Make "don't boot" enforceable.** The tools that *can* start QEMU must
   refuse to start unless someone explicitly allows it. That is a code change,
   not a promise.
3. **Delete what is dead.** Duplicate theme trees, orphaned scripts, generated
   logs pretending to be source, files nothing reads. Dead code is where wrong
   claims hide.

---

## HARD RULES — breaking one of these fails the lane

1. **Never run QEMU.** You own the tools that launch it, so this matters most
   here: you will be reading and editing `show_os.sh`, `proof_boot.sh`,
   `frames_boot.sh` — **run none of them.** Prove they work by reading their
   control flow and by testing their *guard* branch only.
2. **No sudo, no mount, no docker, no `mkfs`, no ISO mastering that needs
   root.** Building the tree into a temp directory is fine; writing a real
   image is not yours.
3. **Never touch another lane's paths.** Yours are below.
4. **Never edit** `os-build/face/**`, `face/**`, or
   `os-build/iso/payload-theme/{gtk,xfwm4,dock,panel,icons,wallpapers}/**`.
   Those are Buffy's while the desktop is rewritten.
5. **Never delete a file another lane owns.** If `metaos-theme/` must shrink,
   list the files and hand the deletion to the owning lane. You may delete
   files nobody owns and nothing references — and you must prove "nothing
   references" with a grep you paste.
6. Commit only your files, only on `agent-os-4`. No merge, no rebase, no push.

---

## You own these paths (and only these)

```
os-build/iso/build_iso.sh
os-build/iso/build-arm64-inner.sh
os-build/iso/finalize-iso-tree.sh
os-build/iso/merge-layers.sh
os-build/iso/metaos-install.sh
os-build/tools/**                     (except proof_session.sh, read-only for you)
os-build/lanes/AGENT_OS_4_REPORT.md   (new file, yours)
```

`os-build/tools/proof_session.sh` is read-only for you: it talks to running
services and its owner is Buffy. Read it, do not edit it.

---

## Tasks

### A. The no-boot guard — do this first, it protects everyone (1–10)

1. Read every script under `os-build/tools/` and list the ones that can start a
   VM: name, line number, and the exact command they use.
2. Add a single guard function used by all of them: unless
   `METAOS_ALLOW_QEMU=1` is set, the script prints
   `refused: this tool boots QEMU. set METAOS_ALLOW_QEMU=1 to allow it.`
   and exits 2.
3. Put the guard in one shared file (`os-build/tools/qemu_guard.sh`) sourced by
   each tool, not copy-pasted five times.
4. Wire the guard in before the first QEMU command in each tool, and show the
   before/after of each insertion (file:line).
5. Make the refusal message name the tool and the flag, so a person who hits it
   knows exactly what to do.
6. Prove the guard: run one guarded tool **without** the flag and paste the
   refusal and the exit code 2. That is the only way you may run these tools.
7. Do not prove the allowed path. Say plainly in your report that the allowed
   path was not exercised, and why.
8. Apply the same guard to any helper in `os-build/iso/` that boots
   (`vm_install_proof.sh` exists — check it).
9. Add a short `os-build/tools/README.md` section listing every tool, whether it
   boots, and that it is guarded.
10. Make sure the guard cannot be bypassed by calling the tool from another
    script that sets the variable — it must be read from the environment only
    and documented as such.

### B. One verification entry point (11–22)

11. Inventory every existing checker in `os-build/tools/` and `os-build/iso/`:
    what it verifies, whether it needs a boot, whether it needs network.
12. Write `os-build/tools/verify_tree.sh`: one command, no arguments, that runs
    every **offline** check and prints a table `check | result | detail`.
13. It must exit non-zero if any check fails, and print `DEAD:` with the names
    when it does — the same contract `proof_session.sh` already uses.
14. Include at least: identity strings (OS-1's `check_strings.sh`), launcher
    allowlist selftest (OS-3's), `.desktop` entries (OS-3's), tree references
    (`Exec=`, `Icon=`, theme asset paths), and a "no Ubuntu in shipped files"
    row.
15. **Do not make it a blocker:** if another lane's checker is not present yet,
    the row must read `absent (owned by OS-N)` and the run must continue.
16. If the checker exists but fails, the row fails. Do not soften a real
    failure into a warning.
17. Run `verify_tree.sh` on the current tree and paste the whole table. Expect
    failures; that is the honest baseline.
18. Record the wall-clock time of a full run and the number of rows.
19. Make it work from any working directory.
20. Make it work without `git` (fall back to `find`), because the guest may not
    have a checkout.
21. Make it have a `--json` mode with one object per row.
22. Prove `--json` parses: pipe it through `python3 -m json.tool` and paste it.

### C. The build (23–32)

23. Read `build_iso.sh` end to end. Draw the pipeline: inputs, stages, outputs,
    and every point where it requires root or network.
24. State in one line what it currently produces and whether it produces
    anything at all on this machine.
25. Add a `--tree-only` mode that assembles the ISO *tree* into a temp directory
    and stops before mastering. No root, no loop mount.
26. Run `--tree-only` and paste the resulting tree listing and size.
27. Verify the tree contains: the face site, the theme, the agent payload, the
    splash, the boot menu files. One line each with PASS/FAIL.
28. Verify no file in the tree is a broken symlink.
29. Verify the tree has no absolute `/Users/` path baked into any text file.
    Paste the grep.
30. Record the tree size and the ten largest files — that is where an image
    gets fat.
31. Do not attempt to master an ISO. Say so explicitly in the report.
32. If `--tree-only` cannot work without root, say so, and instead write a
    dry-run that lists every copy operation without performing it — then run it.

### D. Dead code and duplicate trees (33–42)

33. Compare `metaos-theme/` and `os-build/iso/payload-theme/` file by file:
    identical, drifted, only-in-one. Table with counts.
34. State which tree the build actually ships, and cite the line.
35. For every file that exists in both and has drifted, say which side is newer
    by content (not by mtime) and which one a judge would see.
36. Hand every drift to the owning lane as a request. Do not fix another lane's
    file, and do not delete one.
37. List every script under `os-build/` that nothing references: prove it with a
    grep for its filename, paste the zero-hit result.
38. Delete only the unreferenced ones that nobody owns. List each deletion with
    its proof.
39. Check `os-build/logs/`: is generated output committed as if it were source?
    Say how many files, how big, and whether the build regenerates them.
40. Do not delete logs — they are evidence. Instead write
    `os-build/tools/logs_index.md`: what each log proves and when it was made.
41. Find files that claim something untrue in a header comment (a doc that says
    "installs X" where nothing installs X). List them with the contradiction.
42. Fix the ones you own; report the rest.

### E. Proof and handoff (43–50)

43. Write `os-build/lanes/AGENT_OS_4_REPORT.md`: the guard (with the refusal
    transcript), the verification table, the build tree result, the dead-code
    list, and every request for another lane.
44. In the report, answer directly: *can a judge verify this tree without
    booting anything, and what exactly do they type?*
45. State the single command you would put on screen in the demo, and paste its
    real output.
46. List every check that is `absent` because another lane has not landed yet —
    that is the dependency map for whoever merges.
47. Confirm `sh -n` passes on every shell file you touched, and that no tool you
    edited now lacks the guard.
48. Confirm no absolute `/Users/` path, secret or real hostname in your files.
49. List your commits (hash + subject), confirm nothing on `main`.
50. Confirm: QEMU run zero times, nothing mounted, nothing installed, no temp
    file left under the repo tree.

---

## Definition of done

- Every QEMU-launching tool refuses without `METAOS_ALLOW_QEMU=1`, proven by
  one refusal transcript.
- `verify_tree.sh` runs offline from anywhere, prints a truthful table, and
  treats a missing lane as `absent`, not as a pass.
- The build's tree-only path is proven, or its blocker is named.
- Dead files are gone with proof, and every cross-lane need is written down
  instead of done.
