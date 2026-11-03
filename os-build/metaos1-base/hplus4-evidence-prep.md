# H+4 evidence prep — base + first boot (Hana lane)

Milestone: H+4, login + desktop load, ~01:46 EST 2026-11-03
(checklist: `os-build/METAOS_1.0_RELEASE_CHECKLIST.md`).
ISO cut 2 follows this milestone.

Status of this document: PREP ONLY. It lists what the cut machine
must capture. Nothing in it is captured yet, and nothing here
claims a boot, a login, or a desktop load happened. This sandbox
has no Cubic, no VM, and no base ISO, so it cannot capture any of
it. Every item below stays OPEN until its proof is committed from
the cut machine and Milo signs the audit row.

## Base/firstboot items the cut machine must capture

1. Identity gate on the cut rootfs: `dexubuntu/verify-rootfs.sh`
   output showing all 7 checks PASS, committed with the cut-2
   record. Any FAIL stops cut 2; it is a named failure, not a
   quiet pass.
2. First-boot done-marker present on the installed system:
   `/var/lib/metaos1-firstboot.done` exists after first boot.
3. First-boot defaults applied for the console user: the system
   mimeapps defaults from this slice are in effect for plain text,
   images, and PDF, and no browser type is mapped by this slice.
4. Login screen: OC1's LightDM theme + lock screen shown (OC1
   lane). Password login works for the account the installer
   created (installer is Buffy's lane).
5. Desktop load: Xfce top bar + Plank dock + launcher shown in
   the Meta colorway (OC1 lane), after login.
6. Login-to-desktop screenshot set committed, per milestone, with
   the file names listed in the cut-2 record.
7. Login-to-desktop time recorded in the cut-2 record. The
   checklist sets no threshold for this step, so the time is
   recorded as measured and Pax judges it; no threshold is
   invented here.

## Known gaps carried into H+4 (not silently closed)

- Dexubuntu verify checks 7 items. It does not check the hosts
  entry, issue.net, the motd header, or the artwork dir removal.
  Until Pax answers Milo's question (intentional, or a later
  verify round), the cut operator should record those four items
  by hand in the cut-2 record, as observed, not as gate-proven.
- Real-image execution of dexubuntu is BLOCKED on the
  merge-layers pre-step (still unimplemented as code) and on
  there being no base ISO on this host, per Milo's dexubuntu
  audit. Those blockers are Buffy's and Pax's lanes to clear;
  this prep does not clear them.
- Pax's chroot cycle (apply exit 0, 7/7 after, second apply
  exit 0) is Pax's record on a planted rootfs. It is not
  re-claimed here as proof on a real image.

## Failure rule

Any item above that is missing, failed, or unrecorded at cut-2
time is a named H+4 failure. It goes into the release notes by
name. Nothing is padded, and no item closes on a branch claim
alone.
