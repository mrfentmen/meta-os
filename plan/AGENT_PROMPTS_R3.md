# Round 3 agent prompts — de-Ubuntu, native apps, merges, packaging

Four lanes, four agents, no overlap. Each prompt names the files it owns and
the files it must not touch. Read the lane boundary before starting: the fastest
way to lose an hour here is two agents editing `meta-desktop.sh`.

Repo: `~/Desktop/meta-os`. Image under test: `/tmp/metaos.ext4` (raw ext4,
arm64). Mount it with:

```sh
docker run --rm --privileged -v /tmp/metaos.ext4:/disk.img \
  -v ~/Desktop/meta-os:/repo:ro ubuntu:24.04 bash -c \
  'mkdir -p /mnt; mount -o loop /disk.img /mnt && bash; umount /mnt'
```

Rules for all four agents:

- No mock code, no stub that returns a canned value, no `TODO: implement`.
- If you cannot verify something, say "not verified" in the commit message. Do
  not claim it works because it compiles.
- Never print, echo, or commit an API key. The key lives only in the image at
  `/etc/metaos/agent.env` (root 0600).
- Do not run more than one QEMU at a time. QEMU is the fan noise. Use chroot
  inside the docker mount for anything that does not need a display.
- Commit on your own branch. Do not push. Do not merge to `main`.
- Every script you add gets a `--check` mode that prints PASS/FAIL.

---

## PAX — identity: no Ubuntu left anywhere a person can look

**Owns:** `os-build/identity/*`, `os-build/iso/payload-theme/terminal/*`,
`/usr/share/backgrounds`, `/usr/share/plymouth`, greeter config.

**Must not touch:** dock wiring (`os-build/face/meta-desktop.sh`), agent runtime
(`agents/*`), anything under `eval/`.

### Already done — do not redo

`debrand.sh` rewrites os-release, lsb-release, issue, issue.net and motd, and
prints 14 PASS rows. `rename_user.sh` renames the live user to `meta`, moves the
home, rewrites passwd/shadow/group/gshadow/subuid/subgid, both autologin files
and every `/home/ubuntu` path in `etc`, `opt/face`, `usr/share/metaos` and the
user's own config. Both are applied to the image and verified.

### What is still left

1. **`/usr/share/plymouth/themes/ubuntu-text/`** still ships. The active theme is
   `metaos`, so it is dead weight that a judge can find with `ls`. Remove it
   along with any other `ubuntu*` plymouth theme, and prove `plymouthd.conf`
   still points at `metaos` afterwards.

2. **`/usr/share/backgrounds/greybird.svg` and `xfce/xfce-shapes.svg`** contain
   the string `ubuntu`. These are Xubuntu's stock wallpapers. Remove the stock
   set and keep only `meta-*.png` / `meta-spin.gif`. Then verify the active
   backdrop still resolves (it is set in xfconf, not by filename, so check it).

3. **`/usr/share/applications/gnome-mimeapps.list`** mentions ubuntu. Find out
   whether the reference is a `OnlyShowIn=Xubuntu` style key (then leave it, it
   is behaviour not branding) or a comment (then rewrite it). Say which in the
   commit message.

4. **Epiphany's about/start pages.** Open the browser in the guest and check
   `about:`, the new-tab page and the default homepage for Ubuntu strings. The
   dock no longer uses Epiphany for tiles, but the binary is still installed and
   a judge may open it. Rewrite what is configurable; list what is not.

5. **`/etc/hostname` is `metaos`** and the prompt is blue `metaos`. Check every
   remaining `ubuntu` on a `PATH`-executable, a `.desktop` name, a menu entry,
   or a title bar. `grep -rn ubuntu /usr/share/applications /etc/xdg` is the
   start, not the end.

### Deliverable

`os-build/identity/debrand2.sh` with `--apply` / `--check`, wired into
`os-build/iso/provision.sh`, plus a table in the commit message: every
`ubuntu` string you found, whether you removed it, and why if not. Target: a
fresh `grep -rli ubuntu` over `etc`, `usr/share/applications`, `usr/share/plymouth`,
`usr/share/backgrounds` returns zero hits.

---

## MILO — every app is a real window, and the dead ones work

**Owns:** `os-build/face/native/*`, `os-build/face/*.html` (content only),
Calendar and Musica backends.

**Must not touch:** `os-build/face/meta-desktop.sh` (tile wiring is Pax-adjacent
and currently working — coordinate before changing), `os-build/identity/*`,
`agents/*`.

