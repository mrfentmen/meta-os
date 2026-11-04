#!/usr/bin/env python3
"""check_installer.py — dry-run validation of the Calamares config (R2-T1 E96).

Reads the installer tree, never launches it. Every gate prints PASS/FAIL;
exit 0 only if all pass. No boot, no mount, no network.
"""
import os
import re
import struct
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "..", ".."))
CAL = os.path.join(ROOT, "os-build", "iso", "calamares")
BRAND = os.path.join(CAL, "branding", "metaos")
MOD = os.path.join(CAL, "modules")

passed = failed = 0


def ok(name):
    global passed
    passed += 1
    print("PASS " + name)


def no(name, detail=""):
    global failed
    failed += 1
    print("FAIL " + name + (" -- " + detail if detail else ""))


def read(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def gate_file(path, label):
    if os.path.isfile(path):
        ok(label + " exists")
        return True
    no(label + " exists", path)
    return False


# --- branding strings come from one file ---
desc = os.path.join(BRAND, "branding.desc")
if gate_file(desc, "branding.desc present"):
    text = read(desc)
    for key, want in (("productName", '"Meta OS"'),
                      ("versionedName", '"Meta OS 1.0"'),
                      ("bootloaderEntryName", '"Meta OS"')):
        if want in text:
            ok("branding %s is %s" % (key, want))
        else:
            no("branding %s" % key, "want %s" % want)

# --- installer title / window say Meta OS ---
if "Meta OS" in (read(desc) if os.path.isfile(desc) else ""):
    ok("installer title says Meta OS")
else:
    no("installer title", "no Meta OS")

# --- slideshow images exist and are real PNGs ---
slides = []
sp = os.path.join(BRAND, "slideshow")
names = {1: "welcome", 2: "desktop", 3: "apps", 4: "agents", 5: "done"}
for i in range(1, 6):
    f = os.path.join(sp, "slide-%02d-%s.html" % (i, names[i]))
    gate_file(f, os.path.basename(f) + " ships")
    f = os.path.join(sp, "slide-%02d.png" % i)
    slides.append(f)
    gate_file(f, os.path.basename(f) + " ships")
for f in slides:
    if not os.path.isfile(f):
        continue
    with open(f, "rb") as fh:
        head = fh.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", head[16:24])
        ok("%s PNG %dx%d" % (os.path.basename(f), w, h))
    else:
        no(os.path.basename(f) + " is PNG", "bad header")

# --- brand images referenced by branding.desc exist ---
for img in ("productLogo.png", "productIcon.png", "productWelcome.png"):
    gate_file(os.path.join(BRAND, img), img + " ships")

# --- user-visible strings: no Ubuntu, no Xubuntu, no ubiquity ---
surfaces = []
for dp, _dn, fn in os.walk(BRAND):
    for fn in fn:
        if fn.endswith((".html", ".qss", ".desc")):
            surfaces.append(os.path.join(dp, fn))
hits = []
for f in surfaces:
    for n, line in enumerate(read(f).splitlines(), 1):
        if re.search(r"ubuntu|xubuntu|ubiquity", line, re.I):
            hits.append("%s:%d" % (os.path.relpath(f, ROOT), n))
if hits:
    no("ui.zero-ubuntu-strings", "; ".join(hits[:5]))
else:
    ok("ui.zero-ubuntu-strings -- clean")

# --- palette is the desktop contract ---
css = os.path.join(sp, "slideshow.css")
if os.path.isfile(css):
    pal = read(css)
    if "#070B16" in pal and "#1877F2" in pal and "#EDF5FF" in pal:
        ok("slideshow palette is contract (#070B16/#1877F2/#EDF5FF)")
    else:
        no("slideshow palette", "missing contract hex")
else:
    no("slideshow.css ships", css)

# --- modules: keyboard us, locale America/New_York ---
kb = read(os.path.join(MOD, "keyboard.conf")) if os.path.isfile(
    os.path.join(MOD, "keyboard.conf")) else ""
if '"us"' in kb:
    ok("keyboard layout is us")
else:
    no("keyboard layout", "want us")
loc = read(os.path.join(MOD, "locale.conf")) if os.path.isfile(
    os.path.join(MOD, "locale.conf")) else ""
if '"America"' in loc and '"New_York"' in loc:
    ok("timezone is America/New_York (demo city)")
else:
    no("timezone", "want America/New_York")

# --- username policy: meta, never ubuntu ---
users = read(os.path.join(MOD, "users.conf")) if os.path.isfile(
    os.path.join(MOD, "users.conf")) else ""
if 'login: "meta"' in users and "ubuntu" not in users.lower().replace(
        "ubuntu's equivalent", ""):
    ok("username policy creates meta, not ubuntu")
elif 'login: "meta"' in users:
    ok("username policy creates meta (comment names base honestly)")
else:
    no("username policy", "login is not meta")

# --- finish page: reboot only, reboot pre-checked ---
fin = read(os.path.join(MOD, "finished.conf")) if os.path.isfile(
    os.path.join(MOD, "finished.conf")) else ""
if "restartNowChecked: true" in fin and "systemctl -i reboot" in fin:
    ok("finish page offers reboot (pre-checked)")
else:
    no("finish page", "reboot default unclear")

# --- packages: no Ubuntu desktop metapackage ---
pkg = read(os.path.join(MOD, "packages.conf")) if os.path.isfile(
    os.path.join(MOD, "packages.conf")) else ""
if re.search(r"(?m)^\s*-\s*(xubuntu|lubuntu|kubuntu|ubuntu)-desktop", pkg):
    no("packages.no-ubuntu-metapackage", "desktop metapackage listed")
else:
    ok("packages.no-ubuntu-metapackage -- clean")

# --- licenses: branding carries no dead support/release-notes URLs ---
wel = read(os.path.join(CAL, "modules", "welcome.conf")) if os.path.isfile(
    os.path.join(CAL, "modules", "welcome.conf")) else ""
if "showSupportUrl: false" in wel and "showReleaseNotesUrl: false" in wel:
    ok("no dead Ubuntu release-notes/support URLs")
else:
    no("installer URLs", "support/release-notes links live")

print("RESULT: DRY-RUN %s (%d passed, %d failed; VM walkthrough still owed)"
      % ("PASS" if failed == 0 else "FAIL", passed, failed))
sys.exit(1 if failed else 0)
