# Identity — what a person reads vs what apt reads

Meta OS is a Debian/Xubuntu base with Meta's name on it. Two different
things live in the image and this lane treats them as two:

- **Identity** is what a person reads: `/etc/os-release`, the login banner,
  the hostname, the account name, the wallpaper, the greeter. If it says
  Ubuntu where Meta belongs, that is a bug and `debrand.sh` rewrites it.
- **Compatibility** is what the package manager reads: the archive suites,
  the package names, `ID_LIKE=debian`. This lane never touches those.
  Renaming `ID_LIKE` (or the keyring, or `ubuntu-minimal`) breaks apt,
  systemd and every Debian assumption in the image. The base stays Debian.

## Why `ID_LIKE=debian` stays

`ID_LIKE` tells tools which package family this system belongs to. Ours is
`debian`: the archive, the package names and the init system are Debian's.
Writing `ubuntu` there (which the installer script currently does — see the
report) breaks nothing today and lies to every tool that reads the field
tomorrow. So `debrand.sh` stamps `ID_LIKE=debian` and `--check` fails the
file if it says anything else.

## The checker: one command

```sh
sh os-build/identity/check_strings.sh
```

It greps the tree for the banned words, subtracts `ALLOWLIST.tsv`, prints
one line per surviving hit and exits 1 if any survive. Exact output on the
current tree (exit 1 — the five survivors are real leaks in files owned by
other lanes, deliberately not allowlisted):

```text
os-build/face/meta-desktop.sh:34:[ -n "$HOME_DIR" ] || HOME_DIR="${HOME:-/home/ubuntu}"
os-build/iso/calamares/meta-branding.sh:33:ID_LIKE=ubuntu
os-build/metaos1-base/dexubuntu/identity/os-release:7:ID_LIKE=ubuntu
agent-layer/desktop-entries/atril.desktop:6:Comment=View PDF files (base-observed binary on Xubuntu 24.04.5; KEEP line still says evince pending Hana ack — see README)
agent-layer/desktop-entries/evince.desktop:6:Comment=DEGRADED-OFF: KEEP lists evince but Xubuntu 24.04.5 base ships atril. Hidden until Hana acks. Do not map MIME here.
check_strings: 5 unsuppressed hit(s) — FAIL
```

Wall-clock on this tree: ~35 s warm (dominated by six greps over ~6k files).
`--explain` names the suppressing row per hit. `test_check_strings.sh`
builds three fixtures (clean / dirty / allowlisted) and asserts 0 / 1 / 0.
`STRINGS_INVENTORY.md` is the map of every hit with its verdict.