### Already done — do not redo

`meta-app.py` opens a surface in a GTK window with no address bar, no tabs, and
a Meta-styled "this app is not answering" page instead of a browser error. All
eight surface tiles use it. WebKitGTK's Python binding is installed in the image.

### What to build

1. **Musica has no audio path.** There is no GStreamer in the image: no `Gst`
   typelib, no `gst-*` binaries. Install what is needed (`gstreamer1.0-plugins-base`,
   `gir1.2-gst-plugins-base-1.0`, an audio sink) and make Musica actually play
   the committed wav end to end. If the null sink is what the guest has, say so
   in the UI honestly instead of pretending there is sound. **Verify by playing
   it and reading the pipeline state, not by loading the page.**

2. **Calendar has no backend at all.** `calendar.html` fetches a server that
   does not exist. Write `calendar.py` on its own port with real event storage
   (a JSON file under the user's home, not localStorage), month list + create +
   delete, and wire it the way `board.py` is wired. Then the tile stops being a
   page that says "backend unreachable".

3. **Aegis has no tile.** There is an aegis surface and aegis eval work but no
   dock entry. Add the app window and the tile, and make sure the tile's page
   exists in the image rather than 404ing into the failure page.

4. **App icons in the title bar.** `meta-app` currently shows a generic window
   icon. Give it `--icon` and set the window icon + header bar icon from the
   Meta icon set, so two open apps are distinguishable in the window list.

5. **Kill the remaining dead-click risk.** For every tile, prove the target
   exists in the image before the tile is written (the `add_app` guard already
   checks the binary; extend the check to the page path for surface tiles).

### Deliverable

A table in the commit message: tile → program → what happens on click → verified
how. Any tile you could not verify gets "not verified" and the reason.

---

## HANA — land the merges and produce one honest scoreboard

**Owns:** `agent-layer/MANIFEST.md`, `agents/registry.json`, `eval/*`.

**Must not touch:** `os-build/*` (that is Pax and Milo's lane), `native/*`.

### Task

1. Execute `os-build/lanes/MERGE_PLAN.md` exactly: fifteen branches, in the
   order given, one `--no-ff` merge each, `registry.json` re-validated with a
   parser after **every** merge. A branch that leaves the registry unparseable
   is reverted, not patched by hand.

2. Produce `eval/SCOREBOARD.md`: one row per domain (vigiles, ignis, medicus,
   nypd, fdny, ems, mta, dsny, dep, doe, hospital, custos, nervus, musica,
   handsfree, science-lab, aegis) with scenario count, baseline score, current
   score, and the exact command that reproduces the number. If a domain has no
   harness, the row says `no harness` — do not invent a number.

3. Run every harness once at the end and paste the real output into the file.
   A scoreboard with a fabricated row is worse than an empty one, because a
   judge will ask you to run it live.

### Deliverable

`eval/SCOREBOARD.md` + a commit message listing, per branch, `merged` or
`reverted (reason)`.

---

## ROWAN — this has to be installable, not just bootable

**Owns:** `os-build/iso/*` (build, provision, calamares), `os-build/DEMO.md`.

**Must not touch:** `os-build/identity/*` (Pax), `os-build/face/*` (Milo),
`eval/*` (Hana).

### Task

1. **Calamares.** The installer config exists and has never been run. Install
   Meta OS from the ISO to a fresh qcow2 once, boot the installed system, and
   record what breaks. `os-build/BOOT_ON_32GB_MAC.md` has the boot recipe. If
   the installer cannot run in the time you have, that is a finding — write it
   down, do not delete the config to make the build pass.

2. **The ISO must build from a clean tree** with the current payload: the new
   `meta-app`, the renamed user, the debranded identity, the prompt fix. If
   `provision.sh` references a file that no longer exists, fix the reference.

3. **`DEMO.md` must match reality.** Walk every beat yourself and correct the
   expected output where it drifted. Do not add beats for things that are not
   true yet.

4. **One-command health check.** `os-build/tools/proof_session.sh` already
   probes the backends. Extend it to also check: `/usr/local/bin/meta-app`
   exists and runs `--help`, the `meta` user exists, `lsb_release -a` says Meta
   OS, and the prompt file contains `metaos`. It should be the single thing you
   run before recording the demo.

### Deliverable

A commit that moves `os-build/DEMO.md` from "describes the OS" to "describes
what happens when you run it", plus the proof_session output pasted in.
