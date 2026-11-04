# AGENT OS-3 — User session, defaults and the Ubuntu that lives in userland

**Branch:** `agent-os-3`
**Worktree:** `git worktree add /tmp/agent-os-3 -b agent-os-3 main`

Read this whole file before your first command.

---

## Mission

After the boot screens, the base image's name survives in the small places a
person actually meets: the shell prompt, the terminal font, the app launcher's
allowed list, the `.desktop` files, the fonts, the default handlers, the skeleton
home directory. You own that layer.

This is the layer where "it says Ubuntu" gets reported as a bug and the fix is
one string in one file. Your value is finding **all** of them once, and leaving a
check behind so the next one is caught mechanically.

---

## HARD RULES — breaking one of these fails the lane

1. **Never run QEMU.** No boot, no `show_os.sh`, no `proof_boot.sh`.
2. **No sudo, no mount, no docker, no `apt`, no `fc-cache` on the host.**
   You can run `fc-match`/`fc-list` only if they already exist on this machine.
3. **Never touch another lane's paths.** Yours are below.
4. **Never edit these — they are Buffy's while the desktop is rewritten:**
   `os-build/face/meta-desktop.sh`, `os-build/face/session.sh`,
   `os-build/face/provision.sh`, `os-build/face/kiosk.sh`,
   `os-build/iso/payload-theme/gtk/**`, `os-build/iso/payload-theme/xfwm4/**`,
   `os-build/iso/payload-theme/dock/**`, `os-build/iso/payload-theme/panel/**`,
   `os-build/iso/payload-theme/icons/**`,
   `os-build/iso/payload-theme/wallpapers/**`, `face/**`.
   If a change is needed there, write the exact diff in your report.
5. **No renaming of installed binaries.** You may change what a `.desktop`
   *launches*, not what the system has installed.
6. Commit only your files, only on `agent-os-3`. No merge, no rebase, no push.

---

## You own these paths (and only these)

```
os-build/iso/payload-theme/terminal/**
os-build/iso/payload-theme/fonts/**
os-build/iso/payload-theme/apps/**
os-build/iso/payload-theme/identity/**        (only if OS-1 asks, see note)
metaos-theme/terminal/**
metaos-theme/fonts/**
metaos-theme/apps/**
os-build/face/launcher.py
agent-layer/desktop-entries/**
os-build/lanes/AGENT_OS_3_REPORT.md           (new file, yours)
```

Note on `identity/`: OS-1 owns the canonical identity values. Do **not** edit
`os-build/iso/payload-theme/identity/**` unless your task list says so
explicitly; report the need instead.

---

## The identity contract (agreed, do not contradict)

`PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `NAME="Meta OS"`, `ID=metaos`,
`ID_LIKE=debian`, hostname `metaos`, login user `meta`, product name `Meta OS`.
Terminal prompt: blue `metaos`, then the working directory. No `ubuntu@`.

---

## Tasks

### A. Inventory before edits (1–8)

1. Read `os-build/iso/payload-theme/terminal/metaos-terminal-profile.txt` fully.
   List every Ubuntu-named thing in it: font, colours, comments.
2. Read `os-build/face/launcher.py` fully. List every app name it allows and
   what binary each maps to. Mark the ones that are Ubuntu-specific
   (`snap`, `ubuntu-*`, `snap-store`, `firefox` as a snap, etc.).
3. List every `.desktop` file in `agent-layer/desktop-entries/` with its `Name`,
   `Exec`, `Icon`, and say what a person sees in the menu.
4. List every font reference in your paths: `Ubuntu Mono`, `Ubuntu`, `Ubuntu
   Light`, `Ubuntu Condensed`. For each, what breaks if it is not installed?
5. List the fonts that *are* installed in the image as far as the tree can
   tell (the font packages the build installs). If you cannot tell, say so —
   do not guess.
6. `git grep -in "ubuntu"` inside your paths, bucketed: identity leak / honest
   attribution / dead comment / compatibility.
7. Write the four tables from 1–6 into your report as the baseline.
8. Name the three that a judge would notice in the first minute. Those get
   fixed first.

### B. The terminal (9–18)

9. Replace `Ubuntu Mono` with a font that exists in the image. If nothing
   mono-ish is installed, say so and pick the documented fallback rather than a
   name that will silently fail.
10. Write the terminal profile so it is complete and self-consistent:
    foreground, background, palette, cursor, scrollback, font, font size.
11. Put one comment at the top of the profile that says what it is for and what
    reads it. No file in this tree should be a mystery.
12. Make the profile match the reference desktop's terminal look where the
    values are known (dark background, light text). Do not invent colours.
13. Check the prompt: it must read `metaos`, not `ubuntu@host`. Show the file,
    the line, and the exact rendered string (colour codes spelled out).
14. If the prompt is set by a file you do not own, report the exact line.
15. Find any `bashrc`, `profile`, `inputrc` or `dircolors` in your paths with
    Ubuntu strings. List them; fix the ones you own.
16. Confirm the terminal profile cannot print a URL or a claim that is false.
    Read it as a judge would and say what it asserts.
17. Write `os-build/iso/payload-theme/terminal/README.md`: install path, what
    reads it, what happens when it is missing.
18. Prove the profile parses as a key/value file: small script, no python
    packages, prints duplicate keys and unknown keys. Run it, paste output.

### C. Launcher allowlist (19–30)

19. For each app `launcher.py` allows, find out from the tree whether the
    binary is actually installed by this build. Table: app, binary, installed?,
    evidence.
20. Replace every Ubuntu-only launcher entry with the Meta/image equivalent, or
    remove the entry entirely. Removal is better than a tile that fails.
21. Keep the refusal behaviour: unknown app → `403`, not a silent no-op. Read
    the code, confirm it, and say where.
22. Make the error message name the app and the reason
    (`not installed on this image: <binary>`). No bare 500s.
23. Add `GET /apps` output that lists *what is actually launchable* on the
    running image, computed, not hard-coded twice.
24. Make sure `/apps` cannot lie: if the binary check fails, the app is not
    listed.
25. Do not change the wire format the pages already use. Read the pages first,
    then say what the format is.
26. Prove the allowlist logic with a fake `PATH`: a temp directory containing a
    stub binary for each app, and one missing. Show the four outcomes.
27. Write that test as a runnable script under your paths, with a `--check`
    mode, and run it.
28. Confirm nothing in the launcher shells out with an unquoted path.
29. Confirm the launcher has no command that could be reached from a browser
    with `;`, `|`, `$()` or `&&` — read the handler and state it plainly.
30. List the apps that are installed but not launchable, and the reverse.

### D. Desktop entries and defaults (31–40)

31. Every `.desktop` in `agent-layer/desktop-entries/`: `Name` must be Meta's
    name for the app, `Comment` must describe what it does, `Icon` must point at
    an icon that exists. Verify each `Icon=` with `test -f` (paste).
32. Fill in the entries that have no `Comment` and the ones whose comment is
    the base image's text.
33. Make sure no `.desktop` has `Exec=` pointing at a path that does not exist
    in the image. Table: file, Exec, exists?.
34. Set `Categories=` so the apps sort into sensible menu groups, and list the
    resulting groups.
35. Remove `.desktop` entries for apps that are not installed. A menu entry
    that launches nothing is a demo failure.
36. Check `Terminal=true/false` matches what the app actually needs.
37. Check the MIME defaults if any live in your paths: which app opens text,
    folders, images. Name the file that decides it.
38. Write `os-build/iso/payload-theme/apps/README.md`: what each app is, one
    line, no marketing.
39. Add a checker `check_entries.sh` that validates every `.desktop` for the
    four required keys, an existing `Icon`, and no banned words. Run it.
40. Prove the checker fails on a deliberately broken fixture, then passes on the
    real tree. Paste both.

### E. Fonts (41–45)

41. For every font name you or the tree references, answer: is it in the image?
    Cite the package or the file you checked.
42. If a referenced font is missing, either reference an installed one, or ship
    the font file *only* if a licence file is included and the licence allows
    redistribution. If you cannot confirm the licence, do not ship it.
43. Write `os-build/iso/payload-theme/fonts/FONTS.md` honestly: installed,
    referenced, missing, and what the UI falls back to.
44. Confirm no font you reference is used in a way that makes text unreadable if
    it is absent (state the fallback chain).
45. Check the font name spelling everywhere; a typo means a silent fallback.

### F. Proof and handoff (46–50)

46. Write `os-build/lanes/AGENT_OS_3_REPORT.md`: baseline tables, changes,
    transcripts, requests for other lanes, and the three judge-visible items
    from task 8.
47. State which of your changes are proven by running something and which are
    proven only by reading. Do not blur the line.
48. List every change another lane must make for your work to take effect, with
    the exact line.
49. Confirm `sh -n`/`python3 -m py_compile` passes on every script you touched.
50. Confirm you ran no QEMU, mounted nothing, installed nothing, and left no
    temp file under the repo tree. List your commits.

---

## Definition of done

- No `ubuntu` in the terminal profile, the entries, or the launcher's messages.
- Every `Icon=` and `Exec=` you ship resolves in the tree, proven by a check you
  wrote and ran.
- `/apps` reports the computed truth, and the refusal paths still refuse loudly.
- Report separates "ran and saw" from "read and believe".
