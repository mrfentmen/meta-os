# AGENT 4 — prompt (branch: `agent-4`)

Paste this whole file into one opencode session. It is self-contained.

> **Ignore older prompt files.** `plan/AGENT_PROMPTS_R2.md`, `R3.md`, `R4.md`,
> `os-build/lanes/PROMPTS_4AGENTS_2026-11-03.md` and the `A_/B_/C_/D_*_REPORT.md`
> files are from earlier sessions. They are history, not homework. This file is
> the only brief.

---

## The mission (all four agents share this, word for word)

Meta OS is a Meta-branded desktop built on a Debian/Xubuntu base. The kernel,
theme, session, name and apps are ours; the base is not rewritten and we do not
claim it is.

The apps are built but **not all reachable**. Pages exist on disk that no tile
opens, one page (the messaging app) is not even installed on the image, and the
security engine has no screen at all. Your job is to make **every app we built
reachable, working and proven inside the booted OS**, and to remove the last of
Ubuntu's visible identity. Nothing mocked and nothing claimed that you have not
run.

Read `os-build/APP_INVENTORY.md` before you start. It is the map.

**Rules, all agents:**

- Work on branch `agent-4`. Commit there. **Never** merge to `main` — Buffy
  reviews and merges later.
- Commit only the files listed as yours. Everything else belongs to another
  agent working at the same time, right now, in this same checkout.
- No mock code, no stub handlers, no `TODO: implement`, no fake data to make a
  screenshot look right. If something cannot be done, write why and stop.
- Proven = you ran a command and pasted its output. Reading a file is not proof.
- Do not reboot the whole build repeatedly. One boot at the end to check your
  own work.
- Never commit an API key, token, or password.

---

## You own (and only you)

- `os-build/face/about.html` — new page, served on **18900** as
  `/about.html`. **Fixed contract** — agent-1 writes the dock tile against it.
- `os-build/face/session.sh` — the session entry
- `os-build/face/native/meta-app.py` — the app window host
- `os-build/face/meta-live.py` — the animated wallpaper
- `os-build/tools/show_os.sh` — the boot command

## Not yours — do not edit, they will appear

| File / area | Owner |
|---|---|
| `os-build/face/meta-desktop.sh`, `metaos-update.sh`, icons | agent-1 |
| `bus.html`, `surfaces.html`, `logo-studio.html`, `labs/**`, `design/**` | agent-2 |
| `aegis-page/**` | agent-3 |
| `agents/**` (the relay), `aegis/*.mjs` | nobody — read only |
| `kernel/**`, `os-build/identity/**` | nobody |

---

## Your task, in this order

### 1. Prove whether 3D actually draws, and measure it

The Science Lab molecule viewer (`labs/molecules`) and Music 3D
(`labs/music3d`) are three.js scenes, vendored offline. This host's QEMU has
**no `gl=on` and no GTK display backend**, so hardware 3D is impossible on this
machine. The image does ship Mesa `swrast`/`llvmpipe`, so the accepted approach
is **software WebGL**:

- `session.sh` already exports `LIBGL_ALWAYS_SOFTWARE=1`,
  `GALLIUM_DRIVER=llvmpipe`, `WEBKIT_DISABLE_DMABUF_RENDERER=1`.
- `meta-app.py` already sets `enable-webgl`, `enable-accelerated-2d-canvas`,
  `hardware-acceleration-policy=always`.

Boot, open the molecule page through `meta-app`, and capture the screen. Say
plainly whether the model drew or whether the page printed its no-WebGL notice.
If it did not draw, find the real cause (missing Mesa package, DRI path,
WebKit feature flag, sandbox) and fix it at the smallest level — **one change,
one before/after capture**, no shotgun edits.

Then measure: render time or fps at 1180×780 and at 1920×1080, and the atom
count used. If full screen is below ~10 fps, say so and give the window size
that is smooth. Do not remove the page's honest no-WebGL guard to get a nicer
screenshot.

### 2. `about.html` — "About this OS"

A small page on **18900** showing, read live (not hardcoded):
- version and pretty name from `/etc/os-release`
- `ID=` and codename
- kernel line (`uname -r`)
- session name and the desktop build date
- one short paragraph: what this OS is and what it is not

Style it like the other surfaces. It must say "Meta OS" and must **not** say
Ubuntu anywhere. It must not claim a rewritten kernel.

### 3. Prove an agent runs *inside* the guest

Submit one real job from inside the booted OS through the local relay
(`meta-ask`, or port 18940) for an agent that is live in `agents/registry.json`.
Follow it to a recorded run and paste: job id, agent name, timestamp, run
record. Then count how many of the registry's agents can actually accept a job
and **name the ones that cannot** (draft/unbacked). That honest fraction is
worth more than a percentage of nothing.

If the relay cannot start in the guest, that is the finding: paste the unit
state and the log lines and stop. Do not paper over it.

