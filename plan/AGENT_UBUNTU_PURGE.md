# Agent lane: purge the Ubuntu that is still in the image (not the repo)

Paste this whole file to the agent. Work on branch `agent-ubuntu-purge` in a
worktree. Commit there. **Do not merge. Do not push. Do not boot QEMU.** Do not
modify `/tmp/metaos.ext4` — that is the demo image and it is being filmed.
Work on a copy (`/tmp/ubuntu-purge.img`) made with `cp --sparse=always`.

Use subagents: six lanes below, each with its own verifier. A lane that cannot
prove its claim with pasted output is a failed lane — say what you could not
prove instead of asserting it.

## What the scan found (evidence, measured on the current image)

The repo is mostly clean; the leftovers are at the **package and system-art
layer**. A run of `os-build/identity/check_strings.sh` returns **62 hits**, but
those are almost all lane reports and comments documenting the de-Ubuntu work —
triage them, do not assume they are leaks. What is actually still Ubuntu:

| # | Finding | Where | Evidence |
|---|---|---|---|
| 1 | `apport` installed, service **enabled**, crash reporter | `/etc/systemd/system/multi-user.target.wants/apport.service`, `/etc/default/apport` `enabled=1` | `dpkg` list + unit symlink |
| 2 | `ubuntu-bug` binary shipped | `/usr/bin/ubuntu-bug` | `ls` |
| 3 | `whoopsie` installed, `.path` unit enabled, uploads crash data to Canonical | `/etc/systemd/system/multi-user.target.wants/whoopsie.path` | unit symlink |
| 4 | Ubuntu icon themes: `ubuntu-mono-dark` 5.0M, `ubuntu-mono-light` 6.0M, `Humanity` 18M, `Humanity-Dark` 2.4M | `/usr/share/icons/` | `du -sh` |
| 5 | Ubuntu font family installed and resolvable | `/usr/share/fonts/truetype/ubuntu/Ubuntu-*.ttf` | `ls` |
| 6 | Ubuntu logos on disk | `/usr/share/pixmaps/ubuntu-logo.svg`, `ubuntu-logo-text.png`, `ubuntu-logo-text-dark.png` | `ls` |
| 7 | Ubuntu Software / snap-store handler | `/usr/share/applications/gnome-mimeapps.list:31` → `snap-store_ubuntu-software.desktop` | grep |
| 8 | Canonical's "This system has been minimized…" printed at every login | `/etc/update-motd.d/60-unminimize` | file text |
| 9 | apt points at Ubuntu ports mirror | `/etc/apt/sources.list.d/ubuntu.sources`, `ports.ubuntu.com` | grep |
| 10 | Ubuntu-named greeter fallback path kept alive | `/usr/share/backgrounds/warty-final-ubuntu.png` (content is Meta art) | `ls` |
| 11 | `verify_tree.sh` "no-ubuntu" row FAILs by design (28-file baseline) | `os-build/tools/verify_tree.sh` row 6 | run it |
| 12 | `check_strings.sh` FAILs with 62 unsuppressed hits | `os-build/identity/` | run it |

`ID=metaos`, `ID_LIKE=debian` — identity is already right; do not touch
`os-release` values. `snapd`, `cloud-init`, `casper`, `subiquity`,
`ubuntu-desktop`, `ubuntu-advantage` are **not** installed; do not invent work
for them.

## Hard rules

1. **Never remove something without proving what needs it.** `dpkg -S <path>`
   and `apt-get -s remove` (simulate, inside the mounted copy) before any
   deletion. A removed icon theme that was the fallback for the panel is a
   visible regression, not a win.
2. **Replacement before removal**, always: icon theme → MetaOS then Papirus then
   Adwaita; font → Inter then Noto; logo path → Meta mark; motd → Meta text.
3. `ubuntu-keyring` stays while apt still points at Ubuntu mirrors. Say so in
   the report rather than silently deleting it and breaking `apt update`.
4. No new dependencies, no apt installs of new packages on the host. Inside the
   mounted image copy, `chroot` is allowed (same arch: aarch64 on this Mac).
