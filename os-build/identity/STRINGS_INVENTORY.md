# STRINGS_INVENTORY — every ubuntu hit, one line each, with a verdict

Generated 2026-11-04 by bucketing `git grep -in ubuntu` (996 hits).
Verdicts: `identity` = a person could read Ubuntu where Meta belongs
(LEAK rows name the owning lane); `compat` = package/archive/image/field
name the system needs; `attribution` = names the base honestly (comments,
docs, test denylists, fixer tools); `generated` = evidence output.
Checker scope: `check_strings.sh` never reports inside `plan/`,
`os-build/logs/`, `.git`, `node_modules`, or binaries — those hits are
counted in the summary rows at the bottom, not listed per line.

## Per-hit verdicts (repo files the checker reads)

| file:line | hit (truncated) | verdict | reason |
|---|---|---|---|
| .github/workflows/ci.yml:12 | runs-on: ubuntu-latest | compat | package/archive/image/field name the system needs |
| BOOT_READINESS.md:124 | OC2P-012 bounds this as one spike, Xubuntu ISO only if present | attribution | names the base honestly |
| OC3-STATUS.md:12 | - Structure (CODE-INSPECTED via `bsdtar -tf`, 925 entries, no mount, no boot): standard Ubuntu live layout — `boot/grub` (i386-pc + x86_64-efi), `casper/`, `dists/`, `EFI/`, `install/`, `pool/`. `casp | compat | package/archive/image/field name the system needs |
| OC3-STATUS.md:59 | audit clean; dev-doc Xubuntu mentions out of scope by design. | attribution | names the base honestly |
| OC3-STATUS.md:211 | 3. Cut record: OC3B-cut-record.md. Source xubuntu-base.iso | attribution | names the base honestly |
| agent-layer/README.md:3 | Patrol + crew + queue + livecams, as systemd user units (Debian/Xubuntu target). | compat | supported-distro target statement |
| agent-layer/RELAY_STATUS.md:4 | Image: `/tmp/metaos.ext4` (16 GB ext4, user `ubuntu`), inspected offline via | attribution | names the base honestly |
| agent-layer/RELAY_STATUS.md:57 | version `18.19.1+dfsg-6ubuntu5`, `Architecture arm64`. | attribution | names the base honestly |
| agent-layer/RELAY_STATUS.md:186 | 3. Image content via `debugfs` (Docker `ubuntu:22.04`, read-only): | attribution | names the base honestly |
| agent-layer/check-keep-mime.sh:7 | # atril(drop-in) split is an EXPECTED mismatch with a note (Xubuntu 24.04.5 | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| agent-layer/desktop-entries/README.md:18 | Xubuntu 24.04.5 base ships atril where KEEP lists evince. OC2 does NOT edit | attribution | names the base honestly |
| agent-layer/desktop-entries/atril.desktop:6 | Comment=View PDF files (base-observed binary on Xubuntu 24.04.5; KEEP line still says evince pending Hana ack — see README) | LEAK(OS-3) | user-visible Comment names Xubuntu base — request to OS-3 |
| agent-layer/desktop-entries/evince.desktop:6 | Comment=DEGRADED-OFF: KEEP lists evince but Xubuntu 24.04.5 base ships atril. Hidden until Hana acks. Do not map MIME here. | LEAK(OS-3) | user-visible Comment names Xubuntu base — request to OS-3 |
| agent-layer/desktop-entries/mimeapps.list:5 | # Xubuntu 24.04.5 base ISO ships atril where KEEP lists evince. If Hana acks | attribution | names the base honestly |
| agent-layer/install.sh:20 | # 2. Deps. Debian/Ubuntu target: nodejs (queue hard-requires node for | compat | supported-distro target statement |
| agents/sandbox.mjs:13 | //   node agents/sandbox.mjs run --image ubuntu:24.04 --timeout 10000 --net none -- sh -c 'echo hi > /work/out.txt; cat /etc/os-release / head -1' | compat | package/archive/image/field name the system needs |
| agents/sandbox.mjs:54 | const image = options.image // "ubuntu:24.04"; | compat | package/archive/image/field name the system needs |
| agents/sandbox.test.mjs:6 | // ubuntu:24.04 image is present, they skip (NO_DOCKER/NO_IMAGE) instead | compat | package/archive/image/field name the system needs |
| agents/sandbox.test.mjs:18 | const IMAGE = process.env.SANDBOX_TEST_IMAGE // "ubuntu:24.04"; | compat | package/archive/image/field name the system needs |
| crates/parity-tests/src/tests/test_os_base.rs:26 | "bullseye", "trixie", "forky", "sid", "ubuntu", "fedora", "centos", "rhel", "archlinux", | attribution | test denylist that FORBIDS the word; self-policing |
| crates/parity-tests/src/tests/test_os_livebuild.rs:35 | pub const FORBIDDEN: &[&str] = &["bullseye", "trixie", "forky", "sid", "ubuntu", "fedora", "centos", "rhel", "archlinux"]; | attribution | test denylist that FORBIDS the word; self-policing |
| crates/parity-tests/src/tests/test_os_packer.rs:31 | pub const FORBIDDEN: &[&str] = &["bullseye", "trixie", "forky", "sid", "ubuntu", "fedora", "centos", "rhel", "archlinux"]; | attribution | test denylist that FORBIDS the word; self-policing |
| iso/apps/README.md:3 | Launch configs only — no app is rewritten, no stub ships. Xubuntu already | attribution | names the base honestly |
| iso/apps/README.md:60 | Xubuntu binaries; the fifth is ours: | attribution | names the base honestly |
| iso/base/README.md:10 | `metaos.packages` — what a Cubic remaster must install on top of Xubuntu | attribution | names the base honestly |
| iso/base/README.md:18 | Xubuntu already ships the four programs the launchers start. Naming them on a | attribution | names the base honestly |
| iso/base/metaos.packages:5 | # Binaries the Xubuntu 24.04.5 base image already provides. Listed so the | attribution | names the base honestly |
| iso/theme/README.md:46 | picks up a `theme-name` that Xubuntu did not ship is exactly what a login run | attribution | names the base honestly |
| iso/tools/tokens_to_xfce.py:7 | file, so `xfce4-panel` fell back to Xubuntu's default and the "fully themed" | attribution | names the base honestly |
| metaos-theme/README.md:40 | no Apple/Ubuntu/Xubuntu marks in visible strings. | attribution | names the base honestly |
| metaos-theme/apply.sh:2 | # Apply MetaOS theme stack on a running Xubuntu system (or Cubic chroot). | attribution | names the base honestly |
| metaos-theme/fonts/FONTS.md:1 | # MetaOS 1.0 fonts (via fontsource MCP + Ubuntu archive) | compat | package/archive/image/field name the system needs |
| metaos-theme/fonts/FONTS.md:4 | - Mono: Ubuntu Mono (present in base) — no new package. | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| metaos-theme/greeter/KEYS.md:9 | `Xubuntu/lightdm-gtk-greeter` master, | attribution | names the base honestly |
| os-build/APP_INVENTORY.md:170 | - Not a rewritten Linux. The base is Debian/Xubuntu 24.04; the name, theme, | attribution | names the base honestly |
| os-build/APP_INVENTORY.md:172 | - Not a new kernel in the booted image — it boots Ubuntu's ARM64 kernel. | attribution | names the base honestly |
| os-build/BOOT_ON_32GB_MAC.md:105 | Calamares installed, or that a dock icon opened. Those need the Xubuntu base | attribution | names the base honestly |
| os-build/DEMO.md:57 | **Do not say:** "we wrote the kernel." It boots an Ubuntu ARM64 kernel; the | attribution | names the base honestly |
| os-build/DEMO.md:75 | - the account is `meta`, not `ubuntu` | attribution | names the base honestly |
| os-build/HACKATHON.md:16 | the Meta top bar. No Ubuntu anywhere on screen. | attribution | names the base honestly |
| os-build/HACKATHON.md:49 | / Meta identity, not Ubuntu / `sh os-build/identity/debrand.sh --check` → PASS, plus `lsb_release -a` on the image reading `Meta OS 1.0 (Ribbon)` / `ribbon` / `MetaOS` / | attribution | names the base honestly |
| os-build/HACKATHON.md:50 | / No `ubuntu` user or home / `rename_user.sh --check` → PASS, `grep -r /home/ubuntu` → 0, the account is `meta` / | attribution | names the base honestly |
| os-build/HACKATHON.md:108 | 3. *"What is still Ubuntu?"* — apt, the package names, `ID_LIKE=debian`, and the | compat | package/archive/image/field name the system needs |
| os-build/HACKATHON.md:122 | 6. Terminal — `cat /etc/os-release`, `uname -a`, and whether `apt` says Ubuntu | attribution | names the base honestly |
| os-build/INTEGRATION.md:3 | State of `/tmp/metaos.ext4` (16 GB, user `ubuntu`) as of 2026-11-03. | attribution | names the base honestly |
| os-build/INTEGRATION.md:12 | / 1 / power → desktop / lightdm autologin `ubuntu`, session `metaos` / installed / | attribution | names the base honestly |
| os-build/METAOS_1.0_12H_PLAN.md:6 | Method: Xubuntu core remastered with Cubic. x86_64, tested in UTM/VM. | attribution | names the base honestly |
| os-build/METAOS_1.0_12H_PLAN.md:20 | - **Hana — base + first boot.** Cubic project on the reference Xubuntu | attribution | names the base honestly |
| os-build/METAOS_1.0_12H_PLAN.md:69 | - Reference ISO is the shared testbed (Xubuntu 24.04.5, checksum-pinned); | attribution | names the base honestly |
| os-build/METAOS_1.0_RELEASE_CHECKLIST.md:45 | artifact itself is not built — two parts. (1) The base Xubuntu | attribution | names the base honestly |
| os-build/METAOS_1.0_RELEASE_CHECKLIST.md:49 | reference image is Xubuntu 24.04.5, SHA-256 verified against | attribution | names the base honestly |
| os-build/METAOS_1.0_RELEASE_CHECKLIST.md:100 | (1.0, merge-layers, H+4 apply + re-audit); dexubuntu pack built, | attribution | own tool name contains the substring; not a branding reference |
| os-build/METAOS_1.0_RELEASE_CHECKLIST.md:143 | the ISO artifact itself is still not built — the base Xubuntu | attribution | names the base honestly |
| os-build/METAOS_1.0_RELEASE_CHECKLIST.md:206 | ISO artifact itself is still not built — the base Xubuntu | attribution | names the base honestly |
| os-build/MILO_QA_1.0_AUDIT_2026-11-02.md:18 | - Hana — base + first boot (Cubic, reference Xubuntu ISO). | attribution | names the base honestly |
| os-build/MILO_QA_1.0_AUDIT_2026-11-02.md:29 | Del's claim: the reference Xubuntu 24.04.5 ISO is layered and | attribution | names the base honestly |
| os-build/MILO_QA_1.0_AUDIT_2026-11-02.md:36 | - `os-build/iso/BASE_FACTS.md` (Buffy, merged): reference is Xubuntu | attribution | names the base honestly |
| os-build/MILO_QA_1.0_AUDIT_2026-11-02.md:48 | not built — (1) The base Xubuntu ISO file is Del's own download; | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:1 | # Milo QA — dexubuntu verify audit (MetaOS 1.0) | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:4 | Source: `os-build/metaos1-base/dexubuntu/` on origin/main @77bff3aa | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:7 | Assignment: Pax room-1 LANDED note — "Milo: dexubuntu verify = 7 named | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:17 | 3. os-release has no xubuntu string | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:21 | 7. xubuntu asset dirs absent | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:24 | PRETTY_NAME="MetaOS 1.0", NAME="MetaOS", ID=metaos, ID_LIKE=ubuntu; | compat | package/archive/image/field name the system needs |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:33 | - Planted Xubuntu identity: 7/7 FAIL, exit 1 (matches Pax's README | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:60 | - /usr/share/xubuntu-artwork removal: verify checks only | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:61 | /usr/share/xubuntu-docs and /usr/share/backgrounds/xubuntu, NOT | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:62 | xubuntu-artwork. A leftover xubuntu-artwork dir would still PASS. | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:66 | - Package purge state itself (xubuntu-default-settings etc.): NOT | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:71 | add hosts, issue.net, motd, xubuntu-artwork, wallpaper default, and | attribution | names the base honestly |
| os-build/MILO_QA_DEXUBUNTU_VERIFY.md:77 | Hana/Buffy wire dexubuntu as step 3 in the base flow (after Hana | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:1 | # Milo QA: H+4 application path audit (OC1 theme apply + greeter vs frozen contracts, dexubuntu as cut-2 identity gate) | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:7 | PACKAGES), plus Pax's dexubuntu verify as the identity gate for cut 2. | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:17 | `metaos-theme/apply.sh` cannot complete on main as written. The dexubuntu | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:108 | ## Finding H4-6: dexubuntu verify as the cut-2 identity gate — sound for its 7 checks, with two open edges | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:110 | Re-read verbatim on main @f51f4d7: `os-build/metaos1-base/dexubuntu/verify-rootfs.sh` | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:111 | is the same 7 checks Pax chroot-tested (os-release PRETTY_NAME/NAME/no-xubuntu, | attribution | names the base honestly |
| os-build/MILO_QA_H4_APPLY.md:112 | lsb DISTRIB_ID, hostname, issue banner, xubuntu asset dirs absent), read-only, | attribution | names the base honestly |
| os-build/MILO_QA_H4_APPLY.md:116 | hosts, issue.net, motd, and xubuntu-artwork dir ARE handled by apply now | attribution | names the base honestly |
| os-build/MILO_QA_H4_APPLY.md:118 | dexubuntu audit are closed in code (still unexecuted against a real | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:120 | - Edge still OPEN: wallpaper default. Dexubuntu apply looks for | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:125 | is canonical — fix dexubuntu's WALL, or fix apply.sh's install dir? | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_APPLY.md:126 | - Edge still UNPROVEN: Plymouth. Dexubuntu apply only selects a MetaOS | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_H4_REAUDIT.md:61 | - Wallpaper path (Pax Q4 ruling confirmed on main): dexubuntu | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_MERGE_LAYERS.md:22 | - `os-build/iso/BASE_FACTS.md` (Buffy, merged): the reference Xubuntu | attribution | names the base honestly |
| os-build/MILO_QA_MERGE_LAYERS.md:77 | "the base Xubuntu ISO file is Del's own download; the byte-build | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:1 | # Milo QA — dexubuntu verify round 2 (the six round-1 gaps, checked read-only) | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:7 | xubuntu-artwork dir, wallpaper default, Plymouth, no live run." | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:13 | (`os-build/metaos1-base/dexubuntu/` identical between `77bff3aa` and | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:25 | - Xubuntu-identity fixture: hostname xubuntu, hosts `127.0.1.1 | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:26 | xubuntu`, issue.net Xubuntu text, motd 00-header echoing Xubuntu, | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:27 | `/usr/share/xubuntu-artwork` present, xfce4-desktop.xml pointing at | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:28 | an xubuntu wallpaper, Plymouth default symlink to an xubuntu theme. | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:32 | xubuntu-artwork dir, xfce4-desktop.xml last-image at dexubuntu's | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:42 | - V2-4 xubuntu-artwork: `/usr/share/xubuntu-artwork` does not exist | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:43 | (verify-rootfs.sh checks only `xubuntu-docs` and | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:44 | `backgrounds/xubuntu`, not this dir). | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:46 | dexubuntu's WALL, `/usr/share/backgrounds/metaos/meta-dusk.png`. | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:52 | - Xubuntu fixture: 0/6 — all six FAIL (as expected; the checks | attribution | names the base honestly |
| os-build/MILO_QA_VERIFY_ROUND2.md:54 | - Post-apply fixture (dexubuntu's own semantics): 6/6 — all six PASS. | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:63 | Dexubuntu's WALL is `/usr/share/backgrounds/metaos/meta-dusk.png` | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:66 | `metaos/` subdir). Dexubuntu's wallpaper step is guarded by | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:70 | confirmed from the dexubuntu side: V2-5 passes only under | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:71 | dexubuntu's subdir assumption and fails under OC1's actual layout. | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:72 | Question to Pax (V2-Q1): which path is canonical — fix dexubuntu's | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:81 | (the only `default.plymouth` reference outside dexubuntu's selector | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:82 | is none at all). Dexubuntu's Plymouth step only `--set`s among | attribution | own tool name contains the substring; not a branding reference |
| os-build/MILO_QA_VERIFY_ROUND2.md:89 | alternative — the boot lane, provision.sh, or dexubuntu itself? | attribution | own tool name contains the substring; not a branding reference |
| os-build/OC123_DEMO_4H.md:28 | Inputs: `/private/tmp/xubuntu-base.iso` (present), `/private/tmp/isowork/` (live tree), Hana specs, OC1 theme pack (copy by sha when posted), OC2 drop-ins (copy by sha when posted). | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:25 | - No Apple/Ubuntu trademarked assets or strings in anything shipped. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:58 | - **OC1C-012** Verify no Ubuntu/XFCE default branding survives | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:200 | - **OC1C-077** Confirm greeter shows MetaOS, no Xubuntu. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:216 | - **OC1C-085** Confirm no Ubuntu strings in the session. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:217 | Proof: the sweep in os-build/logs/OC1C-no-ubuntu.txt. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:218 | - **OC1C-086** Record remaining Ubuntu strings if any, with | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:219 | owner + fix. Proof: OC1C-no-ubuntu.txt. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:295 | - **OC1C-122** Confirm no "Xubuntu" in the boot menu. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:478 | - **OC1C-207** Confirm no Ubuntu strings in the installer. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:545 | - **OC1C-239** Grep the live system for "Xubuntu" remnants. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:546 | Proof: os-build/logs/OC1C-noxubuntu.txt. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:548 | Proof: the list in OC1C-noxubuntu.txt. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:549 | - **OC1C-241** Grep for Ubuntu trademark strings. | attribution | names the base honestly |
| os-build/OPENCODE1_TASKS_ISO.md:638 | - **OC1C-282** Confirm no Apple/Ubuntu trademarks shipped. | attribution | names the base honestly |
| os-build/OPENCODE2_500_STATUS.md:250 | - (f) Evince/atril spec-ack PROPOSAL for Hana (proposal only — her files untouched): Xubuntu 24.04.5 base ISO ships atril where `os-build/metaos1-base/packages.txt` KEEP lists `evince` (the line the s | attribution | names the base honestly |
| os-build/OPENCODE2_LAND_WALLS.md:32 | - OC2P-041: GUI-base spike, ONE attempt max: Xubuntu 24.04.5 base ISO exists (5.2G, verified manifests, Xfce present, evince→atril mismatch noted). Attempt desktop reach in QEMU snapshot mode; screend | attribution | names the base honestly |
| os-build/OPENCODE2_PROOF_LANE.md:35 | - OC2P-012: GUI-base spike, bounded: ONE attempt to get a desktop in QEMU (Xubuntu ISO only if | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:36 | - **OC3B-005** Confirm the start page names MetaOS, not Ubuntu. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:52 | - **OC3B-013** Confirm bookmarks contain no Ubuntu/Apple links. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:90 | - **OC3B-030** Confirm no Ubuntu branding in the file manager. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:167 | - **OC3B-067** Confirm no Ubuntu strings in terminal UI. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:206 | - **OC3B-085** Confirm no Ubuntu branding in settings. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:257 | - **OC3B-109** Confirm no Ubuntu branding in media apps. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:310 | - **OC3B-134** Confirm no Ubuntu branding in office apps. | attribution | names the base honestly |
| os-build/OPENCODE3_TASKS_500.md:570 | - **OC3B-256** Confirm no Ubuntu/Apple strings. | attribution | names the base honestly |
| os-build/PROOF_AGENT_PIPELINE.md:60 | ubuntu:24.04 bash -c 'mkdir -p /mnt; mount -o loop /disk.img /mnt; | compat | package/archive/image/field name the system needs |
| os-build/STATUS_2026-11-04.md:29 | / It is Meta OS, not Ubuntu / `/etc/os-release` → `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`; terminal prompt `metaos` / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:1 | # UBUNTU INVENTORY — every place the base distro still shows its name | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:18 | / `/etc/os-release` / `NAME="Meta OS"`, `VERSION="1.0 (Ribbon)"`, `ID=metaos`, `ID_LIKE=debian`, 0 Ubuntu strings / `cat` on the image / | compat | package/archive/image/field name the system needs |
| os-build/UBUNTU_INVENTORY.md:24 | / Boot splash / `Theme=metaos` in `/etc/plymouth/plymouthd.conf`; no `ubuntu-text` theme on disk / `cat`, `ls /usr/share/plymouth/themes` / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:25 | / Wallpapers / only `meta-*.png`; stock Ubuntu/Xubuntu wallpaper sets removed / `ls /usr/share/backgrounds` / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:26 | / Dock/panel icons / Meta icon set present; Ubuntu icon themes not used by the session / repo payload + image / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:28 | / Account name / `meta` (uid 1000), no `ubuntu` account, `/home/ubuntu` gone / `/etc/passwd`, `--check` / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:37 | **The account's display name still said Ubuntu.** `/etc/passwd` read | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:38 | `meta:x:1000:1000:Ubuntu:/home/meta:/bin/bash`. The GECOS field is what a greeter, | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:41 | field — so the OS called the user "Ubuntu" on any screen that shows a full name. | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:44 | still `Ubuntu`. Proven on a synthetic root under Linux: | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:48 | FAIL display name -- passwd still gives meta the full name Ubuntu | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:56 | payload greeter drop-in still said `autologin-user=ubuntu` while the account is | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:57 | `meta`, and both `build_iso.sh` and `theme_proof.sh` asserted `ubuntu` — so the | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:72 | / File / Why it says Ubuntu / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:75 | / ~~`/etc/skel/.bashrc:120`~~ / **fixed in the source, not yet on the image.** The appended block now reads "wins over the base image's `\u@\h` prompt", and `tools/fix_terminal_prompt.sh` also patches | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:76 | / `payload-theme/panel/xfce4-panel.xml:6` / geometry copied from the Xubuntu panel / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:81 | ## 4. Must keep saying Ubuntu or Debian — compatibility | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:86 | / `UBUNTU_CODENAME` in os-release / read by tools that compute the apt suite / | compat | package/archive/image/field name the system needs |
| os-build/UBUNTU_INVENTORY.md:89 | / `/usr/share/fonts/truetype/ubuntu/UbuntuMono*` / the terminal profile asks for Ubuntu Mono; it is a **font**, not branding / | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/UBUNTU_INVENTORY.md:90 | / `Humanity` icon theme's `ubuntuone-*` emblems / never drawn by our dock or panel; removing them only risks breaking the theme / | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:98 | says `DISTRIB_ID=MetaOS` — Ubuntu's own `lsb_release` script title-cases the | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:100 | If a judge notices, the honest answer is "Ubuntu's `lsb_release` capitalises it; | attribution | names the base honestly |
| os-build/UBUNTU_INVENTORY.md:111 | If `theme_proof.sh` still reports `autologin: ubuntu`, the payload and the | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:17 | / The Meta-branded Xubuntu image / `os-build/iso/` / boots, themed, apps missing, no face / | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:75 | **Goal:** a single run turns a stock Xubuntu rootfs into the Meta image. | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:85 | iso/../metaos1-base/dexubuntu/apply-in-chroot.sh   # de-Ubuntu the identity | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:90 | 3. Delete the duplicated work: `dexubuntu` and `brand.sh` both write | attribution | own tool name contains the substring; not a branding reference |
| os-build/WIRING_PLAN.md:101 | 1. **Pick the browser first — this is the blocker.** On Ubuntu 24.04 `chromium` | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:133 | `node:` specifiers, so **Node >= 16**; Ubuntu 24.04 ships 18, fine. | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:233 | 7. **Two `xfce4-desktop.xml` writers** (`dexubuntu`, `brand.sh`) — last writer | attribution | own tool name contains the substring; not a branding reference |
| os-build/WIRING_PLAN.md:266 | 1. `cat /etc/os-release` → `MetaOS 1.0`, `ID=metaos`, no Ubuntu/Xubuntu string | attribution | names the base honestly |
| os-build/WIRING_PLAN.md:268 | 2. No xubuntu package or asset dir on disk. | attribution | names the base honestly |
| os-build/face/APP_MATRIX.md:40 | ## launcher allow-list: Debian spike → Xubuntu 24.04.5 (honest mapping) | attribution | names the base honestly |
| os-build/face/APP_MATRIX.md:42 | Verified against `/private/tmp/xubuntu-base.iso` `casper/filesystem.manifest` | compat | package/archive/image/field name the system needs |
| os-build/face/APP_MATRIX.md:43 | (1876 lines, Xubuntu 24.04.5 Noble, hash `4ed869eb…` per `BASE_FACTS.md`). | attribution | names the base honestly |
| os-build/face/APP_MATRIX.md:49 | / Debian spike `ALLOW` (absent) / Xubuntu 24.04.5 reality / new `ALLOW` / evidence / | attribution | names the base honestly |
| os-build/face/APP_MATRIX.md:54 | / `orage` / absent (deprecated); no standalone calendar in base / `thunderbird` (`["thunderbird"]`) / `orage` absent, `gnome-calendar` absent; `thunderbird 2:1snap1-0ubuntu3` + `snap:thunderbird` pres | attribution | names the base honestly |
| os-build/face/APP_MATRIX.md:56 | / `chromium` / absent as deb / `firefox` (`["firefox","--new-window","about:blank"]`) / `chromium` absent; `firefox 1:1snap1-0ubuntu5` + `snap:firefox` present (default Xubuntu browser). `kiosk.sh` `e | attribution | names the base honestly |
| os-build/face/APP_MATRIX.md:60 | absent here, present in Xubuntu guest). | attribution | names the base honestly |
| os-build/face/SESSION.md:4 | Image: `/tmp/metaos.ext4` (Ubuntu 24.04 + XFCE, autologin session `metaos`, | attribution | names the base honestly |
| os-build/face/SESSION.md:5 | user `ubuntu`, browser epiphany 46.5 WebKitGTK). | attribution | names the base honestly |
| os-build/face/launcher.py:5 | Xubuntu 24.04.5 base (verified from casper/filesystem.manifest): | compat | package/archive/image/field name the system needs |
| os-build/face/launcher.py:12 | - chromium (absent as deb; Ubuntu shim) -> firefox (present as snap) | attribution | names the base honestly |
| os-build/face/meta-desktop.sh:34 | [ -n "$HOME_DIR" ] // HOME_DIR="${HOME:-/home/ubuntu}" | LEAK(Buffy) | HOME fallback /home/ubuntu — request to Buffy |
| os-build/face/meta-desktop.sh:48 | # user already has a Xubuntu panel file that wins over it. Copy the Meta one | attribution | names the base honestly |
| os-build/face/provision.sh:75 | # the greeter fell back to the schema defaults: the Ubuntu warty background | attribution | names the base honestly |
| os-build/face/provision.sh:77 | # Ubuntu logo. Two independent fixes, on purpose: | attribution | names the base honestly |
| os-build/face/provision.sh:80 | #      build whose schemas are not recompiled still cannot show Ubuntu's. | attribution | names the base honestly |
| os-build/face/provision.sh:115 | # unity-greeter kept reading Ubuntu's art out of the old cache. | attribution | names the base honestly |
| os-build/face/provision.sh:125 | # The mark: unity-greeter's stock logo is the Ubuntu logo, at a fixed path. | attribution | names the base honestly |
| os-build/face/provision.sh:132 | # The background: the schema's default path is the Ubuntu warty image. This | attribution | names the base honestly |
| os-build/face/provision.sh:138 | "$ROOT/usr/share/backgrounds/warty-final-ubuntu.png" | attribution | names the base honestly |
| os-build/face/provision.sh:139 | echo "provision(face): greeter background default -> Meta ASCII (no Ubuntu art)" | attribution | names the base honestly |
| os-build/face/provision.sh:190 | FontName=Ubuntu Mono 11 | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/face/provision.sh:223 | # cache compiled before that override shipped still holds Ubuntu's emerald | attribution | names the base honestly |
| os-build/face/provision.sh:224 | # background and Ubuntu logo — the green screen the user kept hitting. So the | attribution | names the base honestly |
| os-build/face/provision.sh:490 | # awk, not python3: provision also runs inside a bare ubuntu container for | attribution | names the base honestly |
| os-build/identity/debrand.sh:2 | # debrand.sh — take Ubuntu's name off a Meta OS root, keep what apt needs. | attribution | names the base honestly |
| os-build/identity/debrand.sh:50 | grep -q "ubuntu" "$f" && u=no // u=ok | attribution | names the base honestly |
| os-build/identity/debrand.sh:54 | say "$f no-ubuntu" "$u" "file still mentions ubuntu" | attribution | names the base honestly |
| os-build/identity/debrand.sh:100 | # These two print Canonical help links and Ubuntu's news feed at every login. | attribution | names the base honestly |
| os-build/identity/debrand.sh:109 | # Anything a person can open that still says Xubuntu/Ubuntu in a menu or a | attribution | names the base honestly |
| os-build/identity/debrand.sh:113 | grep -rl "Xubuntu" "$ROOT/$d" 2>/dev/null / while read -r f; do | attribution | names the base honestly |
| os-build/identity/debrand.sh:114 | sed -i 's/Xubuntu/Meta OS/g; s/Ubuntu/Meta OS/g' "$f" | attribution | names the base honestly |
| os-build/identity/debrand2.sh:2 | # debrand2.sh — the Ubuntu leftovers a `ls` can still find. | attribution | names the base honestly |
| os-build/identity/debrand2.sh:6 | # state, which is where the last visible Ubuntu lives: | attribution | names the base honestly |
| os-build/identity/debrand2.sh:8 | #   1. /usr/share/plymouth/themes/ubuntu-text still ships even though the active | attribution | names the base honestly |
| os-build/identity/debrand2.sh:9 | #      theme is `metaos`. Dead weight with Ubuntu's name on it. | attribution | names the base honestly |
| os-build/identity/debrand2.sh:11 | #      Xubuntu's stock wallpapers. One of them, xfce-shapes.svg, is still named | attribution | names the base honestly |
| os-build/identity/debrand2.sh:13 | #      reports a different monitor name can paint Ubuntu's wallpaper instead of | attribution | names the base honestly |
| os-build/identity/debrand2.sh:33 | # 1. no ubuntu plymouth theme on disk | attribution | names the base honestly |
| os-build/identity/debrand2.sh:34 | n=$(find "$ROOT/usr/share/plymouth/themes" -maxdepth 1 -name 'ubuntu*' 2>/dev/null / wc -l / tr -d ' ') | attribution | names the base honestly |
| os-build/identity/debrand2.sh:35 | [ "$n" = 0 ] && say "plymouth ubuntu themes removed" ok "" \ | attribution | names the base honestly |
| os-build/identity/debrand2.sh:36 | // say "plymouth ubuntu themes removed" no "$n ubuntu* theme dir(s) left" | attribution | names the base honestly |
| os-build/identity/debrand2.sh:43 | # 3. stock Xubuntu wallpapers gone | attribution | names the base honestly |
| os-build/identity/debrand2.sh:76 | for d in "$ROOT"/usr/share/plymouth/themes/ubuntu*; do | attribution | names the base honestly |
| os-build/identity/rename_user.sh:2 | # rename the live user ubuntu -> meta. | attribution | names the base honestly |
| os-build/identity/rename_user.sh:4 | # This is the last place Ubuntu's name is still visible to a person: the home | attribution | names the base honestly |
| os-build/identity/rename_user.sh:23 | OLD=ubuntu | attribution | names the base honestly |
| os-build/identity/rename_user.sh:60 | # the account does not touch it, and it said "Ubuntu" for weeks after the | attribution | names the base honestly |
| os-build/identity/rename_user.sh:66 | say "display name" no "passwd still gives $NEW the full name Ubuntu" | attribution | names the base honestly |
| os-build/identity/rename_user.sh:84 | # group member lists:  sudo:x:27:ubuntu  ->  sudo:x:27:meta | attribution | names the base honestly |
| os-build/identity/rename_user.sh:110 | #     "Ubuntu" is Ubuntu's name still printed on a Meta account. | attribution | names the base honestly |
| os-build/identity/rename_user.sh:142 | #    matters after a rename; drop them so no file on screen says /home/ubuntu. | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:3 | File: `/private/tmp/xubuntu-base.iso` (5,211,408,384 bytes ≈ 4.9 GiB). | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:4 | Identity: **Xubuntu 24.04.5 LTS "Noble Numbat" — Release amd64 (20260908.2)**, | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:10 | $ shasum -a 256 /private/tmp/xubuntu-base.iso | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:13 | $ curl -fsSL https://cdimage.ubuntu.com/xubuntu/releases/24.04.5/release/SHA256SUMS / grep desktop-amd64 | compat | package/archive/image/field name the system needs |
| os-build/iso/BASE_FACTS.md:14 | 4ed869ebf2b9f2f6118c1b60b9ed07576e8fe3d5cdfe10aae06869e669878b81 *xubuntu-24.04.5-desktop-amd64.iso | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:36 | `install-sources.yaml` declares two sources (`xubuntu-desktop-minimal` → | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:37 | `minimal.squashfs`, default false; `xubuntu-desktop` → | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:45 | / `plymouth`, `plymouth-label`, `-theme-xubuntu-*` / 5 / splash stack present; our theme can replace theirs / | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:50 | / `xubuntu-desktop`, `xubuntu-desktop-minimal` / 2.262 each / metapackages / | attribution | names the base honestly |
| os-build/iso/BASE_FACTS.md:52 | / `ubiquity`, `subiquity`, `ubuntu-desktop-provision` / 0 each / not present as debs / | compat | package/archive/image/field name the system needs |
| os-build/iso/INITRD_DIFF.md:14 | / stock initrd / `/tmp/iso-mnt/casper/initrd` (bind-mounted `:ro` into a throwaway `ubuntu:24.04` container) / 99,906,755 B / | compat | package/archive/image/field name the system needs |
| os-build/iso/INITRD_DIFF.md:37 | - `scripts/casper-bottom`: only delta is `48xubuntu_maybe_ubiquity` present in | compat | package/archive/image/field name the system needs |
| os-build/iso/INITRD_DIFF.md:50 | (`strings` → `#31~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC`). No mismatch. | attribution | names the base honestly |
| os-build/iso/INITRD_DIFF.md:68 | - `etc/casper.conf` (live-user identity): identical (`ubuntu`/`ubuntu`/…). | attribution | names the base honestly |
| os-build/iso/INITRD_DIFF.md:109 | / H4 / Missing `48xubuntu_maybe_ubiquity` / casper-bottom ORDER / RULED OUT: post-medium installer shim; and the panic precedes it. / | compat | package/archive/image/field name the system needs |
| os-build/iso/INITRD_DIFF.md:164 | (Xubuntu branding, no `layerfs-path=`, no `console=ttyS0`, Sep-08 mtimes) | attribution | names the base honestly |
| os-build/iso/INITRD_DIFF.md:183 | docker run --rm -v /tmp/iso-mnt:/mnt:ro ubuntu:24.04 bash -c \ | compat | package/archive/image/field name the system needs |
| os-build/iso/LANE_REPORT.md:68 | 3. **Base ISO is a parameter.** The plan names Xubuntu + Cubic; Hana's lane | attribution | names the base honestly |
| os-build/iso/LANE_REPORT.md:71 | 4. **Live-session user is copied by unpackfs.** Ubuntu flavours solve this | attribution | names the base honestly |
| os-build/iso/LANE_REPORT.md:80 | `xubuntu-24.04.5-desktop-amd64.iso` ships `casper/minimal*.squashfs` | compat | package/archive/image/field name the system needs |
| os-build/iso/MERGE_NOTES.md:2 | Base verified: xubuntu-24.04.5-desktop-amd64.iso, sha256 4ed869eb (match). | attribution | names the base honestly |
| os-build/iso/MERGE_NOTES.md:21 | fonts-inter — note: calamares-settings-ubuntu does not exist; branding | attribution | names the base honestly |
| os-build/iso/MERGE_NOTES.md:50 | palette to be verified on real hardware. Session still says xubuntu | attribution | names the base honestly |
| os-build/iso/PAX_BLOCKERS.md:21 | 3. **Base ISO point release.** The plan says Xubuntu core + Cubic; it does | attribution | names the base honestly |
| os-build/iso/PAX_BLOCKERS.md:30 | machine is the official Xubuntu 24.04.5 desktop image, checksum-verified, | attribution | names the base honestly |
| os-build/iso/PIPELINE.md:3 | `merge-layers.sh` is the full reproducible build: layered Xubuntu base in, | attribution | names the base honestly |
| os-build/iso/PIPELINE.md:19 | / Base ISO: `xubuntu-24.04.5-desktop-amd64.iso` / `shasum -a 256 <base>` must print `4ed869eb…69e8` (full hash in `BASE_FACTS.md`); or verify against Canonical's `SHA256SUMS` / | attribution | names the base honestly |
| os-build/iso/PIPELINE.md:37 | BASE=/private/tmp/xubuntu-base.iso   # adjust | attribution | names the base honestly |
| os-build/iso/PIPELINE.md:46 | ubuntu:24.04 bash -c ' | compat | package/archive/image/field name the system needs |
| os-build/iso/PIPELINE.md:110 | / live session still says "xubuntu" (hostname/branding) / base strings survive the merge / theme-lane follow-up (`.disk/info` is already rewritten to `MetaOS 1.0 LTS`) / | attribution | names the base honestly |
| os-build/iso/README.md:8 | Base plan: Xubuntu core remastered with Cubic, x86_64, tested in UTM/VM. | attribution | names the base honestly |
| os-build/iso/README.md:54 | sudo os-build/iso/build_iso.sh --iso ~/Downloads/xubuntu-24.04.3-desktop-amd64.iso \ | attribution | names the base honestly |
| os-build/iso/README.md:77 | Base ISO is a parameter on purpose: the plan names Xubuntu+Cubic, and the | attribution | names the base honestly |
| os-build/iso/README.md:83 | this machine (`/private/tmp/xubuntu-base.iso`) is the official | attribution | names the base honestly |
| os-build/iso/README.md:84 | `xubuntu-24.04.5-desktop-amd64.iso` (hash matches Canonical's SHA256SUMS), | attribution | names the base honestly |
| os-build/iso/ROOM1_POST.md:21 | - Base reality, measured: `/private/tmp/xubuntu-base.iso` is the official | attribution | names the base honestly |
| os-build/iso/build_iso.sh:39 | # Ubuntu flavour ISOs are not uniform any more. Some 24.04 flavour images | attribution | names the base honestly |
| os-build/iso/build_iso.sh:268 | # Ubuntu's casper checks this file for the extracted size. | attribution | names the base honestly |
| os-build/iso/build_iso.sh:282 | # instead of hand-writing isohybrid args per Ubuntu release. This is the | attribution | names the base honestly |
| os-build/iso/calamares/README.md:64 | (`Xubuntu`/`Ubuntu`/`ubiquity`) appear solely in config comments and | compat | package/archive/image/field name the system needs |
| os-build/iso/calamares/README.md:65 | the machine-readable `ID_LIKE=ubuntu` os-release field (kept for | attribution | documents a deliberate compat decision |
| os-build/iso/calamares/README.md:145 | 3. `ID_LIKE=ubuntu` in `/etc/metaos-release`: deliberate for | attribution | documents a deliberate compat decision |
| os-build/iso/calamares/meta-branding.sh:33 | ID_LIKE=ubuntu | LEAK(OS-2) | writes ID_LIKE=ubuntu and copies metaos-release over /etc/os-release — request to OS-2 |
| os-build/iso/calamares/modules/displaymanager.conf:3 | # Xubuntu base uses LightDM. basicSetup is off because the Meta greeter | attribution | names the base honestly |
| os-build/iso/calamares/modules/packages.conf:8 | # ubiquity is in the list because a Xubuntu base may still carry it; on a | compat | package/archive/image/field name the system needs |
| os-build/iso/calamares/modules/unpackfs.conf:3 | # Ubuntu live media mounts the ISO at /cdrom and the classic layout ships | attribution | names the base honestly |
| os-build/iso/calamares/modules/unpackfs.conf:9 | # MEASURED WARNING: the reference base xubuntu-24.04.5-desktop-amd64.iso | attribution | names the base honestly |
| os-build/iso/calamares/modules/users.conf:14 | #     comment says to add that group to defaultGroups. Ubuntu's equivalent is | attribution | names the base honestly |
| os-build/iso/calamares/settings.conf:4 | # provision.sh. The sequence is the stock Ubuntu-flavour Calamares order | attribution | names the base honestly |
| os-build/iso/finalize-iso-tree.sh:13 | s = s.replace('Try or Install Xubuntu', 'Try or Install MetaOS') | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/finalize-iso-tree.sh:14 | s = s.replace('Xubuntu (safe graphics)', 'MetaOS (safe graphics)') | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/payload-theme/README.md:40 | no Apple/Ubuntu/Xubuntu marks in visible strings. | attribution | names the base honestly |
| os-build/iso/payload-theme/README.md:59 | `rename_user.sh` creates — when this said `ubuntu` and the account was | attribution | names the base honestly |
| os-build/iso/payload-theme/README.md:66 | - `gtk.css`: Inter-first stack; terminal profile: Ubuntu Mono 11 | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/apply.sh:14 | # Refuses when neither Inter nor Ubuntu Mono is present on the target. | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/apply.sh:133 | # NOTE: /etc/os-release is a symlink to ../usr/lib/os-release on Ubuntu. | attribution | names the base honestly |
| os-build/iso/payload-theme/apply.sh:158 | if ls "$ROOT"/usr/share/fonts/truetype/ubuntu/UbuntuMono* >/dev/null 2>&1; then have_mono=1; fi | attribution | names the base honestly |
| os-build/iso/payload-theme/apply.sh:162 | DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends fonts-inter fonts-ubuntu | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/apply.sh:164 | ls /usr/share/fonts/truetype/ubuntu/UbuntuMono* >/dev/null 2>&1 // { echo "apply-GATE-FAIL: Ubuntu Mono still absent after apt" >&2; exit 1; } | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/apply.sh:166 | echo "apply-GATE-FAIL: fonts missing on target (inter=$have_inter mono=$have_mono); install fonts-inter + fonts-ubuntu, then re-run" >&2 | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/fonts/FONTS.md:10 | / Ubuntu Mono (monospace) / `fonts-ubuntu` (ships in the base image) / Ubuntu Font Licence 1.0 (grant recorded in `/usr/share/doc/fonts-ubuntu/copyright`, upstream `https://design.ubuntu.com/font/`) / | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/greeter/10-metaos-live.conf:3 | # image's `ubuntu` account and rewrites the casper USERNAME and this autologin | attribution | names the base honestly |
| os-build/iso/payload-theme/greeter/10-metaos-live.conf:4 | # line together. When this file said `ubuntu` and the account was already | attribution | names the base honestly |
| os-build/iso/payload-theme/greeter/99_metaos-greeter.gschema.override:6 | # conf file left the login screen on the schema defaults: the Ubuntu "warty" | attribution | names the base honestly |
| os-build/iso/payload-theme/greeter/99_metaos-greeter.gschema.override:7 | # background and the stock Ubuntu logo. On a Meta OS build that file is not | attribution | names the base honestly |
| os-build/iso/payload-theme/greeter/99_metaos-greeter.gschema.override:14 | # whose schemas are not recompiled still shows Meta art, never Ubuntu's. | attribution | names the base honestly |
| os-build/iso/payload-theme/greeter/KEYS.md:9 | `Xubuntu/lightdm-gtk-greeter` master, | attribution | names the base honestly |
| os-build/iso/payload-theme/gtk/gtk.css:8 | font-family: 'Inter', 'Ubuntu', system-ui, sans-serif; | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/identity/os-release:6 | ID_LIKE="ubuntu debian" | LEAK(mine) | ID_LIKE has ubuntu, CODENAME noble, VERSION short — contradicts contract; fixed this lane |
| os-build/iso/payload-theme/identity/os-release:8 | UBUNTU_CODENAME=noble | LEAK(mine) | ID_LIKE has ubuntu, CODENAME noble, VERSION short — contradicts contract; fixed this lane |
| os-build/iso/payload-theme/panel/xfce4-panel.xml:6 | Geometry is copied from the Xubuntu panel that already works on this | attribution | names the base honestly |
| os-build/iso/payload-theme/terminal/metaos-terminal-profile.txt:2 | # Font: Ubuntu Mono (Ubuntu Font Licence 1.0, package fonts-ubuntu — present | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/terminal/metaos-terminal-profile.txt:12 | FontName=Ubuntu Mono 11 | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/theme_proof.sh:120 | # Allowlist: the live username `ubuntu` (link 1 — must stay) wherever it | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:123 | if grep -i 'ubuntu\/xubuntu' "$ROOT$1" 2>/dev/null / grep -v -E '^(autologin-user=meta/.*USERNAME=meta.*)$' / grep -q .; then | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:136 | if [ -z "$hits" ]; then ok "brand-owned: lane D files carry no ubuntu/xubuntu"; else no "brand-owned" "$hits"; fi | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:141 | if grep -i -E '^(Name/Comment/GenericName)' "$f" 2>/dev/null / grep -qi 'ubuntu\/xubuntu'; then thits="$thits $(basename "$f")"; fi | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:145 | if grep -qi 'ubuntu\/xubuntu' "$ROOT$f" 2>/dev/null; then thits="$thits $f"; fi | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:148 | if grep -v -E '^(ID_LIKE/UBUNTU_CODENAME)=' "$ROOT/etc/os-release" 2>/dev/null / grep -qi 'ubuntu'; then oros="hit"; fi | compat | package/archive/image/field name the system needs |
| os-build/iso/payload-theme/theme_proof.sh:150 | if [ -z "$thits" ]; then ok "brand-tree: .desktop Name/Comment + greeter/panel carry no ubuntu/xubuntu"; else no "brand-tree" "$thits"; fi | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:185 | ls "$ROOT"/usr/share/fonts/truetype/ubuntu/UbuntuMono* >/dev/null 2>&1 // fmiss="$fmiss UbuntuMono-files" | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:187 | grep -q '^FontName=Ubuntu Mono 11' "$ROOT/usr/share/doc/metaos/terminal-profile.txt" 2>/dev/null // fmiss="$fmiss terminal-profile" | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/theme_proof.sh:189 | if [ -z "$fmiss" ]; then ok "fonts: Inter + Ubuntu Mono installed and referenced (gtk+greeter+terminal)"; else no "fonts" "$fmiss"; fi | compat | real font/package name (fonts-ubuntu, Ubuntu Mono), not branding |
| os-build/iso/payload-theme/theme_proof.sh:195 | grep -qi 'ubuntu\/xubuntu' "$ROOT/boot/grub/themes/metaos/theme.txt" 2>/dev/null && gmiss="$gmiss brand-string" | attribution | names the base honestly |
| os-build/iso/payload-theme/theme_proof.sh:198 | if [ -z "$gmiss" ]; then ok "grub: Meta OS 1.0 title, timeout 10, no ubuntu strings"; else no "grub" "$gmiss"; fi | attribution | names the base honestly |
| os-build/iso/provision-all.sh:49 | # 1) packages the face and the relay need. Epiphany is the browser: on Ubuntu | attribution | names the base honestly |
| os-build/iso/provision-all.sh:71 | # 3) identity: de-Ubuntu, then the brand pass | attribution | names the base honestly |
| os-build/iso/provision-all.sh:73 | DEX="$REPO/os-build/metaos1-base/dexubuntu/apply-in-chroot.sh" | attribution | own tool name contains the substring; not a branding reference |
| os-build/iso/provision-all.sh:75 | step 3 "identity (dexubuntu)" sh "$DEX" | attribution | own tool name contains the substring; not a branding reference |
| os-build/iso/provision-all.sh:77 | echo "=== [3] SKIP identity (no dexubuntu)" | attribution | own tool name contains the substring; not a branding reference |
| os-build/iso/provision.sh:198 | # kept Ubuntu's name on the user, the wallpapers and the dead plymouth theme | attribution | names the base honestly |
| os-build/iso/repack-iso.sh:6 | # Optional: EXPECTED_SHA256=<hex> (default: the pinned Xubuntu 24.04.5 sum | attribution | names the base honestly |
| os-build/iso/test/test_stages.sh:208 | menuentry "Try or Install Xubuntu" { | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/test/test_stages.sh:209 | linux   /casper/vmlinuz  file=$cdrom/preseed/xubuntu.seed --- quiet splash | compat | package/archive/image/field name the system needs |
| os-build/iso/test/test_stages.sh:211 | menuentry "Xubuntu (safe graphics)" { | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/test/test_stages.sh:225 | && ! grep -q "Xubuntu" "$tmp/tree/boot/grub/grub.cfg"; then | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/test/test_stages.sh:226 | ok "Meta branding strings replace Xubuntu" | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/tools/check_configs.py:336 | FLAVOURS = re.compile(r"\b(Ubuntu/Xubuntu/Lubuntu/Kubuntu/KDE neon)\b", re.IGNORECASE) | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/tools/check_slideshow.py:12 | 6. no base-flavour / vendor strings (Ubuntu, Xubuntu, Apple, macOS) | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/iso/tools/check_slideshow.py:33 | r"\b(Ubuntu/Xubuntu/Apple/macOS)\b", re.IGNORECASE | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/lanes/AGENT_1_REPORT.md:145 | 4. No logout/login, fresh-home, or Xubuntu-upgrade-path runs (tasks 110–112): | attribution | names the base honestly |
| os-build/lanes/AGENT_4_REPORT.md:44 | ii  libgl1-mesa-dri:arm64  25.2.8-0ubuntu0.24.04.4  free implementation of the | generated | pasted dpkg version string; evidence, not identity |
| os-build/lanes/AGENT_4_REPORT.md:177 | machine …)". Says Meta OS, never Ubuntu (`grep -ci ubuntu` → 0). No | attribution | names the base honestly |
| os-build/lanes/AGENT_STATUS_2026-11-03.md:32 | 1. `agent-1` `52b00701` — Ubuntu-identity cleanup (`rename_user.sh`, greeter | attribution | names the base honestly |
| os-build/lanes/AGENT_STATUS_2026-11-03.md:33 | drop-in, `UBUNTU_INVENTORY.md`, `HACKATHON.md`). 4 files, fast-forward. | attribution | names the base honestly |
| os-build/lanes/WAKEUP_AGENTIC.md:24 | regenerates it as the tree moves). 164 of those are the de-Ubuntu sweep. | attribution | names the base honestly |
| os-build/lanes/WAKEUP_AGENTIC.md:78 | **5. Ubuntu's name is off the box.** `os-build/identity/debrand.sh` rewrote | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:1 | # Wake-up — apps are windows, and Ubuntu is out of the user | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:20 | appended block runs last, so it wins over Ubuntu's green `\u@\h`. | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:21 | Also found: `/etc/bash.bashrc.d/metaos.sh` had never executed, because Ubuntu's | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:32 | **4. Ubuntu's name is off the user.** | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:35 | casper's USERNAME and every `/home/ubuntu` path. Before the change `--check` | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:36 | failed five assertions; after, all six PASS, and `grep -r /home/ubuntu` over | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:46 | / No `ubuntu` account or home / `rename_user.sh --check` → 6 PASS, 0 leftover paths / | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:53 | ## What is still Ubuntu, honestly | attribution | names the base honestly |
| os-build/lanes/WAKEUP_R3.md:59 | - **`/usr/share/plymouth/themes/ubuntu-text/`** still ships. The active theme is | attribution | names the base honestly |
| os-build/metaos1-base/README.md:10 | - A Cubic project definition for an Xubuntu-core remaster (see | attribution | names the base honestly |
| os-build/metaos1-base/README.md:30 | Xubuntu ISO, so no boot was run here. | attribution | names the base honestly |
| os-build/metaos1-base/README.md:36 | H+0 lane. This slice uses Xubuntu defaults until the kit lands and | attribution | names the base honestly |
| os-build/metaos1-base/README.md:43 | ## Slice 2 — base flow wiring (dexubuntu step 3) | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:45 | Pax's room-1 order 2026-11-02 ~23:52 EST: wire dexubuntu as step 3 | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:49 | script stays OC1's, the dexubuntu scripts stay Pax's gap-fill, and | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:53 | → `dexubuntu/apply-in-chroot.sh` → `dexubuntu/verify-rootfs.sh` | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:58 | named, and both dexubuntu scripts pass `sh -n`. | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:61 | sandbox, no boot is run here, and dexubuntu on a real layered | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:62 | image is still unproven — Milo's dexubuntu audit records the | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/README.md:98 | dexubuntu apply, then the verify-rootfs gate at 7/7, all before | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/cubic-spec.md:3 | Tool: Cubic (Custom Ubuntu ISO Creator), run on the cut machine. | attribution | expands the acronym Cubic; honest |
| os-build/metaos1-base/cubic-spec.md:4 | Base: the reference Xubuntu ISO, x86_64 — Xubuntu 24.04.5, per the | attribution | names the base honestly |
| os-build/metaos1-base/cubic-spec.md:17 | identity steps below are the order Pax's dexubuntu README states, | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/cubic-spec.md:38 | `dexubuntu/apply-in-chroot.sh`. It stamps hostname `metaos`, | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/cubic-spec.md:40 | motd banners, purges the branding-only Xubuntu packages, points | attribution | names the base honestly |
| os-build/metaos1-base/cubic-spec.md:47 | `dexubuntu/verify-rootfs.sh` against the chroot rootfs. All 7 | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/cubic-spec.md:49 | os-release free of the Xubuntu string, lsb-release DISTRIB_ID, | attribution | names the base honestly |
| os-build/metaos1-base/cubic-spec.md:50 | hostname, issue banner, Xubuntu asset dirs absent). Any FAIL is | attribution | names the base honestly |
| os-build/metaos1-base/cubic-spec.md:66 | 8. Leave the installer exactly as Xubuntu/Calamares ships it. The | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/README.md:1 | # dexubuntu — MetaOS 1.0 identity step | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/README.md:3 | Removes the Xubuntu identity from the remastered image and stamps MetaOS | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/README.md:24 | (NAME/PRETTY_NAME "MetaOS 1.0", ID=metaos, ID_LIKE=ubuntu) | compat | package/archive/image/field name the system needs |
| os-build/metaos1-base/dexubuntu/README.md:26 | - Purges branding-only packages: `xubuntu-default-settings`, | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/README.md:27 | `xubuntu-wallpapers`, `xubuntu-artwork`, `xubuntu-docs`; removes their | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/README.md:36 | (os-release x3, lsb-release, hostname, issue banner, xubuntu asset dirs | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/README.md:40 | Xubuntu-identity rootfs — verify failed 7/7 before, apply exited 0, | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:10 | echo "[dexubuntu] hostname + hosts" | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:18 | echo "[dexubuntu] os-release / lsb-release / issue" | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:24 | echo "[dexubuntu] motd" | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:30 | echo "[dexubuntu] purge xubuntu identity packages (branding only)" | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:31 | # xubuntu-default-settings ships the Xubuntu session defaults + branding; | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:32 | # xubuntu-wallpapers / xubuntu-artwork are pure identity assets. The Xfce | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:36 | apt-get purge -y xubuntu-default-settings xubuntu-wallpapers xubuntu-artwork xubuntu-docs 2>/dev/null // true | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:39 | rm -rf /usr/share/backgrounds/xubuntu /usr/share/xubuntu-docs /usr/share/xubuntu-artwork 2>/dev/null // true | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:41 | echo "[dexubuntu] default session wallpaper + greeter background" | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:62 | echo "[dexubuntu] plymouth default theme name (artwork is Buffy/OC1 lane)" | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:71 | echo "[dexubuntu] done" | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/dexubuntu/identity/os-release:7 | ID_LIKE=ubuntu | LEAK(Pax) | ID_LIKE=ubuntu in Pax gap-fill payload — request to owner |
| os-build/metaos1-base/dexubuntu/identity/os-release:12 | UBUNTU_CODENAME=noble | LEAK(Pax) | ID_LIKE=ubuntu in Pax gap-fill payload — request to owner |
| os-build/metaos1-base/dexubuntu/verify-rootfs.sh:3 | # no Xubuntu identity in the files a user actually sees. Prints one line | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/verify-rootfs.sh:12 | if grep -qi 'xubuntu' "$ROOT/etc/os-release" 2>/dev/null; then chk "os-release has no xubuntu string" 1; else chk "os-release has no xubuntu string" 0; fi | attribution | names the base honestly |
| os-build/metaos1-base/dexubuntu/verify-rootfs.sh:16 | if [ -e "$ROOT/usr/share/xubuntu-docs" ] // [ -e "$ROOT/usr/share/backgrounds/xubuntu" ]; then chk "xubuntu asset dirs absent" 1; else chk "xubuntu asset dirs absent" 0; fi | attribution | names the base honestly |
| os-build/metaos1-base/hplus4-evidence-prep.md:16 | 1. Identity gate on the cut rootfs: `dexubuntu/verify-rootfs.sh` | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/hplus4-evidence-prep.md:39 | - Dexubuntu verify checks 7 items. It does not check the hosts | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/hplus4-evidence-prep.md:44 | - Real-image execution of dexubuntu is BLOCKED on the | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/hplus4-evidence-prep.md:46 | there being no base ISO on this host, per Milo's dexubuntu | attribution | own tool name contains the substring; not a branding reference |
| os-build/metaos1-base/packages.txt:4 | #   KEEP: shipped by Xubuntu core already; listed so a cut operator can | attribution | names the base honestly |
| os-build/metaos1-base/packages.txt:8 | # Names are Ubuntu archive package names. No third-party repo is added | compat | package/archive/image/field name the system needs |
| os-build/metaos1-base/packages.txt:9 | # by this slice, and no package outside the Ubuntu archive is named. | compat | package/archive/image/field name the system needs |
| os-build/metaos1-base/packages.txt:11 | # KEEP (Xubuntu core already ships these; spot-check only) | attribution | names the base honestly |
| os-build/metaos1-base/validate.py:16 | dexubuntu/apply-in-chroot.sh — names verify-rootfs.sh as the | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/metaos1-base/validate.py:17 | gate, and both dexubuntu scripts pass `sh -n`. | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/metaos1-base/validate.py:123 | dex_pos = spec.find("dexubuntu/apply-in-chroot.sh") | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/metaos1-base/validate.py:127 | check("flow: dexubuntu step named after theme", | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/metaos1-base/validate.py:131 | for script_name in ("dexubuntu/apply-in-chroot.sh", | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/metaos1-base/validate.py:132 | "dexubuntu/verify-rootfs.sh"): | attribution | tool/test that detects or rewrites the word; the fixer, not the leak |
| os-build/research/ecosystem-watch.md:86 | - **Linux prebuilt needs glibc 2.35 or later** (project's words: Ubuntu 22.04, | attribution | names the base honestly |
| os-build/tools/fix_terminal_prompt.sh:6 | #   1. The prompt read `ubuntu@metaos` in Ubuntu's green. The live user is | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/fix_terminal_prompt.sh:7 | #      still `ubuntu` (autologin, home, sudoers all keyed on it), so the | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/fix_terminal_prompt.sh:12 | #      Ubuntu's /etc/bash.bashrc has no drop-in loop, so the spinning-logo | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/fix_terminal_prompt.sh:17 | # after Ubuntu's own colour block, and the last assignment wins. No python, | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/fix_terminal_prompt.sh:29 | for f in "$ROOT/etc/skel/.bashrc" "$ROOT/home/meta/.bashrc" "$ROOT/home/ubuntu/.bashrc"; do | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/fix_terminal_prompt.sh:66 | # Show it for whoever actually logs in: meta first, the legacy ubuntu path | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/fix_terminal_prompt.sh:68 | for _f in "$ROOT/home/meta/.bashrc" "$ROOT/home/ubuntu/.bashrc"; do | compat | must handle the legacy /home/ubuntu path after a rename |
| os-build/tools/install_agent_runtime.sh:28 | -v "$IMAGE:/disk.img" -v "$REPO:/repo:ro" ubuntu:24.04 bash -c ' | compat | package/archive/image/field name the system needs |
| os-build/tools/set_spark_key.sh:14 | # macOS cannot mount ext4, so the write happens inside a throwaway ubuntu | attribution | names the base honestly |
| os-build/tools/set_spark_key.sh:42 | -e EXPECT_SHA="${EXPECT_SHA:-}" ubuntu:24.04 bash -c "$1" | compat | package/archive/image/field name the system needs |
| os-build/tools/sync_image.sh:70 | ubuntu:24.04 bash -s <<'CONTAINER' | compat | package/archive/image/field name the system needs |
| os/plan/LAYER_PLAN.md:69 | - **Debian 12 (bookworm), amd64, one base only.** Rejected and not revisited: Ubuntu (snap stack fights the appliance model), Alpine (musl + OpenRC re-solves supervision systemd gives free), Arch (a m | attribution | names the base honestly |
| os/plan/META_OS.md:16 | 2. **Bootable agent images.** Red Hat's Tank-OS is a bootable, image-based Linux appliance dedicated to running OpenClaw; U-Claw is a bootable Ubuntu USB built for OpenClaw. These do boot — but each i | attribution | names the base honestly |
| os/plan/META_OS.md:52 | Rejected: Ubuntu (snap stack fights the appliance model and the boot budget), Alpine (musl + OpenRC means re-solving service supervision we get free from systemd), Arch (a moving base under a frozen d | attribution | names the base honestly |
| os/tests/test_os_base.py:29 | r"\b(bullseye/trixie/forky/sid/ubuntu/fedora/centos/rhel/archlinux)\b", | attribution | test denylist that FORBIDS the word; self-policing |
| os/tests/test_os_livebuild.py:92 | r"\b(bullseye/trixie/forky/sid/ubuntu/fedora/centos/rhel/archlinux)\b", | attribution | test denylist that FORBIDS the word; self-policing |
| os/tests/test_os_packer.py:52 | r"\b(bullseye/trixie/forky/sid/ubuntu/fedora/centos/rhel/archlinux)\b", | attribution | test denylist that FORBIDS the word; self-policing |

## Excluded-scope summary (checker never reports these)

| plan/ (working history, 15 files) | 416 hits | out of scope |
| os-build/logs/ (generated evidence, 29 files) | 48 hits | out of scope |
| iso-filelist.txt (ISO manifest) | 121 hits | out of scope |

## Xubuntu verdict (task 5)

Every `Xubuntu`/`xubuntu` outside `plan/` and `os-build/logs/` is
`attribution` (names the 24.04 base honestly in a comment, doc, or test)
except three LEAK rows above: the two desktop-entries `Comment=` lines
(OS-3, user-visible) and nothing else — the payload identity files say
`ubuntu`, not `Xubuntu`. `Canonical` (capital) outside plan/logs is the
English word `canonical` in all but one place (`PIPELINE.md:19,
"Canonical's SHA256SUMS", attribution); lowercase `canonical` is the
English word or `fs::canonicalize`-style identifiers everywhere — the
checker still matches it literally and the allowlist carries those rows
with verdict `attribution` and an explicit English-word reason.