Never write the API key into a file. If a key is needed, read it from the
environment and say so.

---

## Definition of done

- A capture showing the molecule (or a positive statement that it cannot draw
  and why), plus the fps numbers and the exact reproduce command.
- `about.html` values matching `/etc/os-release` on the image, pasted side by
  side.
- One run record from inside the guest, live/draft agent counts with names.
- Write `os-build/lanes/AGENT_4_REPORT.md`, including a short list of claims a
  judge could make that this OS cannot back up.

Commit on `agent-4`. Do not merge.

---

# TASK QUEUE — 160 tasks, work top to bottom

Tick each in your report. If one cannot be done, write why and move on. Never
report a number you did not measure.

## A. 3D diagnosis (1-25)

1. Confirm the QEMU binary has no `gl=on` and no GTK display backend.
2. Record the exact `-display help` output as evidence.
3. Confirm Mesa `swrast_dri.so` exists on the image.
4. Confirm `libgl1-mesa-dri` is an installed package there.
5. Confirm `virtio_gpu_dri.so` exists.
6. Confirm `session.sh` exports the three software-GL variables.
7. Confirm those exports reach `meta-app` when launched from the dock.
8. Confirm `meta-app.py` sets `enable-webgl` without throwing on this WebKit.
9. Print the WebKitGTK version from inside the guest.
10. Boot and open `labs/molecules` via `meta-app`.
11. Capture the screen; save as `3d-before`.
12. State plainly whether the model drew.
13. If not, capture the exact on-screen message.
14. Read `/tmp/metaos-session.log` for the session's own errors.
15. Check WebKit's stderr for GL errors while opening the page.
16. Try `LIBGL_ALWAYS_SOFTWARE=1` explicitly on the `meta-app` command line.
17. Try `GALLIUM_DRIVER=llvmpipe` explicitly.
18. Try `WEBKIT_DISABLE_DMABUF_RENDERER=1` explicitly.
19. Try `WEBKIT_DISABLE_COMPOSITING_MODE=1` as a last resort; note the cost.
20. Check whether the landing page guards on `webgl2` only vs both.
21. Confirm the guard's message is not hidden behind a canvas.
22. Record which single change moved the needle, if any.
23. If nothing works, capture the failing GL error text in full.
24. Write the diagnosis in five sentences a non-programmer can follow.
25. Do not proceed to fixes without a capture at each step.

## B. 3D fixes and measurement (26-50)

26. Apply the smallest fix that produced a change, one commit.
27. Re-capture; compare with `3d-before`.
28. Measure render time at 1180×780.
29. Measure render time at 1920×1080.
30. Measure with the default atom count.
31. Measure with a heavy molecule (note the atom count).
32. Record fps or ms per frame, and say which you measured.
33. State the frame rate you would call smooth, and whether this meets it.
34. Give the window size that is smooth, with numbers behind it.
35. Repeat the measurement for `labs/music3d`.
36. Confirm both pages behave the same way.
37. Confirm the molecules page still guards honestly when WebGL is off.
38. Prove the guard by disabling WebGL once and capturing the notice.
39. Restore the settings and confirm the model returns.
40. Confirm the canvas is not stretched or blurry.
41. Confirm rotation responds to drag without lag spikes.
42. Confirm the page does not spin the CPU when idle.
43. Measure idle CPU with the molecule page open.
44. Confirm a second window does not halve the frame rate to unusable.
45. Confirm nothing you changed breaks 2D pages.
46. Confirm the desktop wallpaper still animates after your changes.
47. Confirm `meta-app` still opens non-3D pages normally.
48. Write the reproduce command exactly as you ran it.
49. Put both captures and both measurements in the report.
50. If 3D cannot work, say so and name what host change would fix it.

## C. `about.html` (51-80)

51. Create `os-build/face/about.html` on 18900.
52. Read version from `/etc/os-release` live.
53. Read `PRETTY_NAME` from the same file.
54. Read `ID` and `VERSION_CODENAME`.
55. Read the kernel line from `uname -r`.
56. Show the session name.
57. Show the build date from a real source, not a guess.
58. Show the desktop's name (Meta OS 1.0 Ribbon) consistently.
59. Write the one-paragraph "what this is" line.
60. Write the one-paragraph "what this is not" line.
61. Confirm the page says Meta OS and never Ubuntu.
62. Confirm it does not claim a rewritten kernel.
63. Confirm it does not claim a new distro base.
64. Confirm every value is live, not hardcoded.
65. Prove liveness: change a copy of `os-release` and see the page change.
66. Handle a missing `os-release` with a visible fallback.
67. Handle an unreadable `os-release` the same way.
68. Confirm the page fits 1180×780.
69. Confirm it works at 900×600.
70. Confirm it has no external assets.
71. Confirm it never shows a URL.
72. Confirm it is reachable from the dock tile path agent-1 wrote.
73. Confirm the tile opens it in `meta-app`, not a browser.
74. Confirm the page has a visible failure line if the facts backend is down.
75. Confirm the page reads to a judge in ten seconds.
76. Confirm the copyright/trademark wording is not a lie.
77. Confirm the page has no placeholder text.
78. Screenshot it; save under `os-build/captures/`.
79. Paste the page's values next to the real `os-release` values.
80. Commit.

