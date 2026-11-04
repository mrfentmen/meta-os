# D — Identity (boot to desktop is one product): lane report

Owner: `os-build/iso/payload-theme/**`, `os-build/iso/plymouth/**`,
`os-build/face/plymouth/**`, `metaos-theme/**`, `payload-theme/apply.sh`.
Touched only those. Untouched as ordered: `build_iso.sh`, `calamares/**`,
`finalize-iso-tree.sh`, `repack-iso.sh`, `iso/provision*.sh`, `face/*.html`,
`face/*.py`, `kiosk.sh`, `session.sh`, `meta-live.py` + its frames, `agents/**`.

Ground truths honored: wallpaper (`meta-live.py`, 32 smooth frames @16 fps
image mode) not modified; `kiosk.sh`/`session.sh` not modified; palette
blue/black/white; ASCII-ribbon mark; image `/tmp/metaos.ext4`.

## D1. The theme lands — `apply.sh` rewritten

Change: `payload-theme/apply.sh` reworked — preflight gate (exact counts:
32 splash frames, 20 icons, 12 dock launchers, plus every named source;
exit 1 naming the missing file), absolute destination paths only, optional
`[ROOT]` arg (default `/`) so lane C calls `./apply.sh /mnt`.

Command:

```sh
docker run --rm --privileged -v /tmp/metaos.ext4:/disk.img \
  -v $PWD:/repo:ro ubuntu:24.04 sh -c '
  DEV=$(losetup -f); losetup "$DEV" /disk.img
  mkdir -p /mnt/d && mount -t ext4 -o rw "$DEV" /mnt/d
  sh /repo/os-build/iso/payload-theme/apply.sh /mnt/d
  chroot /mnt/d update-alternatives --install \
    /usr/share/plymouth/themes/default.plymouth default.plymouth \
    /usr/share/plymouth/themes/metaos/metaos.plymouth 100
  chroot /mnt/d update-alternatives --set default.plymouth \
    /usr/share/plymouth/themes/metaos/metaos.plymouth
  sh /repo/os-build/iso/payload-theme/theme_proof.sh /mnt/d'
```

Output: `apply: done -> /mnt/d (autologin untouched; ...)`, then proof
`10 passed, 0 failed`, exit 0. Status: **INSTALLED** (theme files in image,
md5-verified 98/98 — see Proof) and **PROVEN** (proof script green on image).

Side note (recorded, not hidden): the image carried trivial pre-existing
e2fsck filetype-flag warnings; cleared with `e2fsck -p` (exit 0, dir-entry
flags only). A stale `/dev/loop0`→`/disk.img` association blocked auto-loop
mounts; explicit `losetup -f` used instead. Lane C's `/base.iso` loop was
verified untouched (`ls /work/build/srcmnt` healthy in their container).

## D2. Icons resolve — `index.theme` + checker

Change: `payload-theme/icons/metaos/` — 20 128x128 RGBA glyphs (16 vendored
byte-identical from the image, see `SOURCES.md` + `SOURCES.sha256`; 4 drawn
by `generate-icons.py`: web, editor, agents, custos). Palette audit: every
opaque pixel in exactly 3 blue tones, 0 off-palette (`palette audit: PASS`).
`metaos.index.theme` (`Inherits=Papirus,elementary-xfce,hicolor`, all present
in image). `check-icons.sh` walks every `Icon=` in the image's 88+13
`.desktop` files plus the file-manager fixed set (folder, mime, home, trash,
disk, start-here, plank) and fails on the first miss.

Command: `sh theme_proof.sh /mnt/d` (row B delegates to the same resolver).

Output: `PASS icons: 98/98 names resolve (metaos + Inherits)`. Status:
**PROVEN** (resolution proven on image; pixel rendering on glass is lane C's
boot, not claimed here).

Two misses found and fixed during the lane: `metaos-imperium.desktop`
`Icon=metaos-imperium` (nonexistent) → `Icon=imperium`; proof allowlist for
the live username (below).

## D3. Plymouth — the ribbon spins

