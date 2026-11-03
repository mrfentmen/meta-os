# OC3 STATUS — ISO assembly (agent3, NO VM, ZERO QEMU)

Branch: `opencode/agent3-oc3` (base: main @ 1b32be39). No boots, no mounts-as-boot, no builds. All evidence below is VERIFIED (ran it, read-only) or CODE-INSPECTED (read it), per the iron rules.

## T1 — baseline ISO bytes (VERIFIED, pre-drop-in baseline)

- Bytes: `/private/tmp/isowork/metaos-1.0.iso`
- Size: 4,259,762,176 (imageinfo Total Bytes; `ls` agrees)
- SHA256 recomputed 2026-11-03: `6d3793eb1cfb34cb7ca537c90f965a916c1454695af270843a18f06363770dde`
- Matches recorded `metaos-1.0.iso.sha256` and `.sha256-fixed` byte-for-byte. VERIFIED.
- Volume label: `METAOS_1_0` (GUID/ISO9660 hybrid, UDTO). VERIFIED via imageinfo.
- Structure (CODE-INSPECTED via `bsdtar -tf`, 925 entries, no mount, no boot): standard Ubuntu live layout — `boot/grub` (i386-pc + x86_64-efi), `casper/`, `dists/`, `EFI/`, `install/`, `pool/`. `casper/` carries the merged single `filesystem.squashfs` **plus** the `minimal*` layered set, `initrd`, manifests, `SHA256SUMS`, `install-sources.yaml`.
- macOS note: `hdiutil attach` (read-only, nomount and full) reports "no mountable file systems" on this Mac — inspection done via bsdtar instead. This is NOT a boot failure, just a Mac mounting limitation. Booting is OC1's lane.

## What's IN / OUT of this baseline (CODE-INSPECTED)

