# MetaOS Calamares installer (Buffy lane, H+8)

Preseeded installer: a clean install to a fresh disk with no questions it
can answer itself.

**Label: CODE-INSPECTED.** The configs are parsed and checked in
`iso/tools/check_iso_config.py`. The install itself has **not** been run —
this Mac cannot host the VM. H+8's proof line (clean install → reboot →
login screen, screendumps committed) stays **UNPROVEN** until someone runs
it in a VM.

## Files

| File | Role |
|---|---|
| `settings.conf` | module order, branding pointer, no install prompt |
| `branding/meta/branding.desc` | product strings, colourway, slideshow |
| `branding/meta/show.qss` | slideshow type and colour (no artwork) |
| `modules/partition.conf` | erase disk, one ext4 root, no swap |
| `modules/users.conf` | one sudo user, no root password, no autologin, 12-char minimum |
| `modules/welcome.conf` | only storage + RAM requirements, no internet check |
| `modules/locale.conf` | America/New_York, from the live ISO's locale.gen |

Deliberately **not** written: `productLogo`, `productIcon`, `productWelcome`
in `branding.desc`. Naming image files that do not exist is a stub, and
Calamares falls back cleanly without them. They get added when the art
pass draws them.

Autologin is off on purpose: the acceptance line is "reboots into the login
screen", and autologin would quietly prove the wrong thing.

## Install into the live ISO

```sh
install -d /etc/calamares/branding/meta /etc/calamares/modules
cp iso/calamares/branding/meta/*   /etc/calamares/branding/meta/
cp iso/calamares/settings.conf     /etc/calamares/
cp iso/calamares/modules/*.conf    /etc/calamares/modules/
```

Calamares ships its own defaults for every other module in `settings.conf`,
so only the three modules this project actually presets are copied.

## Check without installing

```sh
python3 iso/tools/check_iso_config.py
```

It parses every YAML file, checks the branding pointer resolves, checks the
module sequence names real modules, and checks the password floor. It cannot
tell you the install works.
