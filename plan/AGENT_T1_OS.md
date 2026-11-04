# Agent T1 lane: OS identity, boot surface, installer

Read this whole file before touching anything. Work on branch `agent-t1`.
Commit there. Do not merge. Do not push.

## Mission

The image boots and works. It still carries Ubuntu's name in places a judge
can reach in two clicks: the boot splash, the login greeter, GRUB, the
installer, and a second `os-release` writer that overwrites the first one.
Your lane makes one source of truth for identity and proves the rest of the
surface follows it.

## Owned paths (only these)

- `os-build/identity/`
- `os-build/iso/payload-theme/plymouth/`
- `os-build/iso/payload-theme/grub/`
- `os-build/iso/payload-theme/lightdm/`
- `os-build/iso/payload-theme/apply.sh`
- `os-build/metaos1-base/dexubuntu/`
- `os-build/iso/provision.sh`, `os-build/iso/provision-all.sh`
- `os-build/calamares/`
- `os-build/iso/plymouth/`, `os-build/iso/splash/`, `os-build/iso/grub-fix.sh`
- `os-build/lanes/T1_REPORT.md` (yours to write)

Anything else, request it in your report. Do not edit `os-build/face/`, the
`trio/` pages, `agents/`, `agent-layer/`, or `server/`.

## Rules

- No QEMU. Not with a flag, not "just to check". Use staged roots, `debugfs`
  reads of `/tmp/metaos.ext4`, and static traces.
- No `sudo`, no `mount`, no docker without saying so in the report. If a step
  needs root on the host, stop and write it down.
- Every claim needs a command and its output pasted in the report. "Should
  work" is not a result.
- Use subagents. Split the sections below across at least three, then have one
  read their diffs against this file. A subagent may only touch files in the
  section it was given.

## Section A. One writer for identity (1-18)

1. List every file in the tree that writes `/etc/os-release` or a copy of it. Print the paths.
2. Find which one wins on the install media, in order, and prove the order from the scripts.
3. Make `os-release` have a single writer. Delete or gate the other writers.
4. Make `ID_LIKE` stop saying `ubuntu` on the shipped image. Justify the value you pick.
5. Set `NAME`, `PRETTY_NAME`, `VERSION`, `VERSION_ID`, `HOME_URL`, `BUG_REPORT_URL`, `DOCUMENTATION_URL`, `SUPPORT_URL` to Meta values.
6. Set `ID=metaos` and make every reader of `ID` still work. Grep for readers first.
7. Add `VERSION_CODENAME` that matches the product name, not Ubuntu's.
8. Prove `debrand.sh --check` passes on a staged root after your change.
9. Prove a second `debrand.sh --apply` changes zero bytes.
10. Run `check_strings.sh` and cut the failure count to zero for the words your lane owns.
11. Handle the `/etc/os-release` symlink to `../usr/lib/os-release` without breaking it.
12. Add a test that fails if two scripts write `os-release`. Put it next to the identity scripts.
13. Add the same for `lsb-release`, `/etc/issue`, `/etc/issue.net`, and `/etc/motd`.
14. Make `/etc/hostname` and `/etc/hosts` say `metaos` and survive a reinstall.
15. Rename the default user everywhere it is created, not just in the skel.
16. Update GECOS for that user so `finger` and the greeter stop showing `Ubuntu`.
17. Check `getent passwd` output after your rename on a staged root and paste it.
18. Write down every place the string `ubuntu` still appears after this section, with the reason it stays.

## Section B. Boot splash (19-36)

19. Read the shipped plymouth theme and name the file that actually renders.
20. Replace the Ubuntu logo animation with the Meta mark, frame for frame.
21. Keep the splash under 40 frames of decode so boot is not slower.
22. Prove the theme references only files that exist in the payload.
23. Set the default theme in the plymouth config, and prove no `ubuntu-logo` reference remains.
24. Make the splash text read `Meta OS` and `Starting`.
25. Remove the purple field. Match the desktop's ink colour and paste the hex you used.
26. Make the password prompt in the greeter theme use the Meta colours.
27. Check the theme at 1920x1080 and at 1366x768 by rendering the PNGs at both sizes.
28. Make the progress dots consistent with the dock's active indicator.
29. Handle the `text` plugin fallback: a console boot must still say `Meta OS`.
30. Wire the theme into the initramfs rebuild path and prove the config survives it.
31. Confirm the splash is not shown twice on shutdown. If it is, fix the shutdown path.
32. Time the splash to the session start and record the delta.
33. Make the theme's background match the wallpaper's darkest pixel. Sample it and paste the value.
34. Remove `plymouth-theme-ubuntu-logo` from any manifest that still installs it.
35. Add a check script that fails if the plymouth payload names an Ubuntu file.
36. Add the theme build step to `provision-all.sh` so a fresh image gets it.

