# Meta OS — the demo, beat by beat

Three minutes. Every beat below is something that was actually observed on this
machine, and each one names the evidence. Beats marked **PENDING** are not
ready and must not be shown as if they were.

Tonight's receipts (image re-synced from `main`, booted four times) are in
`os-build/STATUS_2026-11-04.md`: the desktop capture, the 9/9 session proof,
and the five bugs that were only visible on screen.

Two proof scripts back the whole thing:

| Script | What it checks | Run it |
|---|---|---|
| `os-build/tools/show_os.sh` | boots the image in a window, with sound | `sh os-build/tools/show_os.sh` |
| `os-build/tools/proof_boot.sh` | boots detached, polls the framebuffer, fails if the screen stays one colour | `sh os-build/tools/proof_boot.sh --timeout 180` |
| `os-build/tools/proof_session.sh` | inside the guest: 9 rows over the loopback services, fails with `DEAD ports:` | `bash /opt/face/proof_session.sh` |

Latest boot capture: `os-build/captures/proof-boot-1920x1080-20261103T205318Z.png`
— 1920×1080, not single-colour, PASS. It is taken early, so it shows the
top bar and the wallpaper and **no dock yet**.

The dock, on a live guest at 21:09 UTC: `os-build/captures/dock-live-1920x1080-20261103T2109Z.png`.
That frame is the honest "what the desktop looks like" picture: `Meta OS` top
bar, the animated ASCII wallpaper filling the 1920×1080 screen, a terminal
window with the prompt `metaos` in blue, and the plank dock along the bottom
with roughly twenty tile icons. Captured off the running guest's QEMU monitor
(`screendump`), not staged.

---

## Pre-flight (do this before anyone is watching)

```sh
cd ~/Desktop/meta-os
sh os-build/tools/proof_boot.sh --timeout 180     # must end in PASS
```

If that fails, do not start the demo. `show_os.sh` prints the last serial lines
on a failed boot, which is what you paste into the group chat.

---

## Beat 1 — It boots (20s)

```sh
sh os-build/tools/show_os.sh
```

**On screen:** a QEMU window, then the Meta OS desktop — top bar with the Meta
mark and the clock, the dock at the bottom, the animated ASCII Meta symbol
filling the whole screen as wallpaper. All four of those are in
`captures/dock-live-1920x1080-20261103T2109Z.png` if the live boot misbehaves.

**Say:** "This is Meta OS 1.0, codename Ribbon. It boots from a single image."

**Do not say:** "we wrote the kernel." It boots an Ubuntu ARM64 kernel; the
Rust kernel in `kernel/` is a separate experiment that is not what runs here.

---

## Beat 2 — The name is ours, everywhere a person can look (20s)

In the guest terminal:

```sh
cat /etc/os-release
lsb_release -a
id
```

**Expected:**
- `NAME="Meta OS"`, `VERSION="1.0 (Ribbon)"`, `ID=metaos`
- `Description: Meta OS 1.0 (Ribbon)`, `Codename: ribbon`
- the account is `meta`, not `ubuntu`
- the prompt reads `metaos` in blue (visible in
  `captures/dock-live-1920x1080-20261103T2109Z.png`)

**Say:** "Base is Debian; the identity, session, theme, services and apps are
ours."

**Do not say:** "we rewrote Linux." `apt` still says `noble` — that is
deliberate, or package installs break.

---

## Beat 3 — Apps are windows, not web pages (30s)

Click **Board** on the dock, then **Calendar**, then **Musica**.

**On screen:** a titled window with a close button, **no address bar, no tabs,
no URL**. That is the whole difference between "an app" and "a webpage", and it
is why `meta-app` exists.

Calendar is backed by `face-notesd` on 18937 — its own self-test passes 11/11
inside the image (create note, survives restart, calendar export, import,
settings).

**Say:** "Each of these is a GTK window onto a local service. Nothing here
needs the internet."

**Proven for Board** (capture: `os-build/captures/app-window-board-2026-11-03.png`).
For the other tiles this is the same command line — say "same mechanism" rather
than "all verified" until they have each been clicked.

---

## Beat 4 — The Imperium console (25s)

Click **Trio** (or Imperium — same program, two tiles).

**On screen:** the police / fire / EMS dispatch console (Meta Vigiles, Meta
Ignis, Meta Medicus) with its product switcher. Native GTK over local files, not
a browser.

**Say:** "This is the product we built the OS for: one console for three
services."

---

## Beat 5 — An agent runs inside the OS (40s)

In the guest terminal:

```sh
meta-ask --list
meta-ask <agent> "summarise the current board"
```

**On screen:** `--list` prints the live agents from `agents/registry.json`;
the job is accepted with a job id, then appears as a run in the **Agents**
window (port 18940).

**Say:** "The agent relay runs in the OS, not on my laptop."