- IN: merged squashfs layout per LANE_TAKEOVER plan, GRUB + EFI bootloaders present as files (presence only — execution is OC1's proof).
- OUT: OC2 drop-ins (zero `.desktop` / `mimeapps.list` in the image) and OC1 theme pack (zero `plymouth`/`calamares`/metaos-branded paths in the image). → **T2 re-cut required** once OC1 theme posts; drop-ins staged below.

## Staged inputs for T2 (recorded, not copied — copy happens at re-cut)

- OC2 drop-ins, source `origin/opencode2/landwalls`, blob shas (short):
  - `5a99d4b65fd9` README.md, `2b062cdf86c2` atril.desktop, `10edb2100053` evince.desktop, `915c5485bc67` meta-agent-status.desktop, `167500f900e6` mimeapps.list, `e8bececadb31` mousepad.desktop, `e33c117ab5e9` ristretto.desktop, `90bbb6a625d4` thunar.desktop
- OC1 theme pack: NOT POSTED yet (no theme-pack/shot-list/greeter drop-in on main or landwalls as of this writing; `iso/theme/` on main is the pre-existing Buffy set, not a posted pack). T2 waits on it per the no-waiting rule — baseline stands meanwhile.

## Next (OC3)

- T2: re-cut ISO with OC1 theme + OC2 drop-ins when both posted (copy by sha, record sha, publish new bytes + sha here). No boot — hand off to OC1.
- T3: installer config static check only (unattended seed, firstboot script). Boot test is OC1's lane.

## §9 verdict (OC3B-220) — DONE static, boot checks deferred to OC1
- 201 inventory committed. 202 eight entries authored (oc3b-desktop/).
  203/206/207/208/209/210 all-pass, output committed (OC3B-desktop-test.txt).
- 204 Exec-on-image, 205 icon-resolve, 211 targets-run, 216/217 menu-opens,
  222/223 persist-across-reboot/upgrade: DEFERRED — OC1 boot checks, named.
- 212 handoff written with copy-only + sha instructions.
- 213 pins proposed, approval OC1/theme. 215/218/219 structures recorded.
- 221 defects filed (3, one is office-suite-has-no-source).
- 224 ownership recorded. No shared files touched; OC2/ISO/theme entries
  referenced, never rewritten.

## §1 verdict (OC3B-023) — DONE static, boot + package confirmations deferred
- 001/002 BLOCKED with owner (ISO lane provision step): no browser
  binary confirmable from the ISO file list on this Mac.
- 003 start page authored, 004 offline (0 external refs), 005 MetaOS-named,
  006 zero Apple-adjacent strings/assets, 014 fluid-layout CODE-INSPECTED,
  015 3726-byte proxy + on-target timing deferred.
- 007 homepage wired two layers, 008 --app launcher authored (9th entry,
  all audits pass), 009 Terminal=false, 010 no remote default (documented
  as policy, not an omission), 011 wizard mitigations, 012/013 no seeded
  bookmarks (vacuous pass, stated), 016 history options open, 017 ops,
  018 handoff written, 019 acceptance PENDING, 020 self-install fallback
  written, 021 quiet honestly bounded (packet capture: OC1), 022 no
  extensions, 024 three defects filed (one BLOCKED dep, two watch items).

## §2 verdict (OC3B-045) — DONE static, interactive checks with OC1
- 026 package recorded (xfce4 KEEP), version explicitly NOT guessed.
- 029/030 theming wired by config (MetaOS xsettings + icons), UI-string
  audit clean; dev-doc Xubuntu mentions out of scope by design.
- 034/041/044/043 recorded as CODE-INSPECTED with keys named.
- 037/038 no new entry (two already exist); 038 answered from the
  Exec line, observation deferred. 039/040 written.
- 027/028/032/033/035/036/042/047/048/049 BLOCKED-with-owner (OC1 boot),
  all in one basics file. 031 home defaults: watch item for first boot.
- 046 two defects + one all-clear. Handoff doc written; no shared
  files touched.

## §3 verdict (OC3B-068) — DONE static, interactive with OC1
- 051 package recorded, version explicitly not guessed. 054/055 hook
  guards verified by reading (once-flag, PS1 gate, || true).
- 056 bash + user PS1, unchanged. 070 welcome app standalone per its
  docstring. 059 no new entry (two exist); TryExec suggestion filed.
- 060 opens-to-home from Exec analysis. 061/062 written. 063-066,071,
  072-074 recorded with exact provenance; ssh-client presence +
  version are OC1 one-liners. 073 inert-by-construction (nothing ships
  autostart/ssh-config). 067 hook strings clean; binary menu strings
  are OC1 screenshots. 057/058/065 BLOCKED-with-owner (OC1 boot).
- 069 one suggestion + all-clear. No shared files touched.

## §4 verdict (OC3B-093 pattern; 076..100 batch) — DONE static, screens with OC1
- 076 inventory from shipped xfconf channels, no invented panels.
- 078 wallpaper pin verified in xfce4-desktop.xml (last-image +
  zoomed style); sticks-by-construction, screenshot still OC1's.
- Theme keys + clock verified in shipped configs; per-screen
  behavior (079/082/083/084) and persist/reboot (090) with OC1.
- 085 UI-string audit clean (dev docs out of scope by rule).
- 091 a11y gap honestly recorded with a named decider.
- 086 no new launcher (exists); TryExec suggestion filed, not edited.
- 087/088 handoff + ops written. 093 two gaps + all-clear.

## §5 verdict (OC3B-116) — DONE static, playback with OC1
- 101 inventory: viewers committed, binaries TryExec-guarded, webcam
  honestly absent, audio plumbing UNCONFIRMED (not claimed either way).
- 102-105/112/113/119: pointer files to OC1 boot proofs. 106 audio:
  unconfirmed, named. 107/108 launchers authored + handoff written.
- 109 brand audit clean (UI strings). 110 ops written. 111 tool
  committed. 114 absent-on-record. 115 bounded quiet claim (no
  packet-capture pretended). 118/123/124 gaps named with filler
  package + policy owner. 120/121 entry committed, mute test OC1.
  122 no separate lane needed. 117 three defects, all owned.

## §6 verdict (OC3B-141) — DONE static, runs with OC1
- 126 editors/calc/notes inventoried; 132 entries listed (mine +
  OC2's, none rewritten). 130 welcome opens from menu; 131
  once-flag CODE-INSPECTED + test_welcome 30/30 co-located
  (earlier 4-error run was my harness missing a file, recorded).
- 134/140 brand+quiet bounded and clean. 135 ops written. 136
  archives pointer to §2. 137 readers present; 138 render check OC1.
- 139 printing stack ABSENT (named, owner ISO lane). 143-145/147
  clipboard/charmap/disk-GUI absent with CLI fallback named.
- 148 nothing to hand. 133 handoff written. 142 three defects, all
  owned. 127/129/149 interactive BLOCKED-with-owner (OC1).

## §7 verdict (OC3B-166) — DONE static, playback with OC1
- 151 inventory with exact byte counts; 152/153 structural
  verification via ffprobe (180.000s film, 1.5s loop, codecs present).
- 154 wallpapers pixel-verified at native sizes. 155 placed-path
  contract recorded, installer owns it. 156 tour = 60s script beats.
- 157/158 script written with per-beat timing; live timing is OC1's
  overwrite, not mine. 159/160/163/164/165 honesty + licenses
  audited (SIMULATED present where it belongs; all-original pack).
- 161 launcher authored + tour.html written (offline, 0 external
  refs). 162 handoff written. 168/169/170 1.4 MB counted, no budget
  to check against — sent to Pax. 171 closing line per cut plan.
- 172 stutter check OC1. 173 silent-by-cut-design + beds licensed.
  174 offline (local files only). 167 two defects, both owned.

## §6 verdict (OC3B-141) — DONE static, runs with OC1
- 126 editors/calc/notes inventoried; 132 entries listed, none
  rewritten (OC2's + my galculator). 130 menu entry present;
  131 once-flag CODE-INSPECTED + test_welcome 30/30 co-located
  (earlier 4-error run was my harness, recorded).
- 134/140 brand+quiet bounded and clean. 135 ops written.
- 136 archives: pointer to §2. 137 readers present (atril live,
  evince degraded-off, Hana ack pending). 138 render check OC1.
- 139 printing stack ABSENT, owner ISO lane. 143/144/145/147
  helpers absent with du fallback named. 148 nothing to hand over.
- 127/129 interactive + 149 cold timing BLOCKED-with-owner (OC1).
- 142 three defects, all owned. 133 handoff written.

## §8 verdict (OC3B-192) — DONE static, screenshots OC1's
- 176-178 About written (1.0 vs 2.0 per LAYERS/iso docs).
- 179 launcher authored, 180 standard handoff. 181 five tips in-page;
  182 once-behavior rides the welcome flag (see §6).
- 183 defaults documented as upstream Xfce, verified at boot.
- 185 nothing exotic claimed. 184/187 tried-vs-named split honored.
- 188/189 privacy matches shipped config; capture is OC1's.
- 190/191 paths recorded, existence OC1-confirmed.
- 194 offline (swept: zero external refs, 4 files).
- 195/196 two relative tour links resolve at install; no dead ends.
- 197/198 original, cleared for ISO. 199 done-criteria met bar boot
  screenshot. 193 one watch item + clean sweep.
