# AGENT OS-2 — Boot chain, splash and the installer

**Branch:** `agent-os-2`
**Worktree:** `git worktree add /tmp/agent-os-2 -b agent-os-2 main`

Read this whole file before your first command.

---

## Mission

Between the machine turning on and the desktop appearing there are three
surfaces: the bootloader, the splash, and the installer. All three still carry
the base image's name and art in places. You own all three.

You are also the lane that fixes the *duplication*: splash and boot files exist
in more than one tree, and a build that picks the wrong copy is how a green
Ubuntu screen survives a fix that was already made.

---

## HARD RULES — breaking one of these fails the lane

1. **Never run QEMU, ever.** Not `show_os.sh`, not `proof_boot.sh`, not
   `frames_boot.sh`, no raw `qemu-system-*`, no `-kernel`/`-initrd` test boot.
   You cannot prove your work by booting, so prove it by parsing.
2. **No sudo, no loop mount, no docker, no `mkfs`, no `grub-install`,
   no `update-initramfs`, no `plymouth` commands.** All of those need a root
   filesystem or a boot. Build files instead; show files.
3. **Never touch another lane's paths.** The list of yours is below.
4. **Never edit `os-build/face/provision.sh`.** Buffy owns it. If your work
   needs a line installed into the image, write the line in your report.
5. **Do not edit `os-build/iso/build_iso.sh`** — OS-4 owns the build scripts.
   If the build must copy one of your files, write the exact line as a request.
6. Commit only your files, only on `agent-os-2`. No merge, no rebase, no push.

---

## You own these paths (and only these)

```
os-build/iso/plymouth/**
os-build/iso/splash/**
os-build/face/plymouth/**
os-build/iso/payload-theme/grub/**
os-build/iso/grub-fix.sh
os-build/iso/calamares/**
metaos-theme/splash/**
os-build/lanes/AGENT_OS_2_REPORT.md    (new file, yours)
```

`metaos-theme/splash/` is legacy and may duplicate what you own elsewhere. You
may edit it; you may not delete the directory (OS-4 decides the theme tree).

---

## The identity contract (agreed, do not contradict)

`PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `NAME="Meta OS"`, `ID=metaos`,
`ID_LIKE=debian`, `VERSION_CODENAME=ribbon`, hostname `metaos`, user `meta`.
Boot and installer surfaces show **Meta OS**, never Ubuntu, never Xubuntu.

---

## Tasks

### A. Inventory the three surfaces (1–8)

1. List every file under `os-build/iso/plymouth/`, `os-build/iso/splash/` and
   `os-build/face/plymouth/` with size, and say which one a build would
   actually install. Cite the line that installs it.
2. Do the same for `os-build/iso/payload-theme/grub/` and
   `os-build/iso/grub-fix.sh`.
3. Do the same for `os-build/iso/calamares/` — list every module config, what
   reads it, and what it would make the installer say.
4. Find every copy of `metaos.plymouth` in the tree. Diff them. Name the
   canonical one and the copies that must die.
5. Write down which of these surfaces are *shipped* (copied into the image or
   ISO) and which are orphaned files nobody reads. Orphans are OS-4's problem;
   list them for the report.
6. `git grep -n "ubuntu"` inside your paths. Bucket as identity leak / honest
   base-image note / dead comment.
7. `git grep -n "Xubuntu\|xubuntu"` inside your paths. Same bucketing.
8. Write the inventory into your report as a table before you change a byte.
   This is your baseline; without it you cannot claim an improvement.

### B. The splash — one theme, Meta art, no Ubuntu fallback (9–20)

9. Pick the canonical plymouth theme directory. State the choice and why.
10. Write `metaos.plymouth` clean: `ModuleName`, `ImageDir`, `LinkFile`,
    `Color`. No path that does not exist, no reference to `ubuntu-logo` or
    `ubuntu-text`.
11. Ship a `metaos.script` that draws the Meta mark and the product name. It
    must draw something even if the art is missing — a text fallback, not a
    black screen.
12. Handle the "splash never ran" case honestly: if the theme is missing,
    plymouth shows text mode. Document that as the fallback rather than
    pretending it cannot happen.
13. Kill every reference to `ubuntu-text` and `ubuntu-logo` inside your paths
    and show the before/after grep.
14. Make the theme resolution deterministic: the same `plymouthd.defaults`
    logic must not be able to pick an Ubuntu theme on this image. Show which
    file decides it, and what value makes Meta win.
15. Write `os-build/iso/plymouth/INSTALL.md`: the four files that must land,
    where each goes, and the one command a build would run.
16. Verify your theme files parse: a small parser or an `awk` check that every
    key in `metaos.plymouth` is a real key, no typos, no duplicates. Run it.
17. Check the art files you reference actually exist in your tree. `test -f`
    each one and paste the output.
18. If the art does not exist, do not invent a binary. Reference the Meta
    asset that exists (state its path) or ship a documented text-only theme.
19. Write the fallback contract in one paragraph at the top of `INSTALL.md`:
    what the user sees if the theme is broken.
20. Confirm no file you wrote is executable-by-accident (modes 644 for configs,
    755 only for scripts), and paste `ls -l`.

### C. The bootloader (21–30)

21. Inventory the grub files you own: menu entries, theme fragments, defaults.
    For each, what shows on screen and where it is set.
22. Rewrite the boot menu entries so the choice reads `Meta OS` and the
    recovery entry says what it recovers. No Ubuntu strings.
23. Set a sane default: the Meta entry is default, timeout long enough to
    choose recovery on purpose, short enough not to look hung. State the value
    and why.
24. Remove the `Ubuntu` distributor string the bootloader prints, or replace
    it with `Meta OS`. Show the file and the line.
25. If a grub theme is referenced, verify every referenced asset exists in your
    tree. If it does not, drop the reference rather than shipping a missing
    file.
26. Check `grub-fix.sh` line by line: what it rewrites, whether it is
    idempotent, and whether it is still needed at all. State a verdict.
27. If `grub-fix.sh` is needed, make it `--check`-capable and idempotent, and
    prove both on a staged fake directory tree under `mktemp -d`.
28. Prove the fake-tree run: apply twice, diff the trees, show no drift.
29. Add a check that fails if any grub file you own contains `ubuntu`
    (case-insensitive), and run it.
30. Confirm nothing you changed would stop a machine booting if a file were
    missing — i.e. every file you reference is optional with a defined
    fallback, or is listed as required in `INSTALL.md`.

### D. The installer (31–42)

31. Inventory `os-build/iso/calamares/`: every module config, the branding
    directory, the package list, the display-manager config, the unpackfs
    notes.
32. Fix `meta-branding.sh`'s `ID_LIKE=ubuntu` — it must be `debian`. Show the
    line before and after, and say what breaks if it stays `ubuntu`.
33. Make the installer's product name, version, short name and URLs all Meta,
    in every branding file. List each file and its values.
34. Make sure the installer cannot write Ubuntu's identity onto the installed
    system: trace which identity files the install copies, and confirm they are
    Meta or are rewritten afterwards. Name the step that rewrites them.
35. The installer will run on a machine with no network. Read the package list
    and say plainly which packages come from the ISO and which would need a
    network. Do not guess — cite the list.
36. Remove or justify `ubiquity` in `packages.conf`. A dead package name in an
    installer list is a slow failure; state your verdict.
37. Give the installer a slide/showcase page that shows Meta's four systems and
    says what they are, with no claim that cannot be checked offline.
38. Check the installer's default user/session/autologin: it must produce the
    same `meta` / `metaos` session the image ships, not a generic desktop.
39. Verify every asset the branding references exists in your tree, with
    `test -f`, pasted.
40. Write `os-build/iso/calamares/README.md`: what the installer does, in what
    order, and what a judge can verify without installing.
41. Add a static check that walks `calamares/` and fails on any Ubuntu string
    outside a documented allowlist comment.
42. Run it and paste the result.

### E. Proof and handoff (43–50)

43. Write `os-build/lanes/AGENT_OS_2_REPORT.md`: inventory table, changes,
    proofs, requests, and the list of files you deliberately left alone.
44. State plainly which of your three surfaces is verified by parsing only and
    which would need a boot to confirm. Never claim a boot proof you did not do.
45. Name the single most likely way your work breaks the demo, and how someone
    can see it in ten seconds without booting.
46. List every file another lane must change for your work to take effect, and
    the exact line, as a request.
47. Confirm `sh -n` passes on every shell file you touched.
48. Confirm no absolute `/Users/` path, no secret, no hostname leaked into your
    files.
49. List your commits (hash + subject) and confirm nothing landed on `main`.
50. Confirm you ran no QEMU, mounted nothing, installed nothing, and left no
    temp file under the repo tree.

---

## Definition of done

- One canonical plymouth theme, no Ubuntu fallback reachable, every referenced
  asset present, art-free fallback documented.
- Boot menu entries read Meta OS, default is the Meta entry, plugin/assets
  verified.
- Installer branding is Meta everywhere, `ID_LIKE=debian`, no dead package
  names, and a judge can verify it with greps you supply.
- A report that separates "proven by parsing" from "would need a boot".