Change: one theme, one owner. `payload-theme/splash/` is the source;
`os-build/iso/plymouth/metaos/` is a byte-identical mirror (`diff -r`
clean, runtime files). `frames/` holds the existing 32-frame ribbon
downscaled 1920x1088 → 480x272 PNG (3.8 MB total, same pixels, 100.00%
blue-dominant audit). `metaos.script` preloads all 32 as literals
(zero-padded names avoided: the script language has no zero-pad operator)
and advances one frame per 4 refresh ticks ≈ 15 fps at 60 Hz, matching
`meta-live.py` image mode (32 frames at 16 fps, same 2 s turn). Progress
bar, password (`*` bullets, no cursor sprite anywhere), message and quit
handlers kept; 7 hooks asserted.

Prove-without-boot commands and output (all on the image, via chroot/ro):

- `update-alternatives --query default.plymouth` →
  `Value: /usr/share/plymouth/themes/metaos/metaos.plymouth` (Status: manual)
- descriptor parses: `[Plymouth Theme]`, `ModuleName=script`, absolute
  `ImageDir`/`ScriptFile` pointing at installed files
- script refs: 34 `Image("…")`, all resolve; 7/7 hooks present; no
  ubuntu/xubuntu strings; balanced brackets
- frame count in image: 32/32 (`ls …/frames/frame-*.png`)
- contact sheet: `os-build/lanes/D_plymouth_contact.jpg` (8x4, next to this
  report) — the ribbon mid-turn, meta blues on ink

Status: **PROVEN** (everything provable without a boot). **BLOCKED** by
scope: the boot capture (`screenshots/theme/H12-splash-boot.png`) and the
initramfs rebuild (`plymouth-set-default-theme -R`) are lane C's at ISO
build — stated plainly, not claimed.

## D4. GRUB theme

Change: `payload-theme/grub/{theme.txt,background.png,mark.png,
generate-grub.py}` — title `Meta OS 1.0`, timeout 10, stock GRUB fonts only
(no `.pf2` ships), background = splash pixels 1920x1080, mark = M at 256 px.
No ubuntu/xubuntu strings (`grep` clean).

Command: `python3 generate-grub.py` → `grub: background.png 1920x1080,
mark.png 256x256`. Installed by `apply.sh` to `/boot/grub/themes/metaos/`
(staging; proof row I green). Status: **INSTALLED**; wiring
(`GRUB_THEME=…`, `GRUB_TIMEOUT`, `GRUB_DISTRIBUTOR`) is lane C's integration.

## D5. Greeter

Change: `greeter/lightdm-gtk-greeter.conf` (`icon-theme-name=metaos`,
`font-name=Inter 11`, mark avatar, blue field — key set unchanged from the
validated `KEYS.md`); new `greeter/unity-greeter.conf` for the greeter
actually installed in the image (background `meta-rays.png`, logo
`meta-m.png`, same font/theme/icon names). `10-metaos-live.conf` kept except
one comment reworded off the literal `(xubuntu)`.
`lightdm.conf` / `50-metaos.conf` untouched.

Autologin proof (image, post-install):

- `50-metaos.conf`: `autologin-user=ubuntu`, `user-session=metaos`,
  `greeter-session=unity-greeter` (unchanged)
- proof row G: `PASS autologin: ubuntu + user-session=metaos (link 1 intact)`

