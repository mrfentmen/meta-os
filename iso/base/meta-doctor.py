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

    autostart = root / "etc/xdg/autostart"
    entries = sorted(autostart.glob("*.desktop")) if autostart.is_dir() else []
    unresolved = []
    for entry in entries:
        exe = ""
        try:
            for line in entry.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Exec="):
                    exe = line.split("=", 1)[1].strip().split(" ")[0]
                    break
        except OSError:
            unresolved.append("%s (unreadable)" % entry.name)
            continue
        if not exe or not (root / exe.lstrip("/")).is_file():
            unresolved.append("%s -> %s" % (entry.name, exe or "no Exec"))
    if not entries:
        put("FAIL", "autostart binaries", "no entries in %s" % autostart)
    else:
        put("PASS" if not unresolved else "FAIL", "autostart binaries",
            "%d entry/entries all resolve" % len(entries) if not unresolved
            else "missing " + ", ".join(unresolved))

    agent_units = root / "usr/lib/systemd/user"
    wanted_units = ("oc2-queue.service", "oc2-trio.service",
                    "oc2-patrol.service", "oc2-patrol.timer")
    missing = [u for u in wanted_units if not (agent_units / u).is_file()]
    put("PASS" if not missing else "FAIL", "agent units",
        "%d of %d in %s" % (len(wanted_units) - len(missing),
                            len(wanted_units), agent_units)
        if not missing else "missing " + ", ".join(missing))

    wants = root / "etc/systemd/user"
    links = ([wants / "default.target.wants" / u for u in wanted_units[:3]]
             + [wants / "timers.target.wants" / wanted_units[3]])
    torn = [str(p.relative_to(root)) for p in links
            if not p.is_symlink() and not p.is_file()]
    put("PASS" if not torn else "FAIL", "agent enabled",
        "4 links" if not torn else "missing " + ", ".join(torn))

    agent_payload = root / "usr/share/metaos/agent"
    runtime = ("server/queue/queue_service.py", "server/queue/patrol.py",
               "server/queue/trio_agent.py", "js/products.js", "js/schema.js")
    missing = [rel for rel in runtime if not (agent_payload / rel).is_file()]
    put("PASS" if not missing else "FAIL", "agent runtime",
        "all %d files" % len(runtime) if not missing
        else "missing " + ", ".join(missing))

    env = root / "etc/skel/.config/oc2-agent/env"
    if not env.is_file():
        put("FAIL", "agent env", str(env))
    else:
        env_body = env.read_text(encoding="utf-8", errors="replace")
        secret = ("SPARK_API_KEY" in env_body or "sk-" in env_body
                  or "BEGIN PRIVATE" in env_body)
        pinned = "OC2_CHECKOUT=/usr/share/metaos/agent" in env_body
        put("PASS" if pinned and not secret else "FAIL", "agent env",
            "checkout pinned, no secret" if pinned and not secret
            else ("contains a secret" if secret else "OC2_CHECKOUT not the payload"))

    hook = root / "usr/local/bin/meta-agent-login"
    put("PASS" if hook.is_file() and os.access(hook, os.X_OK) else "FAIL",
        "agent login hook", str(hook))

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
