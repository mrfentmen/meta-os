# AGENT OS-1 — Identity, naming and the Ubuntu-to-Meta sweep

**Branch:** `agent-os-1`
**Worktree:** create your own, never work in the shared checkout:
`git worktree add /tmp/agent-os-1 -b agent-os-1 main`

Read this whole file before your first command.

---

## Mission

The image still says Ubuntu in places a person can see. Your job is to make the
OS *read* as Meta everywhere, without breaking a single package operation.
Those are two different things and the repo already treats them as two:
**identity** is what a human reads, **compatibility** is what apt reads. You
rewrite the first and you never touch the second.

You are also the lane that makes "debranded" a measurement instead of a claim,
because a grep that nobody runs is not a check.

---

## HARD RULES — breaking one of these fails the lane

1. **Never run QEMU.** Not `show_os.sh`, not `proof_boot.sh`, not
   `frames_boot.sh`, not a raw `qemu-system-*`. The machine must stay quiet.
   See `plan/AGENT_OS_INDEX.md` for why.
2. **No booting, no mounting the image, no sudo, no docker.** If a task needs a
   boot to prove itself, you must prove it another way (staged temp root,
   static parse, diff against a fixture). Say so in your report.
3. **Never touch another lane's paths.** The full list of what is yours is
   below; everything else is off limits, including `os-build/face/`.
4. **Never edit `os-build/face/provision.sh` or `os-build/face/meta-desktop.sh`.**
   Buffy owns both while the native desktop is rewritten. If you need a line in
   them, write the line in your report as a request.
5. **No `ID_LIKE` changes.** `ID_LIKE=debian` stays. Removing it breaks apt,
   systemd and every Debian assumption in the image.
6. **No package renames.** `ubuntu-keyring`, `ubuntu-minimal` and friends stay
   installed. They are compatibility, not identity.
7. Commit only your own files, only on `agent-os-1`. **No merge, no rebase, no
   push.** One commit per completed group of tasks, named for the group.

---

## The identity contract (other lanes read this; do not contradict it)

| Thing | Value |
|---|---|
| `PRETTY_NAME` | `Meta OS 1.0 (Ribbon)` |
| `NAME` | `Meta OS` |
| `VERSION` | `1.0 (Ribbon)` |
| `VERSION_ID` | `1.0` |
| `VERSION_CODENAME` | `ribbon` |
| `ID` | `metaos` |
| `ID_LIKE` | `debian` (never `ubuntu`) |
| hostname | `metaos` |
| login user | `meta` |
| product name in UI | `Meta OS` |

If a file disagrees with this table, the file is wrong.

---

## You own these paths (and only these)

```
os-build/identity/**
os-build/iso/payload-theme/identity/**
plan/AGENT_OS_1.md                     (your notes at the bottom)
os-build/lanes/AGENT_OS_1_REPORT.md    (your report — new file)
```

You may also **create** new files under `os-build/identity/`. You may not create
files anywhere else.

---

## Tasks

Work top to bottom. Tick each in your report. If one cannot be done, write the
reason and move on — a skipped task with a reason is worth more than a fake tick.

### A. Read the ground truth first (1–6)

1. Read `os-build/identity/debrand.sh` end to end. List every file it rewrites
   and every file it deliberately leaves alone, with the reason.
2. Read `os-build/identity/debrand2.sh`. State in one paragraph what it does
   that `debrand.sh` does not, and whether it is still needed.
3. Read `os-build/identity/rename_user.sh`. Note what it assumes about the
   existing user, and whether it is safe on a root that has never been booted.
4. Run `git grep -il ubuntu` and bucket every hit into: (a) identity, (b)
   compatibility, (c) comment that names the base image honestly, (d) stale
   generated output. Counts per bucket in your report.
5. Find every place the string `Xubuntu` or `xubuntu` appears outside `plan/`
   and `os-build/logs/`. Decide whether each is honest attribution or a leak.
6. Write the buckets into `os-build/identity/STRINGS_INVENTORY.md` with a line
   per hit and its verdict.

### B. One debrand script, not two (7–14)

7. Decide the survivor between `debrand.sh` and `debrand2.sh`. State the
   decision and the reason in your report. Do not delete the loser yet — first
   prove nothing calls it (`git grep` the filename).
8. Fold any unique behaviour of the loser into the survivor.
9. Give the survivor three modes: `--apply`, `--check`, `--json`.
   `--json` prints one object per file: path, expected, actual, pass.
10. Make `--check` exit non-zero when anything fails, and print `PASS`/`FAIL`
    per file. No file is allowed to fail silently.
11. Make `--apply` idempotent: running it twice must produce byte-identical
    files and the second run must report zero changes made.
12. Add a `--root DIR` flag and keep the positional form working, so old
    callers in build scripts do not break.
13. Stage a fake root under `/tmp/fakeroot-1` with the real file shapes
    (`etc/os-release` as a regular file, `etc/lsb-release`, `etc/issue`,
    `etc/issue.net`, `usr/lib/os-release` as a symlink target) and prove
    apply → check → PASS, then check a copy with Ubuntu values → FAIL.
14. Prove the symlink case specifically: `/etc/os-release → ../usr/lib/os-release`
    must not be replaced by a regular file. Show the `ls -l` before and after.

### C. The allowlist, so the sweep can be a test (15–24)

15. Create `os-build/identity/ALLOWLIST.tsv`. **This is a contract file — other
    lanes read it, so the format is fixed:** tab-separated
    `path<TAB>pattern<TAB>verdict<TAB>reason`. Verdict is one of
    `compat`, `attribution`, `generated`.