**Be precise:** name how many agents are live versus draft. If the run does not
complete, show the refusal text — a refusal that says why is a better demo than
a fake success.

---

## Beat 6 — Science Lab, 3D (25s)

Click **Science**.

**On screen:** the molecule viewer with a real rotating model, or — if WebGL has
not been proven on this boot — a clearly worded "no 3D context" notice.

**Say:** "Software-rendered: this host's emulator has no GPU 3D, so Mesa's
software rasteriser draws it. On real hardware this is GPU-accelerated."

**PENDING:** an fps number at 1180×780 and 1920×1080. Until that is measured,
say "software rendered, slower than real hardware" and stop there.

---

## Beat 7 — What this is, honestly (20s)

**Say:** "Meta OS is a Meta-branded desktop on a Debian base: our kernel
experiment, our theme, our session, our services, our apps, our agent relay.
The base is Debian — we say so, because a judge will check."

**Do not claim any of these:**

- a rewritten Linux
- a new kernel in this image
- that Aegis is finished — the page exists and the tile is wired, but the
  nightly image install was not proven
- that Messages is a working messenger — it is a relay client with no relay
- that all dock tiles were clicked and verified — only Board has been
- GPU 3D

---

## PENDING beats — do not show until the report says proven

| Beat | Blocked on |
|---|---|
| Aegis security dashboard | page + tile exist (`aegis-page/`, self-test PASS); copy landing on the image is unproven |
| Messaging app | `bus.html` ships with a tile, but it needs a relay REST URL + token; offline it says `Status: not connected` |
| 3D fps numbers | measurement (agent-4) |
| Every tile clicked | per-tile proof; 27 tiles exist, Board is the only one with a capture |
| Icon glyphs read clearly at 40px | none are duplicates (`shasum` over the 26 files shows 0 identical pairs), but the two shields (Aegis, Imperium) look alike and the terminal mark is a bare slash — polish, not a bug |

---

## If something breaks on stage

1. Do not restart the VM mid-beat; close the app window and reopen it.
2. If the desktop does not appear, run `proof_boot.sh` and paste its verdict —
   it is the difference between "broken" and "you did not wait".
3. If a service is down, `bash /opt/face/proof_session.sh` inside the guest
   prints one row per port and ends with `DEAD ports:` naming the failures.
   Read those out loud; it is a better look than guessing.

---

## R2-T4 corrections, 2026-11-04 (agent-r2-t4 lane — appended, existing lines untouched)

Evidence lane read the tree from `/tmp/agent-r2-t4` (branch `agent-r2-t4`) without
booting. Beats needing QEMU, the guest, or services are marked cannot-run with why.

**C1 — stale capture filenames.** `captures/proof-boot-1920x1080-20261103T205318Z.png`
is not in the tree (`ls` → no such file). Quote a present capture instead.

**C2 — dock count is 26 today.** `grep -cE '^\s*add_app ' os-build/face/meta-desktop.sh` → **26**
(was 27, then 30 — sibling lanes keep adding tiles; recount before the show).

**C3 — icons 30, sums file lives one level up.** `ls
os-build/iso/payload-theme/icons/metaos | wc -l` → **30** PNGs;
`SOURCES.sha256` is at `icons/SOURCES.sha256`, not `icons/metaos/`.

**C4 — identity `--check` rows need the guest image, not this Mac.** They fail
here by design (no `/mnt` root); run them in the guest or mounted chroot.

**C5 — numbers re-verified still true on this tree:** `agents/registry.json`
→ 24 agents, 23 live, 1 draft; `python3 os-build/face/notesd.py --selftest`
→ 11/11 ok + PASS (ran 2026-11-04).

## Beat 0 (PROPOSED) — sync the image, prove the tree matches — boot lane

Do this before the pre-flight. It needs the image and one boot, so it stays
in the boot lane and must not be shown as done until it passes.

```sh
git log --oneline -3
sh os-build/tools/verify_tree.sh
sh os-build/tools/proof_boot.sh --timeout 180     # must end in PASS
bash /opt/face/proof_session.sh                   # inside the guest, expect 9/9
```

## Division-apps beat (paths only, no boot)

| App | Page |
|---|---|
| Boards | `surfaces.html` (13 boards, `#board-index` count) |
| Science bench / cycles | `labs/index.html` → `labs/molecules/`, `labs/science-lab-review/` |
| Music | `labs/music3d/index.html` (`design/meta-musica-notes.html` redirects there) |
| Security | `aegis-page/index.html` |
| Messages | `bus.html` (rooms over T3 `board.mjs` :18935) |
| Status | `nervus/index.html` (read-only; dock entry proposed, not wired) |

## Agent-job beat (PROPOSED) — PENDING on this host

`meta-ask --list` needs a staged relay (`~/.local/state/oc2-agent`) or the
guest; on this host it prints `meta-ask: no registry found`. Do not demo
until a lane proves one job end to end on the demo machine.
