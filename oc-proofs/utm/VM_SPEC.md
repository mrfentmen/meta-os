# UTM VM spec for metaos-2026-11-01.img (NC-085)

Host: this Mac. UTM 5.0.8, utmctl 5.0.8 (both verified on the machine).

- Architecture: x86_64 emulation (Apple silicon host — slow, stated).
- CPU model: a MODERN one (e.g. max / Cascadelake-Server class). NEVER
  qemu64: a crew program (Freebuff) SIGILLs under the qemu64 default
  (the Freebuff lesson — recorded, not re-learned).
- RAM: 4096 MB. vCPUs: 2 (matches the packer build: 2G/2c; RAM raised
  to 4G for headroom).
- Disk: attach the built `metaos-2026-11-01.img` as the boot disk
  (virtio-blk). Working copy only — the golden base stays read-only
  (see rollback note).
- Display: default; serial console ENABLED (the ttyS0 question needs
  it). Serial log file: utmserial-$DATE.log in the VM folder (checked
  available on UTM 5.0.8 — NC-093: yes, serial logging supported).
- Network: shared (NAT) for DHCP + host HTTP to the guest dashboard.
- Boot target: stock entry → relay.target (dashboard :8080).