16. Seed it with every compatibility hit from task 4 (apt sources, package
    names, `ID_LIKE`), every honest attribution (a comment naming the Xubuntu
    base ISO), and every generated file under `os-build/logs/`.
17. Write `os-build/identity/check_strings.sh`: greps the tree for the banned
    words, subtracts the allowlist, prints one line per surviving hit, exits 1
    if any survive.
18. Banned words: `ubuntu`, `Ubuntu`, `Xubuntu`, `xubuntu`, `canonical`,
    `Canonical`. Each may need a separate verdict; do not collapse them.
19. Make `check_strings.sh` accept `--explain`: for each hit it prints which
    allowlist row suppressed it, or why it did not.
20. Scope the grep so it never reports inside `.git`, `node_modules`,
    `os-build/logs/`, `plan/`, or binary files. State the exclusions in a
    comment and in `--help`.
21. Handle the case where `git grep` is unavailable (the guest may not have a
    checkout): fall back to `find` + `grep`.
22. Prove the checker fails: add a temporary file containing `ubuntu` outside
    the allowlist, run it, show exit 1 and the hit, then delete the file.
23. Prove the checker passes on the clean tree: show exit 0.
24. Prove the checker is not vacuous: temporarily add an allowlist row that
    should not match, show it does nothing, then remove it.

### D. Places the sweep will actually find things (25–36)

25. `/etc/lsb-release` — confirm the debrand script writes Meta values and that
    `lsb_release -a` would read them. Show the file content you install.
26. `/etc/issue` and `/etc/issue.net` — no Ubuntu, and no escape sequences that
    print a hostname nobody set.
27. The motd directory: list every script in `/etc/update-motd.d/` that prints
    Ubuntu branding, and write the Meta replacement (a plain, honest 3-line
    banner: product, version, where to read the truth).
28. Remove or rewrite the motd scripts that print Ubuntu's "help" URLs. Keep
    the security-update notice — that one is real information.
29. `python3 -c 'import platform; platform.dist()'` style lookups: find any code
    in the shipped tree that reads distro identity and would print Ubuntu.
    List each with its file and line.
30. `distro.id()` / `/etc/lsb-release` consumers in `os-build/face/*.py` and
    `os-build/iso/payload-apps/**`: report them for the owning lane, do not
    edit the files.
31. Confirm `hostnamectl` would print `Meta OS` and not `Ubuntu`: trace which
    files it reads and show each one.
32. Check `/etc/hosts`, `/etc/hostname` and the `127.0.1.1` line for leftovers.
33. Check the GECOS field of the `meta` user: a `chfn`-visible "Ubuntu" is still
    Ubuntu in the About screen and in `who`. Write the exact `usermod -c`
    command that fixes it, and check it in `--check` from now on.
34. Check every `/etc/skel` file that shows identity in a prompt or banner and
    list the ones your lane may not edit (they belong to OS-3).
35. Write `os-build/identity/IDENTITY_MATRIX.md`: one row per identity surface
    (os-release, lsb-release, issue, motd, hostname, GECOS, greeter, login
    banner, About page, terminal prompt) with the file that owns it, the lane
    that owns it, and PASS/FAIL today.
36. In that matrix, mark the rows owned by other lanes as `not mine` — do not
    fix them, just name them.

### E. Proof that survives a judge (37–45)

37. Write `os-build/identity/README.md` aimed at a judge: what identity is,
    what compatibility is, why `ID_LIKE=debian` stays, and how to run the
    checker in one command.
38. Put the exact command and its exact output in the README. Real output, not
    a paraphrase.
39. Add a `make`-free entry point: `sh os-build/identity/check_strings.sh` must
    work from the repo root with no arguments and no environment.
40. Time it. Record the wall-clock time in the README.
41. Prove it works from a different working directory (`cd /tmp && sh
    /path/to/check_strings.sh`), because the build calls it that way.
42. Write a shell test `os-build/identity/test_check_strings.sh` that builds
    three fixtures (clean, one banned word, one allowlisted word) and asserts
    exit 0 / 1 / 0. It must create its fixtures in `mktemp -d` and clean up.
43. Run it. Paste the transcript.
44. Confirm no file you created contains a real secret, hostname of a real
    machine, or an absolute path under `/Users/`.
45. Confirm `sh -n` passes on every shell file you touched.

### F. Handoff (46–50)

46. Write `os-build/lanes/AGENT_OS_1_REPORT.md`: what you changed, what you
    proved, what you could not, and every request for another lane.
47. In the report, list every file you did **not** touch but that still prints
    Ubuntu, with the lane that owns it. This is the most useful section.
48. State plainly whether the image would now pass `check_strings.sh` as-is, or
    whether the hits live in files you do not own. Do not overstate.
49. List your commits (hash + subject) and confirm nothing landed on `main`.
50. Confirm you ran no QEMU, mounted nothing, and left no temp file under the
    repo tree.

---

## Definition of done

- `sh os-build/identity/check_strings.sh` gives a real, explainable verdict on
  the current tree and exits 0 or 1 truthfully.
- `--apply` then `--check` passes on a staged fake root, twice in a row.
- `ALLOWLIST.tsv` exists, is tab-separated, and every row has a reason.
- `IDENTITY_MATRIX.md` names an owner for every identity surface.
- Your report names the leftovers you could not fix and who owns them.
