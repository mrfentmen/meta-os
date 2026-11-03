# MetaOS 1.0 — release checklist (Pax, integration + release lane)

Source of truth: `os-build/METAOS_1.0_12H_PLAN.md` (main @80a7886c).
Clock: H+0 = 2026-11-02 21:46 EST (boss's word). H+12 = ~09:46 EST Nov 3.
Every box gets a label when it closes: VERIFIED (proof read by Pax) /
CODE-INSPECTED / UNIMPLEMENTED / BLOCKED (reason named). No box closes on a
branch claim alone.

## Standing rules for every cut

- Lanes commit to their own branches. Pax merges everything; only Pax
  pushes main and posts.
- AMENDED by the boss's decoupling amendment (main @d835b59a, 2026-11-02
  22:17 EST): no lane waits on another. Pax cuts from lane branches
  as-they-are; a missing lane or a missing proof is a named gap in the
  cut record, never a delayed cut. Milo audits whatever exists at each
  cut; his audit rows record state, they do not hold a cut.
- Fences: original assets only (nothing Apple-adjacent ships), no mock or
  placeholder presented as done, simulated loopback dispatch only,
  kernel/src/syscalls.rs FROZEN.

## H+0 — brand kit locked (~21:46 EST)

- [ ] Name, logo, hex values, wallpaper, password policy committed (OC1).
- [ ] Milo original-asset audit row for the kit.

## H+2 — base boots with splash (~23:46 EST)

- [x] Cubic base project committed (Hana): package list, accounts,
      first-boot setup, default files/associations. — CODE-INSPECTED:
      hana/metaos1-base @41a16c53 merged to main (7 files, 0 conflicts,
      blobs verified). No Cubic build has run yet.
- [x] Plymouth splash in the base (Buffy). — CODE-INSPECTED:
      buffy/boot-installer @cbf00e3f merged to main (49 files, 0
      conflicts, blobs verified): build_iso.sh, Calamares branding,
      splash assets committed. Not yet built into an ISO.
- [x] Bond core-app configs. — CODE-INSPECTED: bond/12h @df5b1664
      merged to main (40 files, 0 conflicts, blobs verified). His new
      ISO/agent tests are committed; Pax has not run them yet.
- [ ] Proof: VM boot to login under 60s, screendump set committed.
      — BLOCKED: no base ISO bytes exist yet (see cut 1 gap).
- [x] ISO cut 1 by Pax from the merged tree. — CUT RECORD: tree =
      main @0eddeb5d (2026-11-02 ~22:57 EST), all three 1.0 lane
      branches merged and blob-verified (96/96). NAMED GAP: the ISO
      artifact itself is not built — Buffy's build runs on a Linux
      host (Pax's sandbox is ready: root, xorriso + squashfs-tools
      installed) but the base Xubuntu ISO file is Del's own download
      (his order 22:13 EST: he has it); the byte-build starts when
      the file reaches the build host. Per the decoupling amendment
      the cut stands with the gap named, not delayed.

## H+4 — login + desktop load (~01:46 EST)

- [ ] LightDM/SDDM theme + lock screen (OC1); password login works.
- [ ] Xfce top bar + Plank dock + launcher in the Meta colorway.
- [ ] Proof: login-to-desktop screenshot set committed per milestone.
- [ ] ISO cut 2.

## H+6 — fully themed (~03:46 EST)

- [ ] GTK recolor, Papirus recolor, wallpaper pack, font picks (OC1).
- [ ] Core apps open from the dock and close clean (Bond): file manager,
      terminal, settings, Chromium with Meta start page. Configs committed,
      no stubs.
- [ ] ISO cut 3.

## H+8 — installer tested end to end (~05:46 EST)

- [ ] Calamares preseeded with Meta branding (Buffy).
- [ ] Proof: clean install to a fresh disk, start to finish, reboots into
      the login screen. VM screendumps committed.
- [ ] Agent layer autostarts at login (OC2): patrol cycle runs on a fresh
      boot with no hand-holding, crew assessment logged, spend tracked
      against the guardrail.
- [ ] ISO cut 4.

## H+10 — bugfix / polish (~07:46 EST)

- [ ] Every BLOCKED or failed acceptance item from H+2..H+8 either fixed
      with proof or carried into the final notes by name.
- [ ] ISO cut 5.

## H+12 — final (~09:46 EST)

- [ ] Final ISO cut from the merged tree.
- [ ] Boot-video proof committed (fresh file name, link delivery).
- [ ] Milo claim audit: every shipped claim labelled; anything unproven
      named in the release notes, never padded.
- [ ] Pax go/no-go posted to room 1 and reported to the boss with the
      evidence list.

## Open blockers carried into the run (named at H+0)

- Meta API billing returned HTTP 402 on 2026-11-02 — live-model calls
  (patrol assessments, OC2 live proofs, Milo MT checks) are blocked until
  the boss tops the account up. Staged/offline proofs still count as what
  they are.
- Key route for crew VMs unpicked (plan: boss sets keys on the Mac).
- Kernel 2.0 track continues off the critical path: KF-03 gated
  (compile), loader fix + framebuffer re-proof owed; K3 gate-2 boot owed;
  K4 talker/listener pair owed. None of it blocks a 1.0 cut.
