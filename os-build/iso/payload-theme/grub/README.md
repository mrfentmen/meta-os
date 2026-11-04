# GRUB payload — change the menu title in one place

Edit `branding.conf` (`TOP_TITLE`, `RECOVERY_TITLE`, `VERSION`,
`DISTRIBUTOR`, `TIMEOUT`), then:

1. `sh os-build/iso/grub-fix.sh <built-tree>/boot/grub/grub.cfg`
   (idempotent; converges live titles, recovery titles, timeout,
   default entry, and strips `quiet splash` on recovery lines).
2. Install `metaos-grub-defaults` as
   `/etc/default/grub.d/99-metaos.cfg` on the target so `grub-mkconfig`
   writes `GRUB_DISTRIBUTOR="MetaOS"` and the named default.
3. `sh os-build/iso/payload-theme/grub/check-grub.sh --template` (static
   template gates) and `--grub-cfg <file>` (generated-config gate:
   fails on `Ubuntu` in boot-visible text).

`theme.txt` + `background.png` + `mark.png` are the whole theme asset set
(stock GRUB font only, no `.pf2`). The `xubuntu.seed` path reference is
deliberately carved out of every rewrite: renaming it would break boot.