5. Every claim needs pasted output. "Should work" is a failed task.
6. Own only: `os-build/identity/`, `os-build/face/provision.sh` (the sections you
   add), `os-build/iso/provision.sh`, `os-build/face/motd*` if you create it,
   and your own lane report. Do **not** touch `os-build/iso/payload-theme/tokens/`,
   the trio pages, or anything under `face/*.html` — Buffy owns those.

## Lane A — reporters and phone-home (1–10)

1. `cp --sparse=always /tmp/metaos.ext4 /tmp/ubuntu-purge.img`; record sha256 of both.
2. Mount the copy rw; `dpkg -l | grep -E 'apport|whoopsie'`; paste it.
3. `dpkg -S /usr/bin/ubuntu-bug`; list what depends on apport (`apt-cache rdepends --installed apport`).
4. `apt-get -s purge apport` — paste the full simulation, note every package it would take with it.
5. Same for `whoopsie`.
6. Deciding whether `ubuntu-report`/`popularity-contest`/`landscape-client` exist; if absent, say so once, do not pad.
7. Purge apport + whoopsie on the copy if the simulation is clean; paste the result.
8. Prove no unit still points at them: `ls multi-user.target.wants | grep -E 'apport|whoopsie'` empty, `systemctl` can't be run headless — say so.
9. Prove `/usr/bin/ubuntu-bug` is gone and nothing in `/usr/share/applications` references it.
10. Add all of it to `os-build/face/provision.sh` as a documented block (why: Ubuntu crash/error reporting uploads to Canonical; a demo OS must not have a Canonical upload path). Guard it so a base without those packages still provisions.

## Lane B — icons (11–20)

11. `dpkg -S` each of the four Ubuntu icon dirs; paste which package owns them.
12. `grep -rl "Humanity\|ubuntu-mono" /etc/xdg /usr/share/themes/MetaOS /opt/face /etc/skel` — every live reference.
13. Confirm the active icon theme chain: `gsettings get org.gnome.desktop.interface icon-theme`, GTK `gtk-icon-theme-name`, panel/dock settings, and `index.theme` inheritance in MetaOS.
14. Add an explicit `Inherits=` chain to the MetaOS icon theme so it cannot fall through to Humanity.
15. Prove with `gtk-update-icon-cache`-style resolution or `find` that every icon name the MetaOS theme lacks resolves inside Papirus/Adwaita, not Humanity.
16. Purge `ubuntu-mono-dark`, `ubuntu-mono-light`, `Humanity`, `Humanity-Dark` on the copy if the simulation is clean.
17. Prove the four dirs are gone and `du` of `/usr/share/icons` dropped (paste before/after).
18. Prove `gtk-icon-theme-name` still resolves: list the theme dir the setting names.
19. Screenshot-free proof: `check_desktop.sh`/`check_entries.sh` still pass (they run headless).
20. Add the purge + `Inherits` pin to provision.

## Lane C — fonts (21–28)