## D. Agent pipeline proof inside the guest (81-110)

81. Confirm `metaosd` is running in the guest and on which port.
82. Confirm `/usr/local/bin/meta-ask` exists and is executable.
83. Run `meta-ask --list` in the guest; paste the output.
84. Count live agents and draft agents from that output.
85. Name every agent that cannot accept a job.
86. Submit one real job for a live agent.
87. Record the job id and the agent name.
88. Follow the job to a run record; paste it.
89. Confirm the run appears in the Agents app's run list.
90. Screenshot the Agents window showing the run.
91. Confirm the job's status transitions are visible, not instant-fake.
92. Submit a job for a draft agent; confirm it is refused with a reason.
93. Paste the refusal text.
94. Confirm the refusal does not look like success.
95. Submit an empty order; confirm it is refused.
96. Submit a duplicate; confirm the behaviour and document it.
97. Confirm the queue port answers and say which port.
98. Stop the queue; confirm the app says so instead of hanging.
99. Restart it; confirm recovery without a reboot.
100. Confirm `journalctl --user -u metaosd` shows your job.
101. Paste the two most relevant journal lines.
102. Confirm no API key is written to any file the image keeps.
103. Confirm the key is read from the environment only.
104. Confirm a run with no key fails loudly, not silently.
105. Measure how long one job takes end to end.
106. Record whether the agent's output is real text or a canned string.
107. If it is canned, say so — do not present it as a model response.
108. Write the numbers: agents live, drafts, jobs accepted, runs completed.
109. Write what a judge would find if they clicked around for a minute.
110. Commit with the run record attached.

## E. Session resilience (111-135)

111. Confirm `session.sh` still ends in `exec startxfce4`.
112. Simulate `meta-desktop.sh` missing; prove the desktop still appears.
113. Simulate `face.target` failing; prove the desktop still appears.
114. Simulate `metaosd` failing; prove the desktop still appears.
115. Simulate the agent login hook failing; prove the desktop still appears.
116. Simulate the wallpaper unit failing; prove a static wallpaper appears.
117. Simulate plank missing; prove the desktop works with no dock.
118. Confirm each failure writes one readable log line.
119. Confirm no failure writes a stack trace to the screen.
120. Confirm the session log has timestamps.
121. Confirm the session log is readable by the user who needs it.
122. Confirm the session starts in under eight seconds to the panel.
123. Confirm the panel and dock appear before the apps are clicked.
124. Confirm the dock starts after the window manager exists.
125. Confirm the wallpaper does not fight the window manager.
126. Confirm a second login works identically to the first.
127. Confirm a logout and login leaves no duplicate app windows.
128. Confirm no zombie processes after logout.
129. Confirm CPU is idle when nothing is open.
130. Confirm memory is reasonable with the desktop idle.
131. Confirm no service restarts in a loop.
132. Confirm no unit is enabled twice.
133. Confirm every unit has a description a human can read.
134. Confirm the wallpaper and session do not depend on each other.
135. Commit.

## F. `show_os.sh` (136-150)

136. Confirm `--headless N` exits on its own and never leaves a VM.
137. Confirm it refuses to start a second VM on the same image.
138. Confirm it extracts kernel and initrd from the ISO when `/tmp` is empty.
139. Confirm the extraction lands the exact filenames the boot expects.
140. Confirm `--persist` is the only mode that writes the image.
141. Confirm the audio device is optional and its absence is announced.
142. Confirm a failed boot prints the last log lines.
143. Confirm a successful boot prints PASS with a colour count.
144. Confirm it never hangs past its own timeout.
145. Confirm killing it leaves no QEMU process behind.
146. Confirm the serial log path is printed before boot.
147. Confirm the script works from any working directory.
148. Confirm it fails clearly when the image is missing.
149. Confirm `sh -n` passes.
150. Commit.

## G. Report and honesty (151-160)

151. Write `os-build/lanes/AGENT_4_REPORT.md`.
152. Put a one-paragraph summary at the top.
153. List every measurement with the command that produced it.
154. List every claim you are NOT making and why.
155. List what a judge could ask that this OS cannot answer yet.
156. List completed vs skipped task counts.
157. Confirm `git diff --name-only` shows only files you own.
158. Confirm you did not merge, rebase or push.
159. Confirm `main` is untouched by you.
160. Stop. Do not start work outside this queue.
