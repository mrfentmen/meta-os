#!/usr/bin/env python3
"""meta-doctor.py — report what the install actually put on the machine.

A bad boot fails at the first missing piece and the screen does not say which.
This prints one row per part of the lane, in the order the machine needs them,
so the install names itself instead of just looking wrong.

    meta-doctor [--root DIR] [--home DIR] [--json]

Point --root at a staging tree to check it before it is installed. Exit 0
when every part is present, 1 when any is missing, 2 on bad usage. It reads;
it writes nothing.
"""

import json
import os
import sys
from pathlib import Path

GROUPS = (
    ("splash", (
        "usr/share/plymouth/themes/metaos/metaos.plymouth",
        "usr/share/plymouth/themes/metaos/metaos.script",
        "usr/share/plymouth/themes/metaos/ring-dot.png",
    )),
    ("boot menu", (
        "boot/grub/themes/metaos/theme.txt",
        "boot/grub/themes/metaos/meta-grub.png",
        "etc/default/grub.d/metaos-theme.cfg",
    )),
    ("installer", (
        "etc/calamares/settings.conf",
        "etc/calamares/branding/meta/branding.desc",
        "etc/calamares/modules/users.conf",
    )),
    ("desktop theme", (
        "usr/share/metaos/theme/meta-wallpaper.png",
        "usr/share/metaos/theme/gtk.css",
        "etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml",
    )),
    ("login screen", (
        "etc/lightdm/lightdm-gtk-greeter.conf",
        "usr/share/metaos/theme/greeter-wallpaper.png",
        "usr/share/themes/MetaOS/index.theme",
        "usr/share/themes/MetaOS/gtk-3.0/gtk.css",
    )),
    ("start page", (
        "usr/share/metaos/start/meta-start.html",
        "usr/share/metaos/start/tokens.css",
        "etc/chromium/policies/managed/metaos.json",
    )),
)

LAUNCHERS = ("meta-files", "meta-terminal", "meta-settings",
             "meta-browser", "meta-agent-status")


def rows(root, home):
    out = []

    def put(status, name, detail=""):
        out.append({"status": status, "check": name, "detail": detail})

    for stem in LAUNCHERS:
        path = root / "usr/share/applications" / (stem + ".desktop")
        put("PASS" if path.is_file() else "FAIL", "launcher " + stem, str(path))

    dock = root / "usr/share/metaos/dock"
    items = sorted(dock.glob("*.dockitem")) if dock.is_dir() else []
    put("PASS" if len(items) == len(LAUNCHERS) else "FAIL", "dock items",
        "%d of %d in %s" % (len(items), len(LAUNCHERS), dock))

    for group, files in GROUPS:
        missing = [rel for rel in files if not (root / rel).is_file()]
        put("PASS" if not missing else "FAIL", group,
            "all %d files" % len(files) if not missing
            else "missing " + ", ".join(missing))

    exe = root / "usr/local/bin/meta-agent-status"
    put("PASS" if exe.is_file() and os.access(exe, os.X_OK) else "FAIL",
        "meta-agent-status", str(exe))

    put("SKIP", "base image programs",
        "installed by the base, not by this tree: thunar xfce4-terminal "
        "xfce4-settings-manager chromium")

    if home is not None:
        marker = home / ".config" / "metaos" / "first-login.done"
        put("PASS" if marker.is_file() else "FAIL", "first login applied", str(marker))

    return out


def main(argv):
    root_arg = None
    home_arg = None
    as_json = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--root" and i + 1 < len(argv):
            root_arg = argv[i + 1]
            i += 2
        elif arg == "--home" and i + 1 < len(argv):
            home_arg = argv[i + 1]
            i += 2
        elif arg == "--json":
            as_json = True
            i += 1
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            print("doctor: unknown argument %s" % arg, file=sys.stderr)
            return 2

    root = Path(root_arg).expanduser().resolve() if root_arg else Path("/")
    if not root.is_dir():
        print("doctor: not a directory: %s" % root, file=sys.stderr)
        return 2

    if home_arg:
        home = Path(home_arg).expanduser().resolve()
    elif root_arg:
        home = None
    else:
        home = Path(os.environ["HOME"]) if os.environ.get("HOME") else None

    result = rows(root, home)
    summary = {key.lower(): sum(1 for row in result if row["status"] == key)
               for key in ("PASS", "FAIL", "SKIP")}

    if as_json:
        print(json.dumps({"root": str(root),
                          "home": str(home) if home else None,
                          "summary": summary,
                          "rows": result}, indent=2))
    else:
        print("doctor: root %s%s" % (root, ", home %s" % home if home else ""))
        for row in result:
            print("%-5s %-22s %s" % (row["status"], row["check"], row["detail"]))
        print("%d passed, %d failed, %d skipped"
              % (summary["pass"], summary["fail"], summary["skip"]))

    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