21. `fc-list` equivalent inside the copy (`chroot ... fc-list`), filtered for `Ubuntu`; paste family names and files.
22. `fc-match Ubuntu` and `fc-match "Ubuntu Mono"` inside the copy — what an app asking for Ubuntu type actually gets.
23. `grep -rn "Ubuntu" /etc/fonts /usr/share/fontconfig` — any alias that keeps the family alive.
24. Decide: remove `fonts-ubuntu` (Ubuntu Font Licence + branding) or keep it. Whichever, paste the `apt-get -s purge` simulation and the fontconfig substitute that keeps the UI identical.
25. If removing, add `fontconfig` substitution rules so any request for Ubuntu/Ubuntu Mono lands on Inter/Monospace, and prove with `fc-match` **after** the removal.
26. Prove the terminal/panel/GTK still resolve a real face (paste `fc-match` for the three themes' font keys).
27. Keep the `.ttf` count before/after.
28. Land the decision in provision with the reason in a comment.

## Lane D — Ubuntu art and text (29–38)

29. `dpkg -S /usr/share/pixmaps/ubuntu-logo.svg` and the two PNGs; owner package.
30. `grep -rl "ubuntu-logo" /usr/share/applications /etc /opt/face /usr/share/glib-2.0/schemas` — anything that would draw the Ubuntu logo.
31. Replace the three logo paths with the Meta mark (same filenames, our pixels) OR remove them if nothing references them — prove which with task 30.
32. `/etc/update-motd.d/`: read `00-header` and `60-unminimize`; list which scripts are executable.
33. Rewrite `60-unminimize` (or disable it) so a login never prints Canonical's minimized-system text; paste old and new output by running the script directly (`sh /etc/update-motd.d/60-unminimize`).
34. Check `10-help-text` / `50-motd-news` still disabled (`.metaos-disabled` suffix) and that their absence does not leave a blank motd.
35. `grep -ri "ubuntu" /etc/motd /etc/issue /etc/issue.net /etc/lsb-release /etc/legal` — anything a user can cat.
36. `warty-final-ubuntu.png`: prove what reads that path (`grep -r` across `/etc`, `/usr/share/glib-2.0/schemas`, `/opt/face`), then keep-or-replace with the reason. The content is already Meta art; the question is the name and the Ubuntu fallback it represents.
37. `/etc/apt/sources.list.d/ubuntu.sources` + `help.ubuntu.com`: keep the mirror (updates matter for a demo OS) but strip the help URL from any user-visible place; paste what you changed.
38. Add the motd/art work to provision, with a `--check` mode that fails if the Canonical text returns.

## Lane E — repo strings and the gate (39–50)

39. Run `os-build/identity/check_strings.sh`; paste the summary line and the file list.
40. Classify all 62 hits into: (a) lane report/doc, (b) source comment, (c) live code/config, (d) test fixture. Give the counts.
41. For (c) only: name file:line and what a user would see. Fix those.
42. For (a)/(b)/(d): add allowlist rows **with a reason string**, following the existing `ALLOWLIST.tsv` format.
43. Re-run the checker: it must exit 0 with a truthful report; paste it.
44. `check_entries.sh` BANNED list contains `ubuntu xubuntu` — verify it still passes on the tree.
45. Write `os-build/identity/check_no_ubuntu.sh`: a gate that fails if any of these reappear — apport/whoopsie installed, `ubuntu-bug` present, the four icon dirs, `fonts-ubuntu` (unless Lane C kept it, then the gate asserts the substitution instead), the three ubuntu logos, the snap-store mimeapps line, the minimized motd text.
46. Give it `--check` (default, no writes), `--json`, and a self-test with a planted fixture that must fail.
47. Prove the gate: clean tree → exit 0; planted `ubuntu-bug` → exit 1 naming the file; remove the plant → exit 0.
48. Wire it into `os-build/tools/verify_tree.sh` as a row (or say why it cannot be a row there).
49. Run `verify_tree.sh` and paste the table; the "no-ubuntu" row should now report the same 62 → triaged number.
50. `sh -n` every script you touched.

## Lane F — the verifier (51–60)

51. Review the whole diff for out-of-lane edits; list any.
52. Re-run every proof the other lanes pasted, from a clean shell, and paste your own runs.
53. Check no absolute host path leaked into the image (`grep -r "/mnt/img" /tmp/ubuntu-purge.img/etc` style).
54. Confirm the demo image `/tmp/metaos.ext4` sha256 is unchanged by the lane.
55. Confirm zero QEMU processes and no boot attempted (`pgrep -f qemu-system`).
56. Confirm nothing was pushed (`git log origin/main..HEAD` only your branch).
57. Write `os-build/lanes/AGENT_UBUNTU_PURGE_REPORT.md`: per-task pass/fail, the table above with before/after, and a "could not prove" section.
58. List every cross-lane request with file:line (tokens, trio pages, session script, ISO builder).
59. State the honest residual: what Ubuntu remains (the mirror, `ubuntu-keyring`, kernel package names in `dpkg`, `ID_LIKE=debian`) and why each is either required or cosmetic.
60. Final message: one paragraph, what changed, what was proven, what was not.

## Definition of done

`check_no_ubuntu.sh` exits 0 on the tree, exits 1 on a planted leftover, and the
image copy has no Canonical upload path, no Ubuntu icon/font/logo/software
references, and no Canonical login text — each backed by pasted output, with
nothing removed that a `dpkg -S` or `fc-match` shows is still needed.
