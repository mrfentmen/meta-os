# NB-051 to NB-060 — UTM boot check: report only (Section E)

NB-051: I do not have the image file. Whole-disk search for
`metaos-*.img` returns zero hits. Per the task, the section stops here;
NB-052 through NB-060 are not attempted and nothing below is claimed.

What was established while checking:
- UTM is installed on this Mac (brew cask, UTM.app present, utmctl linked).
- The image (about 6.0 GiB, built 2026-11-01) was never delivered to this
  machine. The packer pipeline that builds it needs a Debian ISO plus KVM;
  its own test file states no build has ever run on a host without
  /dev/kvm, and macOS has no KVM.
- Unblock needs: the built .img file copied to this Mac. No rebuild was
  attempted (explicitly out of scope) and no VM was created.