Status: **PROVEN** (config installed, autologin contract intact; pixels on
glass are lane C's boot).

## D6. Identity strings

Change: `payload-theme/identity/{os-release,lsb-release,hostname,issue,
issue.net,motd,00-header}`; `apply.sh` installs them (os-release written
*through* the `/etc/os-release → ../usr/lib/os-release` symlink, link
preserved — verified `Type: symlink` post-install; base copy kept as
`os-release.base-flavour`).

- `/etc/os-release`: `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `ID=metaos`
  (full content pasted in Proof below)
- `/etc/hostname` = `metaos`, hosts `127.0.1.1 metaos`, issue/motd carry
  `(Ribbon)`
- 17 dock `.desktop` Names: 12 new `apps/dock/meta-dock-*.desktop` + already
  installed Web/Files/Settings/Terminal + `metaos-imperium.desktop` renamed
  to `Name=Imperium`. Proof row J: all 17 resolve. Pre-existing image scan:
  all 88 installed `.desktop` Name/Comment lines already clean (zero hits).
- Tree scan (proof rows D+E): green; allowlist below.

Status: **PROVEN**.

## D7. Fonts

No font binaries shipped (nothing to re-licence). `fonts/FONTS.md` records:

| face | package in image | licence (in-package proof) | referenced from |
|---|---|---|---|
| Inter (display/UI) | `fonts-inter` 4.0+ds-1 | SIL OFL 1.1 (`/usr/share/doc/fonts-inter/copyright`, `License: OFL-1.1`) | greeter `font-name=Inter 11`, `gtk.css` `font-family: 'Inter', …` |
| Ubuntu Mono | `fonts-ubuntu` | Ubuntu Font Licence 1.0 (`/usr/share/doc/fonts-ubuntu/copyright`, design.ubuntu.com/font) | `terminal-profile.txt` `FontName=Ubuntu Mono 11`, gtk fallback stack |

Changes: `gtk.css` gains the Inter-first font stack; terminal profile moves
`Monospace 11` → `Ubuntu Mono 11`; profile doc installed to
`/usr/share/doc/metaos/terminal-profile.txt`. `apply.sh` refuses the install
when neither face is present (files found in image; gate not triggered).
Proof row H green. Status: **PROVEN**.

## Proof

`theme_proof.sh` (in `payload-theme/`, installed to
`/usr/local/lib/metaos/theme_proof.sh` + `check-icons.sh` beside it),
run against the mounted image after `apply.sh`:

```
PASS assets: manifest complete in image
PASS icons: 98/98 names resolve (metaos + Inherits)
PASS absolute-refs: greeter + plymouth point at absolute paths
PASS brand-owned: lane D files carry no ubuntu/xubuntu
PASS brand-tree: .desktop Name/Comment + greeter/panel carry no ubuntu/xubuntu
PASS plymouth: descriptor+32 frames+7 hooks+fps note+default=metaos
PASS autologin: ubuntu + user-session=metaos (link 1 intact)
PASS fonts: Inter + Ubuntu Mono installed and referenced (gtk+greeter+terminal)
PASS grub: Meta OS 1.0 title, timeout 10, no ubuntu strings
PASS dock-names: all 17 dock apps have a .desktop Name=
----
theme_proof: 10 passed, 0 failed
```

md5-compare repo→image: **98 compared, 0 differ**. Full list:

```
65cfd2ed244cb29beb7c4245886c55fa greeter/gtk-greeter.conf
47c18bb494ac4ee2cb5bf47743f90291 greeter/unity-greeter.conf
92793d13b36737945ed888f02e6641f5 greeter/10-metaos-live.conf
cadca877ec07e19f9ae11c79def53bb3 backgrounds/meta-ascii.png
703348305e476b32aa9044cf58f70526 backgrounds/meta-rays.png
70f4cd98751220cb8699a9f1faf9b454 backgrounds/meta-dusk.png
f16c0be366db8d73985d939fda97842e backgrounds/meta-dawn.png
92d8014f686d4dbcfb16aba4698c9606 backgrounds/meta-m.png
b53b84920dd845d9089378d2bc7020a1 plymouth/metaos.plymouth
48a936408f732149e6faa5f975c47a8f plymouth/metaos.script
1f7bf4b6d51f5c8abe54ef604622e93e plymouth/background.png
92d8014f686d4dbcfb16aba4698c9606 plymouth/meta-m.png
0df04e8ae3e148c438e726a546298d56 plymouth/progress.png
6083d68ce99ead5f965fab2a988ece67 plymouth/frames/frame-0.png
3b5d1fdb6f0407409f70a69c6d371b4d plymouth/frames/frame-1.png
c5d21838472ca37badd39359ed6c862c plymouth/frames/frame-2.png
6152927bff51294e141514871087fd1d plymouth/frames/frame-3.png
b1f0ffe3365a7072de83af6d0fcef8c8 plymouth/frames/frame-4.png
801a3a7a91ff93992f3d5ffae 
...[truncated 3881 chars]
## Shared-tree note (not my changes, left untouched)

The working tree is shared by four parallel lanes and was already dirty when
this lane started. Notably `wallpapers/live/meta-live.py` (`FPS_IMAGES 8→16`,
`_fit_to_screen` — the settled wallpaper work) and
`panel/xfce4-panel.xml` (top-bar position/length fix) carry uncommitted diffs
authored outside this lane; per the lane contract neither file was edited
here. This lane's tracked edits are 13 files, all under `payload-theme/` +
`iso/plymouth/metaos/`; `metaos-theme/` untouched.
