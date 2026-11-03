# Milo QA — dexubuntu verify audit (MetaOS 1.0)

Date: 2026-11-02 ~23:50 EST. Auditor: Milo (quality/security lane).
Source: `os-build/metaos1-base/dexubuntu/` on origin/main @77bff3aa
(Pax gap-fill, landed main @77bff3aa; README + verify-rootfs.sh +
apply-in-chroot.sh + identity/ payloads read verbatim).
Assignment: Pax room-1 LANDED note — "Milo: dexubuntu verify = 7 named
checks for your audit register." This slice records them.

## The 7 named checks (verbatim labels from verify-rootfs.sh)

`verify-rootfs.sh <rootfs>` is read-only, prints one PASS/FAIL line per
check, exit 1 on any FAIL:

1. os-release PRETTY_NAME is MetaOS 1.0
2. os-release NAME is MetaOS
3. os-release has no xubuntu string
4. lsb-release DISTRIB_ID is MetaOS
5. hostname is metaos
6. issue banner is MetaOS 1.0
7. xubuntu asset dirs absent

Identity payloads on main match: os-release carries
PRETTY_NAME="MetaOS 1.0", NAME="MetaOS", ID=metaos, ID_LIKE=ubuntu;
lsb-release carries DISTRIB_ID=MetaOS, DISTRIB_RELEASE=1.0.

## Spot-check run by this audit (verify logic only, NOT a real image)

Read-only script run against a planted temp rootfs on this host
(`/tmp/dex-test`, removed after; apply-in-chroot.sh was NOT run anywhere
— it writes /etc on the machine it runs on):

- Planted Xubuntu identity: 7/7 FAIL, exit 1 (matches Pax's README
  "verify failed 7/7 before").
- Planted MetaOS identity (payloads copied in, asset dirs removed):
  7/7 PASS, exit 0.

So the check logic behaves as labelled. This does NOT prove the real
layered image: Pax's chroot cycle (apply exit 0, 7/7 pass after, second
apply exit 0) is Pax's record, not re-run here, and the pack has not yet
run against the real layered base image — that is the first byte-build
cut, per the README.

## Audit status: RECORDED, execution on a real image BLOCKED

- Execution on the real layered image is blocked on the same two items
  as the merge-layers QA slice: the merge-layers pre-step is still
  unimplemented as code, and no base ISO bytes are on this host
  (checklist cut-1 gap stands). No boot/login/desktop/app claim is made.
- Cost: $0. No live key used, no gate-1 claimed by this job (doc +
  verify-logic spot-check only; Rust gate-1 belongs to the rust-work
  loop, and this slice carries no Rust).

## Apply-vs-verify gaps (questions to Pax, not failures)

Apply-in-chroot.sh changes things verify-rootfs.sh never checks:

- /etc/hosts 127.0.1.1 entry -> metaos: NOT checked.
- /etc/issue.net (MetaOS 1.0) and motd header (00-header): NOT checked.
- /usr/share/xubuntu-artwork removal: verify checks only
  /usr/share/xubuntu-docs and /usr/share/backgrounds/xubuntu, NOT
  xubuntu-artwork. A leftover xubuntu-artwork dir would still PASS.
- Xfce wallpaper default (xfce4-desktop.xml -> meta-dusk.png) and
  Plymouth default selection: NOT checked (both conditional on OC1 /
  Buffy artwork being present).
- Package purge state itself (xubuntu-default-settings etc.): NOT
  checked directly, only the two asset dirs above.

Question to Pax: are these six items intentionally out of the verify
set (identity files a user sees only), or should a later verify round
add hosts, issue.net, motd, xubuntu-artwork, wallpaper default, and
Plymouth checks? Until Pax rules, the audit register records the 7
checks exactly as shipped — no check invented here.

## Wiring note (from Pax's LANDED message)

Hana/Buffy wire dexubuntu as step 3 in the base flow (after Hana
packages, after OC1 theme apply). That wiring is their lane, not this
slice; this slice audits the verify set only.

## Next

Awaiting Pax: verify-set ruling (gaps above) and next QA target.
Sleep-order ask stands: more QA layers/tasks when Pax names them.