## Section C. GRUB (37-52)

37. Dump every menu entry on the built ISO tree and paste it.
38. Make the top entry read `Meta OS` with a version that matches `os-release`.
39. Remove `Ubuntu` from every entry title, including recovery entries.
40. Change the distributor string that `grub-mkconfig` writes.
41. Set the default entry by name or id so a kernel update cannot reorder it.
42. Set the colour palette to the desktop's ink and paper values.
43. Choose a timeout that lets a demo boot without waiting and still allows recovery.
44. Add a recovery entry that says what it does, in Meta's words.
45. Remove `quiet splash` from the recovery entry so it prints.
46. Make the advanced submenu show kernels without the Ubuntu codename.
47. Prove `grub-fix.sh` is idempotent by running it twice and diffing.
48. Make sure the GRUB theme file, if any, points at files that exist.
49. Check the ISO's `boot/grub/grub.cfg` after `build_iso.sh --tree-only`.
50. Add a check that fails when `Ubuntu` appears in the generated grub.cfg.
51. Record the font used for the menu and confirm the payload carries it.
52. Document how to change the menu title in one place, for the next person.

## Section D. Greeter and session (53-74)

53. Read the lightdm drop-in and list every Ubuntu string in it.
54. Replace the greeter background with the Meta wallpaper or its solid tone.
55. Make the greeter's session name read `Meta OS`, not `Xubuntu`.
56. Keep autologin working. Prove the config that enables it after your change.
57. Make sure the greeter does not fall back to a stock session when Meta's is missing. It should fail loudly.
58. Remove the guest session if it exists.
59. Set the greeter's clock format to match the desktop.
60. Hide the user list if the demo runs with one account, and say why.
61. Make the greeter's font the same family as the desktop's interface font.
62. Check that the greeter and the session use the same cursor theme.
63. Prove the session file that lightdm loads is the Meta session, by path.
64. Check the session's `.desktop` name and comment for Ubuntu words.
65. Make the greeter show the machine name `metaos`, not a hostname from the base image.
66. Add a check that fails if the greeter config names an Ubuntu theme.
67. Confirm the greeter does not start a second panel or dock.
68. Handle a failed session start: it must land on a visible error, not a black screen.
69. Read `/var/log/lightdm` from the image if present and paste anything that failed.
70. Set the keyboard layout explicitly and record the value.
71. Set the locale explicitly so the greeter does not inherit the host's.
72. Remove the Ubuntu logo from the greeter's logo slot, or replace it with the Meta mark.
73. Confirm the greeter theme's assets are all in the payload.
74. Write the exact steps to change the greeter background in the report.

## Section E. Installer (75-98)

75. Read the Calamares config and list every Ubuntu string a user sees.
76. Make the installer title and window name say Meta OS.
77. Set the product name on the branding page and prove it comes from one file.
78. Make the slideshow images Meta's. Name every file the config references.
79. Make the "about" text in the installer true. No invented features.
80. Set the default hostname to `metaos`.
81. Set the default username policy and confirm it does not create `ubuntu`.
82. Remove the Ubuntu release notes link from the installer.
83. Set the installer's palette to the desktop's colours.
84. Check the partition page's warning text for a stock Ubuntu phrase and rewrite it in Meta's voice.
85. Make the finish page offer a reboot only, or say plainly what each button does.
86. Confirm the installer's package list has no Ubuntu desktop metapackage.
87. Confirm the installer copies the Meta identity files and does not then overwrite them.
88. Prove that order by tracing the shell commands the installer runs.
89. Add a post-install check that reads `/etc/os-release` and fails on `Ubuntu`.
90. Check the installer's icon set. Replace the Ubuntu logo wherever it appears.
91. Make the installer's license page honest: what is GPL, what is Meta's.
92. Set the installer's timezone default to the demo's city, and say which.
93. Remove any `ubuntu` user from the installer's test fixtures.
94. Check the Calamares QML for a hardcoded `Ubuntu` string. There is at least one.
95. Make the slideshow not claim features the image lacks. Read `BOOT_READINESS.md` first.
96. Add a dry-run target that validates the Calamares config without launching it.
97. Record every installer string you could not change, and why.
98. Write the installer section of the report with the file and line of each change.

