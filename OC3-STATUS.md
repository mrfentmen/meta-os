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
