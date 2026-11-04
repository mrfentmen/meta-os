# Greeter payload — what lives where, and how to change the background

The live greeter configs ship from `../greeter/` (drop-ins the provision
scripts install verbatim); this directory holds the Meta session launcher
plus the gates. The two must agree:

- `../greeter/lightdm-gtk-greeter.conf` — `background=`, `theme-name`,
  `font-name`, `clock-format`, cursor keys (lightdm-gtk-greeter reads it).
- `../greeter/unity-greeter.conf` — `background=`, `logo=` (installed
  unity-greeter reads it, not the gsettings path).
- `../greeter/99_metaos-greeter.gschema.override` — the keys unity-greeter
  *actually* reads (`com.canonical.unity-greeter`); must be compiled with
  `glib-compile-schemas` after install.
- `metaos.desktop` — `Name=Meta OS`, `Exec=/opt/face/session.sh`,
  installed as `/usr/share/xsessions/metaos.desktop`; `TryExec` makes a
  missing session fail loudly instead of falling back to stock.

## Change the greeter background (all three, or one screen disagrees)

1. Put the art in `../wallpapers/<name>.png`.
2. Set the same path in `../greeter/lightdm-gtk-greeter.conf`
   (`background=`) AND `../greeter/unity-greeter.conf` (`background=`) AND
   `../greeter/99_metaos-greeter.gschema.override` (`background='...'`).
3. Recompile schemas on the target (`glib-compile-schemas
   /usr/share/glib-2.0/schemas`) — without this the override is inert.
4. Run `sh ../lightdm/check-greeter.sh` (this dir): 21 checks, exit 1 on
   any Ubuntu string, missing art, or session/autologin/guest/clock/font/
   cursor/hostname drift.