## Section F. Package and manifest surface (99-120)

99. List every installed package whose name starts with `ubuntu`, `xubuntu`, or `lubuntu`.
100. For each, decide: keep, replace, or remove. Write the decision in a table.
101. Remove the ones that only supply branding, and prove nothing needs them.
102. Replace `ubuntu-mono` fonts if the desktop is not using them. Check before removing.
103. Find where `lsb_release` output is used and make it read Meta values.
104. Check `hostnamectl` output on a staged root. It must not say Ubuntu.
105. Check `neofetch` or `fastfetch` if installed, and its ASCII art.
106. Make the terminal's default shell prompt read `metaos`. Do not change the user's PS1 if it is theirs.
107. Check the MOTD for Ubuntu lines and replace them.
108. Check `/etc/update-motd.d/` scripts. Disable the ones that advertise Ubuntu.
109. Check the apt sources file names and the comment text at the top.
110. Make sure apt's `Origin` and `Label` do not print Ubuntu in `apt-cache policy` for the demo's packages.
111. Check the GRUB package's distributor hook and whether it rewrites your title.
112. Check the snap store branding in the image, if snaps are installed.
113. Check `dpkg --print-architecture` and the manifest for a mismatch, and report it.
114. Add a manifest check that fails on an Ubuntu desktop metapackage.
115. Record the total image size before and after your removals.
116. Make sure nothing you removed was the only provider of a binary the dock calls.
117. Check the file manager's "About" dialog strings.
118. Check the settings manager's "About this system" values.
119. Check the text editor's default template or welcome text.
120. Write the package table into the report with sizes.

## Section G. Proof and reporting (121-150)

121. Write `os-build/lanes/T1_REPORT.md` with a section per section above.
122. Every claim gets the command and the first and last line of its output.
123. Stage a clean root and run the whole identity check chain on it. Paste the summary.
124. Run the same chain on a root that still has an Ubuntu `os-release`. It must fail. Paste it.
125. Plant a file containing `Ubuntu` in a path your checker scans. It must fail. Delete it after.
126. Run every script you edited with `sh -n` or `bash -n`. Paste the clean result.
127. Run every Python file you edited through `python3 -m py_compile`.
128. List every file you changed with `git diff --stat` on your branch.
129. Confirm no file outside your owned paths appears in that diff.
130. Confirm no QEMU process is running after your work. Paste `pgrep -f qemu-system`.
131. Confirm no mount is left behind. Paste `mount | grep metaos`.
132. Write the one-paragraph answer to "is this image Ubuntu with a skin?" using only what you proved.
133. Name the three remaining places a judge could find Ubuntu, if any.
134. Name the single change that would remove the most of them.
135. Record the boot-time delta of your splash change, or say you could not measure it.
136. Record the image size delta of your package removals.
137. Check the ISO still builds with `--tree-only` after your changes. Paste the file count.
138. Confirm the tree has no broken symlinks after your changes.
139. Confirm no file you touched hardcodes `/home/ubuntu`.
140. Confirm no file you touched hardcodes an absolute host path.
141. Make sure the identity scripts still run on macOS, since that is where they are edited. Paste the run.
142. Fix anything in your lane that only works on Linux.
143. Write the exact commands the next agent needs to verify your lane in one copy-paste block.
144. Note every cross-lane request with the file, the line, and what you need from the owner.
145. Do not fix cross-lane files yourself, even when the fix is one line.
146. Check your commits are on `agent-t1` and only `agent-t1`. Paste `git branch --show-current`.
147. Confirm `main` is untouched by you. Paste the `git log --oneline -3 main`.
148. Summarise what a judge would see differently on boot after your lane.
149. List what you could not verify without booting, honestly, and why each matters.
150. End the report with the next three tasks you would do if you had another session.
