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
      artifact itself is not built — two parts. (1) The base Xubuntu
      ISO file is Del's own download (his order 22:13 EST: he has it);
      the byte-build starts when the file reaches the build host.
      (2) Buffy's measured facts (BASE_FACTS.md, merged): the
      reference image is Xubuntu 24.04.5, SHA-256 verified against
      Canonical's published sums — and it is LAYERED (minimal +
      standard + live squashfs, 9.68 GB assembled, no single
      casper/filesystem.squashfs), which build_iso.sh --iso
      currently refuses by design. Buffy's lane task: a merge-layers
      pre-step for the script; Pax's Linux host (root, xorriso +
      squashfs-tools installed) will run/test it once the ISO lands.
      Per the decoupling amendment the cut stands with the gap
      named, not delayed.

## H+4 — login + desktop load (~01:46 EST)

- [ ] LightDM theme + lock screen (OC1); password login works.
      — Theme code MERGED + apply path VERIFIED: metaos-theme greeter
      conf + apply.sh on main; the H4-1 blocker (apply.sh installed a
      nonexistent slick-greeter.conf and aborted everything) was found
      by Milo's audit, fixed by Pax @f60dd3e8, and independently
      re-audited CLOSED by Milo (shim run exit 0, 7/7 payloads).
      The GTK half of Milo's H4-2 index gap is also filled: a standard
      X-GNOME-Metatheme index.theme for MetaOS landed (Pax gap-fill,
      apply.sh installs it; shim re-test 8/8 payloads). The icon half
      resolves when OC1's Papirus recolor runs on the build host
      (the copied tree carries its index); the xfwm4 window theme
      remains an H+6 item, not yet built.
      Post-sweep hand-combine (Pax, @6d1620e7): apply.sh now also
      installs OC1's splash set and registers the Plymouth theme
      (guarded update-alternatives + update-initramfs activation);
      shim run exit 0, 15/15 payloads land, activation calls verified
      via stubs (real update-initramfs runs in the ISO chroot, not
      the shim). Plymouth is now installed by code; a themed boot
      splash is still not boot-proofed. NAMED GAP for proof only.
      Password login itself: NOT proofed on a committed screenshot —
      Del-side first boot (2026-11-02 23:41 EST, Del-reported) reached
      a desktop; no login-screen shot is committed. NAMED GAP.
- [ ] Xfce top bar + Plank dock + launcher in the Meta colorway.
      — CODE-INSPECTED: panel xml + plank dock.theme merged with the
      theme; token values verified against the frozen contracts by
      Milo. NOT proofed on a booted image: the one committed desktop
      screenshot (os-build/iso/proof/metaos-first-desktop.png, read
      by Pax) shows a stock Xfce panel, no dock, and a green wallpaper.
      A second committed shot landed in this pass
      (os-build/iso/proof/metaos-desktop-autologin.png, OC1, read by
      Pax): autologin reaches the desktop, but it is the same stock
      panel, no dock, green rays wallpaper — an autologin proof, not
      a theme proof. NAMED GAP.
- [ ] Proof: login-to-desktop screenshot set committed per milestone.
      — Two desktop PNGs exist (first boot + autologin); both are
      stock/unthemed and no login-screen shot exists. NAMED GAP.
- [x] ISO cut 2 by Pax from the merged tree. — CUT RECORD: tree =
      main @6d1620e7 (cut at H+4, 2026-11-03 ~01:55 EST). Since cut 1:
      frozen contracts + OC1 theme merged; Milo QA audits x3 merged
      (1.0, merge-layers, H+4 apply + re-audit); dexubuntu pack built,
      chroot-tested 7/7, wired as base-flow step 3 (Hana; validate.py
      107 PASS run by Pax); Bond ISO lane merged through @3b97ead3
      (Pax-run ISO suites: 53 + release_gate 8, all OK); OC2 delta
      fully merged (science-lab 374 OK); the byte-build pipeline is
      now scripted end to end on main: merge-layers.sh (OC1) ->
      finalize-iso-tree.sh (OC1, Pax-tested) -> repack-iso.sh (Pax,
      mechanism-tested incl. base SHA gate). Full branch sweep run by
      Pax before this cut (Del's order): every non-contained branch
      classified file-by-file — 17 lane branches merged whole (incl.
      Milo's agent-layer gate docs, Rowan's K3/K4 design docs, OC1
      round-6 + wave-3 evidence archives, Bond's rewritten officina
      test_code100 — 13 tests OK on the merged tree) and 4 partial
      merges taking only apply-clean files (71 files, blob-verified);
      kernel/Rust branches stay HELD behind their proof gates, and
      conflicted branches were left untouched. Pax-run test baselines
      at the pre-sweep tree b0859f10 (all green): queue-python 613 OK
      (1 skip), science-lab 374 OK, custos 125 OK, ISO battery 61 OK,
      agent-layer units 10 OK, hortus 14 OK; post-sweep additions
      verified separately (officina test_code100 13 OK at the new tip).
      MERGE PASS at H+4 (Del's order 01:19 EST, "start merging"):
      every branch moved since the sweep was re-classified file-by-file
      against main — Milo qa-h6-firstlogin merged whole (1 file, his
      H+6 first-login QA doc); Bond 12h merged whole (39/39 apply-clean:
      wallpaper at three sizes + login picker, welcome app, MetaOS icon
      theme, xfconf panel/power/locker configs, claims registry +
      checker, precut + tokens_to_xfce tools); OC1 boot-installer
      merged whole (70/70 apply-clean: merge-layers.sh update,
      payload-theme pack incl. welcome app + tests, Plymouth splash
      set, Calamares slideshow + mount/umount modules, pipeline docs,
      boot + autologin proof PNGs); OC1 metaos-1.0 partial merge (170
      apply-clean files: theme splash/welcome/icons/wallpapers, face
      updates, test batch) with metaos-theme/apply.sh EXCLUDED as the
      single conflict, then hand-combined by Pax @6d1620e7 (see theme
      bullet above). Post-merge verification by Pax on the merged tree:
      10/10 spot blobs match branch blobs; ISO battery 114 OK (up from
      61 — the new Bond ISO tests included), cross-lane claims 6 OK,
      both welcome test suites OK, shell syntax OK on the merged
      scripts. HELD in this pass: buffy/agentic-layer (41 files,
      apply-clean, but Rust userspace + agent code with no Milo gate-1
      message — gate requested on room 1); all kernel branches remain
      held behind their Mac/boot proofs as before.
      NAMED GAP (carried):
      the ISO artifact itself is still not built — the base Xubuntu
      24.04.5 file (Del's copy) has not reached Pax's build host.
      Per the decoupling amendment the cut stands with the gap
      named, not delayed.

## H+6 — fully themed (~03:46 EST)

- [ ] GTK recolor, Papirus recolor, wallpaper pack, font picks (OC1).
      — PARTIAL, CODE-INSPECTED: wallpaper pack MERGED (Bond greeter +
      desktop wallpapers at 1366/2560/3840 + make_wallpaper.py +
      MANIFEST; OC1 meta-ascii wallpaper; OC1 live-wallpaper pack —
      the spinning ASCII ribbon as a live desktop background, per the
      boss's attract-screen ruling). GTK theme + greeter conf merged
      and apply-tested (H+4 record). Papirus recolor still NOT run on
      a build host; the xfwm4 window theme is still NOT built.
      NAMED GAPS, carried to H+8/H+10.
- [ ] Core apps open from the dock and close clean (Bond): file manager,
      terminal, settings, Chromium with Meta start page. Configs committed,
      no stubs.
      — Configs + apps CODE-INSPECTED and test-verified on the merged
      tree (welcome suites OK; ISO battery 114 OK at H+4 tree; agent
      layer staged into provision.sh with payload-gate checks; Bond
      health service + watchdog cadence merged). Opening from a dock
      on a booted themed image is NOT proofed — no byte-built image
      exists yet (carried gap, same root as cut 1/2: the base ISO file
      has not reached Pax's build host).
- [ ] ISO cut 3.
      — CUT RECORD: tree = main @451798b8 (cut at H+6, 2026-11-03
      ~03:46 EST). Since cut 2: the boss lifted all lane fences
      (2026-11-03 02:12 EST, "everyone over everyone's lanes") and Pax
      ran two all-in merge rounds — Bond 12h round 2 (grub theme,
      greeter, wallpaper set, ISO tools) + agent-layer-iso + watchdog
      cadence (health service/timer); OC2 landwalls 500-lane +
      queue round (watchdog, OC2B proof logs, queue e2e set); Buffy
      contract-worker superset (327 files: the full os/skills catalog,
      os/mos worker contract, capcheck userspace sources — her
      os-skills branch fully absorbed) + skills-runtime + boot-gate +
      layer1 clean set (45 contract/lobster files); OC1 Imperium
      wrapper update (single vendored Imperium app, per the boss's
      Trio = Imperium ruling); agents/runtime.mjs hand-combined by Pax
      (main lineage UNION Buffy hardening). Pax-run verification on
      merged trees: queue-python 637 OK; worker-contract + ISO
      wallpaper/checker suites 48 OK; os skills runtime 15 OK;
      test:agents — the ledger torn-line policy fork is RESOLVED:
      Milo's QA call (strict stands) updated the 2 stale
      skip-anywhere tests to the landed policy (milo/qa-ledger-strict
      merged by Pax); Pax re-ran the suite on the merged tree:
      184/184 GREEN. Provision dry-run re-verified by Pax on the
      cut tree: exit 0, Imperium app + agent runtime land. Pre-cut Pax
      gap-fill: Bond's updated meta-doctor checked the agent layer
      but iso/tools/apply.sh never staged it (4 doctor tests red);
      apply.sh now stages agent-layer like provision.sh does and
      records the staged paths for exact revert — full ISO battery
      re-run by Pax on the fixed tree: 123/123 OK (doctor 20 passed,
      0 failed against an apply.sh tree; BUFFY_ISO_STATUS claims
      refreshed to match, measured). After those rounds: Bond watchdog-cadence follow-ups merged (6-file partial: stage.sh, precut.sh, audit/handoff/box-map/proof-plan docs; then agents/memory.mjs + its tests whole) and Pax closed the manifest gap they exposed (oc2-health service+timer added to manifest TARGETS, MANIFEST.md regenerated). Pax re-verified on the merged trees: ISO battery 123/123 OK; test:agents 195/195 GREEN. At 02:38 EST the boss ordered Rowan, Milo and Hana to stop work and report what they have left, the OpenCodes to finish the build, and Pax to merge only (Hana and Milo acked stop; Rowan's ack still pending at cut time if not posted). Bond watchdog-cadence @72a025f6 landed whole after Pax's hand-combine (notify feature, registry draft rules, memory wiring; one policy edit: his torn-middle test removed per the settled strict ledger ruling, tail case already covered). Final pre-cut verification: test:agents 212/212 GREEN, ISO battery OK. still pending at cut time if not posted). HELD with
      reasons, not fences: Buffy's 5 kernel files (caps gate) —
      Milo gate-1 GREEN on record (kernel cargo check exit 0), held
      only for the boss's syscall-6 call (her caps query takes
      syscall 6; the frozen table assigns 6/7 to K4 IPC) plus the
      Mac boot log (gate-2); Rowan kernel-kf03-align @436c6cc — Milo
      gate-1 GREEN on record; held for the Mac build + QEMU log
      (gate-2). NAMED GAP (carried): the
      ISO artifact itself is still not built — the base Xubuntu
      24.04.5 file (Del's copy) has not reached Pax's build host;
      themed-desktop and login-screen proofs stay open for the same
      reason. Per the decoupling amendment the cut stands with the
      gaps named, not delayed.
      — ADDENDUM (final, at cut): after the rounds above, Bond
      watchdog-cadence landed twice more (@f0a9510b partial 12 +
      Pax edges hand-combine; @f9ce25c1 whole — jobs retry, Musica
      and Science Lab hosted), OC3 agent3 landed partial (SAM to
      Spark intel pipeline, 12 tests OK; its 6 crates files held,
      no compile gate), and Pax closed a manifest gap
      (oc2-watchman TARGETS row). Pax-verified on the merged tree:
      test:agents 239/239 GREEN, ISO battery 123/123 OK,
      queue-python 637 OK, science-lab 374 OK. At 03:34 EST the
      boss stopped Pax merging branches (the OpenCode lanes merge
      directly now); at 03:39 EST he ordered Pax to commit his own
      code to main. KERNEL (2.0 track): OC3's direct merge
      8923da87 put Buffy's RK-007 tree on main — kernel/src is now
      the bootloader_api 0.11 line (syscalls.rs untouched). Its
      committed serial log shows K1 alive, K3 ticks, K4 up, but
      all four userspace programs loader-refused ("address in
      use": the RK-007 build linked every program at the default
      address inside the kernel image). Pax's fix is committed at
      451798b8: rk007/build.sh now links each program at its own
      base via build_userspace.py, and kernel/build.rs no longer
      teaches the colliding plain build. The fixed-pipeline boot
      proof (zero refusals) is still owed; KF-03 screen proof and
      the two kernel holds above stand.

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
