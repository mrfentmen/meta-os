#!/usr/bin/env python3
"""iso/tools/check_iso_config.py — static checks for the MetaOS ISO lane.

This checks files, not a running system. It cannot boot Plymouth, run
Calamares, or click a dock icon, and it does not pretend to: a PASS here
means the config is well formed and points at things that exist.

    python3 iso/tools/check_iso_config.py

Exit 0 when every check passes, 1 when any fails.
"""

import configparser
import hashlib
import json
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
AS_JSON = "--json" in sys.argv[1:]
passes, fails, skips = [], [], []


def ok(msg):
    passes.append(msg)
    if not AS_JSON:
        print("PASS  " + msg)


def bad(msg):
    fails.append(msg)
    if not AS_JSON:
        print("FAIL  " + msg)


def skip(msg):
    skips.append(msg)
    if not AS_JSON:
        print("SKIP  " + msg)


def read(path):
    return path.read_text(encoding="utf-8")


def load_yaml(path):
    """Parse YAML with PyYAML, or Ruby's built-in YAML when PyYAML is absent."""
    try:
        import yaml  # noqa: PLC0415

        return yaml.safe_load(read(path))
    except ImportError:
        pass
    try:
        out = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e",
             "puts JSON.dump(YAML.load_file(ARGV[0]))", str(path)],
            capture_output=True, text=True, check=True,
        )
        return json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("no YAML parser available: %s" % exc)


def ini(path):
    parser = configparser.ConfigParser(
        interpolation=None, strict=False, delimiters=("=",)
    )
    parser.optionxform = str  # .desktop keys are case-sensitive
    parser.read(path, encoding="utf-8")
    return parser


# --- Plymouth splash ---------------------------------------------------
theme_dir = ISO / "plymouth" / "metaos"
descriptor = theme_dir / "metaos.plymouth"
script = theme_dir / "metaos.script"

if not descriptor.is_file():
    bad("plymouth: metaos.plymouth is missing")
else:
    cfg = ini(descriptor)
    module = cfg.get("Plymouth Theme", "ModuleName", fallback="")
    if module == "script":
        ok("plymouth: descriptor names the script module")
    else:
        bad("plymouth: ModuleName is %r, expected 'script'" % module)

    script_ref = cfg.get("script", "ScriptFile", fallback="")
    image_ref = cfg.get("script", "ImageDir", fallback="")
    if Path(script_ref).name == "metaos.script" and script.is_file():
        ok("plymouth: ScriptFile resolves to the shipped script")
    else:
        bad("plymouth: ScriptFile %r does not resolve" % script_ref)
    if Path(image_ref).name == theme_dir.name:
        ok("plymouth: ImageDir matches the theme directory")
    else:
        bad("plymouth: ImageDir %r does not match %r" % (image_ref, theme_dir.name))

if not script.is_file():
    bad("plymouth: metaos.script is missing")
else:
    body = read(script)
    if body.count("{") == body.count("}"):
        ok("plymouth: script braces balance")
    else:
        bad("plymouth: script braces do not balance (%d open, %d close)"
            % (body.count("{"), body.count("}")))
    images = re.findall(r'Image\("([^"]+)"\)', body)
    missing = [name for name in images if not (theme_dir / name).is_file()]
    if not images:
        bad("plymouth: script loads no image")
    elif missing:
        bad("plymouth: script loads missing image(s): %s" % ", ".join(missing))
    else:
        ok("plymouth: every image the script loads exists (%s)" % ", ".join(images))
    if "SetRefreshFunction" in body and "SetBootProgressFunction" in body:
        ok("plymouth: refresh and boot-progress callbacks are registered")
    else:
        bad("plymouth: a callback registration is missing (refresh or progress)")

# --- splash asset ------------------------------------------------------
ring = theme_dir / "ring-dot.png"
if not ring.is_file():
    bad("plymouth: ring-dot.png is missing")
else:
    head = ring.read_bytes()[:33]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        bad("plymouth: ring-dot.png is not a PNG")
    else:
        width, height, depth, colour = struct.unpack(">IIBB", head[16:26])
        if (width, height) == (24, 24):
            ok("plymouth: ring asset is 24x24")
        else:
            bad("plymouth: ring asset is %dx%d, expected 24x24" % (width, height))
        if colour == 6:
            ok("plymouth: ring asset is RGBA")
        else:
            bad("plymouth: ring asset colour type is %d, expected 6 (RGBA)" % colour)
        if depth == 8:
            ok("plymouth: ring asset is 8 bits per channel")
        else:
            bad("plymouth: ring asset bit depth is %d" % depth)

# --- Calamares ---------------------------------------------------------
KNOWN_MODULES = {
    "welcome", "locale", "keyboard", "partition", "users", "summary", "mount",
    "unpackfs", "machineid", "fstab", "localecfg", "displaymanager",
    "networkcfg", "hwclock", "services-systemd", "bootloader-config", "grubcfg",
    "bootloader", "umount", "finished", "shellprocess", "contextualprocess",
    "initramfs", "initcpiocfg", "dracut", "preservefiles", "removeuser",
    "webview", "notesqml", "tracking", "packagechooser", "luksbootkeyfile",
}

cal = ISO / "calamares"
branding = cal / "branding" / "meta" / "branding.desc"

try:
    brand = load_yaml(branding)
except FileNotFoundError:
    brand = None
    bad("calamares: branding.desc is missing")
except RuntimeError as exc:
    brand = None
    skip("calamares: branding.desc not parsed (%s)" % exc)

if brand:
    name = (brand.get("strings") or {}).get("productName")
    if name == "MetaOS":
        ok("calamares: branding names the product MetaOS")
    else:
        bad("calamares: strings.productName is %r" % name)
    style = brand.get("style") or {}
    for key in ("sidebarBackground", "sidebarText", "sidebarTextHighlight"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(style.get(key, ""))):
            bad("calamares: style.%s is not a hex colour" % key)
            break
    else:
        ok("calamares: sidebar colours are all hex")
    slideshow = brand.get("slideshow")
    if not slideshow or not (branding.parent / slideshow).is_file():
        bad("calamares: slideshow %r does not exist" % slideshow)
    else:
        ok("calamares: slideshow file exists")
        if not str(slideshow).endswith(".qml"):
            bad("calamares: slideshow %r is not a QML presentation" % slideshow)
        else:
            body = read(branding.parent / slideshow)
            if "import calamares.slideshow 1.0" not in body:
                bad("calamares: the slideshow has no calamares.slideshow import")
            else:
                ok("calamares: the slideshow imports the Calamares module")
            count = body.count("Slide {")
            if count >= 3 and "goToNextSlide" in body:
                ok("calamares: the slideshow has %d slides and advances" % count)
            else:
                bad("calamares: the slideshow has %d slide(s) or never advances" % count)
            try:
                contract = json.loads(read(ISO / "contracts" / "tokens.json"))
            except Exception:  # noqa: BLE001
                contract = {}
            if contract:
                allowed = {value.upper() for value in contract.values()}
                stray = sorted({hit.upper() for hit in
                                re.findall(r"#[0-9A-Fa-f]{6}\b", body)} - allowed)
                if stray:
                    bad("calamares: slideshow colours outside the contract: %s"
                        % ", ".join(stray))
                else:
                    ok("calamares: the slideshow uses only contract colours")

slideshow_gen = subprocess.run(
    [sys.executable, str(ISO / "tools" / "tokens_to_slideshow.py"), "--check"],
    capture_output=True, text=True,
)
if slideshow_gen.returncode == 0:
    ok("calamares: the slideshow is exactly what the generator produces")
else:
    bad("calamares: the slideshow is stale (%s)"
        % (slideshow_gen.stdout + slideshow_gen.stderr).strip())

settings_path = cal / "settings.conf"
try:
    settings = load_yaml(settings_path)
except RuntimeError as exc:
    settings = None
    skip("calamares: settings.conf not parsed (%s)" % exc)
except FileNotFoundError:
    settings = None
    bad("calamares: settings.conf is missing")

if settings:
    if settings.get("branding") == "meta":
        ok("calamares: settings point at the meta branding")
    else:
        bad("calamares: branding is %r, expected 'meta'" % settings.get("branding"))
    unknown = []
    seen = 0
    for stage in settings.get("sequence") or []:
        for kind, modules in stage.items():
            for module in modules:
                seen += 1
                if module not in KNOWN_MODULES:
                    unknown.append("%s/%s" % (kind, module))
    if unknown:
        bad("calamares: unknown module(s) in the sequence: %s" % ", ".join(unknown))
    else:
        ok("calamares: all %d sequence entries are real modules" % seen)
    ok("calamares: install prompt is off (preseeded)") if settings.get(
        "prompt-install") is False else bad("calamares: prompt-install is not false")
    for inst in settings.get("instances") or []:
        conf = inst.get("config")
        if conf and not (cal / "modules" / conf).is_file():
            bad("calamares: instance %r points at missing %r" % (inst.get("id"), conf))

def module_conf(name):
    path = cal / "modules" / name
    try:
        return load_yaml(path)
    except FileNotFoundError:
        bad("calamares: %s is missing" % name)
    except RuntimeError as exc:
        skip("calamares: %s not parsed (%s)" % (name, exc))
    return None

part = module_conf("partition.conf")
if part:
    if part.get("initialPartitioningChoice") == "erase":
        ok("calamares: partition preseed erases the chosen disk")
    else:
        bad("calamares: initialPartitioningChoice is %r" % part.get("initialPartitioningChoice"))
    if part.get("defaultFileSystemType") == "ext4":
        ok("calamares: default filesystem is ext4")
    else:
        bad("calamares: defaultFileSystemType is %r" % part.get("defaultFileSystemType"))

users = module_conf("users.conf")
if users:
    # Calamares nests this under `user:`, not at the top level.
    autologin = (users.get("user") or {}).get("doAutologin")
    if autologin is False:
        ok("calamares: autologin is off (the proof is a login screen)")
    else:
        bad("calamares: user.doAutologin is %r, expected false" % autologin)
    min_len = ((users.get("passwordRequirements") or {}).get("minLength"))
    if isinstance(min_len, int) and min_len >= 12:
        ok("calamares: password floor is %d characters" % min_len)
    else:
        bad("calamares: password minLength is %r" % min_len)

welcome = module_conf("welcome.conf")
if welcome:
    checks = (welcome.get("requirements") or {}).get("check") or []
    if {"storage", "ram"} <= set(checks):
        ok("calamares: welcome checks storage and ram only")
    else:
        bad("calamares: welcome checks are %r" % checks)

# --- sequence completeness ---------------------------------------------
if settings:
    flat = [m for stage in (settings.get("sequence") or [])
            for modules in stage.values() for m in modules]
    if flat and flat[-1] == "finished":
        ok("calamares: the sequence ends with finished")
    else:
        bad("calamares: the sequence ends with %r, not 'finished'"
            % (flat[-1] if flat else None))
    for required in ("partition", "bootloader"):
        if required in flat:
            ok("calamares: the sequence installs %s" % required)
        else:
            bad("calamares: the sequence never runs %s" % required)

if users:
    groups = (users.get("user") or {}).get("groups") or []
    if "sudo" in groups:
        ok("calamares: the user is in the sudo group")
    else:
        bad("calamares: the user groups are %r, no sudo" % groups)
    if users.get("setRootPassword") is False:
        ok("calamares: no root password is set")
    else:
        bad("calamares: setRootPassword is %r" % users.get("setRootPassword"))

locale_cfg = module_conf("locale.conf")
if locale_cfg:
    if locale_cfg.get("region") and locale_cfg.get("zone"):
        ok("calamares: locale preseeded to %s/%s"
           % (locale_cfg.get("region"), locale_cfg.get("zone")))
    else:
        bad("calamares: locale.conf has no region/zone")

# --- base image manifest ----------------------------------------------
# What the base image supplies, and what this lane adds on top. A launcher for
# a program no package installs is a dead icon, so the desktop entries are
# checked against this manifest instead of against a list inside this file.
packages_path = ISO / "base" / "metaos.packages"
REQUIRED_PACKAGES = {"plank", "fonts-inter", "lightdm-gtk-greeter", "plymouth", "calamares"}
packages, base_binaries = [], set()

if not packages_path.is_file():
    bad("base: metaos.packages is missing")
else:
    for raw in read(packages_path).splitlines():
        line = raw.strip()
        if line.startswith("#base:"):
            base_binaries |= set(line.split(":", 1)[1].split())
            continue
        if not line or line.startswith("#"):
            continue
        packages.append(line)

    dupes = sorted({name for name in packages if packages.count(name) > 1})
    if dupes:
        bad("base: duplicate package(s): %s" % ", ".join(dupes))
    else:
        ok("base: %d package(s), no duplicates" % len(packages))

    invalid = [name for name in packages if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", name)]
    if invalid:
        bad("base: not apt package names: %s" % ", ".join(invalid))
    else:
        ok("base: every line is a well-formed apt package name")

    missing_pkgs = sorted(REQUIRED_PACKAGES - set(packages))
    if missing_pkgs:
        bad("base: the manifest does not install %s" % ", ".join(missing_pkgs))
    else:
        ok("base: the manifest installs the packages the configs reference")

    if base_binaries:
        ok("base: the base image is declared to provide %s" % ", ".join(sorted(base_binaries)))
    else:
        bad("base: no #base: line, so no launcher can be checked against the base image")

# The per-user half of the install. Calamares makes the account after this
# runs, so the dock and the wallpaper are applied at first login instead.
first_login = ISO / "base" / "meta-first-login.sh"
if first_login.is_file():
    ok("base: the first-login script ships")
else:
    bad("base: meta-first-login.sh is missing")

doctor = ISO / "base" / "meta-doctor.py"
if doctor.is_file():
    ok("base: the doctor ships")
else:
    bad("base: meta-doctor.py is missing")
if "meta-doctor" in read(ISO / "tools" / "apply.sh"):
    ok("base: apply.sh installs the doctor")
else:
    bad("base: apply.sh never installs meta-doctor")

autostart = ISO / "base" / "autostart" / "meta-first-login.desktop"
if not autostart.is_file():
    bad("base: the first-login autostart entry is missing")
else:
    got = ini(autostart)["Desktop Entry"]
    exe = got.get("Exec", "").split()[0]
    try_exec = got.get("TryExec", "")
    if exe != "/usr/local/bin/meta-first-login":
        bad("base: autostart runs %r, expected /usr/local/bin/meta-first-login" % exe)
    elif try_exec != exe:
        bad("base: autostart TryExec %r does not match Exec %r" % (try_exec, exe))
    else:
        ok("base: first login starts from autostart, behind a matching TryExec")

# --- desktop entries ---------------------------------------------------
# Binaries this lane ships. The value is the file that must exist.
SHIPPED_APPS = {"meta-agent-status": Path("apps") / "agent-status" / "meta-agent-status.py"}
APPS = set(packages) | base_binaries | set(SHIPPED_APPS)

# The frozen launcher set, `metaos-contracts/APPS.md`: id -> launcher stem.
# A missing id is a named gap, and this table is how it gets named.
FROZEN_APPS = {
    "files": "meta-files",
    "terminal": "meta-terminal",
    "settings": "meta-settings",
    "browser": "meta-browser",
    "agent-status": "meta-agent-status",
}
desktop_dir = ISO / "apps" / "desktop"
entries = sorted(desktop_dir.glob("*.desktop"))
if not entries:
    bad("apps: no .desktop files")
for entry in entries:
    cfg = ini(entry)
    section = "Desktop Entry"
    if not cfg.has_section(section):
        bad("apps: %s has no [Desktop Entry]" % entry.name)
        continue
    got = cfg[section]
    missing = [k for k in ("Type", "Name", "Exec", "Categories", "Icon") if not got.get(k)]
    if missing:
        bad("apps: %s is missing %s" % (entry.name, ", ".join(missing)))
        continue
    if got.get("Type") != "Application":
        bad("apps: %s Type is %r" % (entry.name, got.get("Type")))
        continue
    binary = got.get("Exec", "").split()[0]
    if binary not in APPS:
        bad("apps: %s runs %r, which no package installs and this lane does not ship"
            % (entry.name, binary))
    else:
        ok("apps: %s runs %s" % (entry.name, binary))

# --- plank dock --------------------------------------------------------
dock_dir = ISO / "apps" / "plank"
items = sorted(dock_dir.glob("*.dockitem"))
if not items:
    bad("apps: no dock items")
for item in items:
    cfg = ini(item)
    launcher = cfg.get("PlankDockItemPreferences", "Launcher", fallback="")
    target = Path(launcher).name
    if target and (desktop_dir / target).is_file():
        ok("apps: %s points at %s" % (item.name, target))
    else:
        bad("apps: %s points at %r, which is not a shipped launcher" % (item.name, launcher))

# Every frozen id must have a launcher and a dock item. This is the rule that
# would have named the missing fifth app the day the contract was frozen.
launcher_stems = {entry.stem for entry in entries}
dock_stems = {item.stem for item in items}
for app_id, stem in sorted(FROZEN_APPS.items()):
    if stem in launcher_stems:
        ok("apps: frozen id %r ships %s.desktop" % (app_id, stem))
    else:
        bad("apps: frozen id %r has no launcher (%s.desktop)" % (app_id, stem))
    if stem in dock_stems:
        ok("apps: frozen id %r has a dock item" % app_id)
    else:
        bad("apps: frozen id %r has no dock item (%s.dockitem)" % (app_id, stem))

for binary, rel in sorted(SHIPPED_APPS.items()):
    if (ISO / rel).is_file():
        ok("apps: %s is backed by %s" % (binary, rel))
    else:
        bad("apps: %s is declared but %s is missing" % (binary, rel))

# The dock is not allowed to grow a sixth item or lose one: the frozen set is
# the contract, and an extra icon is as much a lie as a missing one.
expected_docks = {stem + ".dockitem" for stem in FROZEN_APPS.values()}
found_docks = {item.name for item in items}
if found_docks == expected_docks:
    ok("apps: dock items are exactly the frozen five")
else:
    if found_docks - expected_docks:
        bad("apps: dock has unexpected item(s): %s"
            % ", ".join(sorted(found_docks - expected_docks)))
    if expected_docks - found_docks:
        bad("apps: dock is missing item(s): %s"
            % ", ".join(sorted(expected_docks - found_docks)))

# Two launchers with the same Name or the same Exec confuse the menu.
seen_names, seen_execs, dupes = {}, {}, []
for entry in entries:
    got = ini(entry)["Desktop Entry"]
    name, exe = got.get("Name"), got.get("Exec")
    if name in seen_names:
        dupes.append("Name %r in %s and %s" % (name, seen_names[name], entry.name))
    if exe in seen_execs:
        dupes.append("Exec %r in %s and %s" % (exe, seen_execs[exe], entry.name))
    seen_names[name], seen_execs[exe] = entry.name, entry.name
if dupes:
    for note in dupes:
        bad("apps: duplicate launcher " + note)
else:
    ok("apps: every launcher has a unique Name and Exec")

# --- chromium policy and start page ------------------------------------
policy_path = ISO / "apps" / "chromium" / "policies.json"
start_page = ISO / "apps" / "chromium" / "meta-start.html"
policy = None
try:
    policy = json.loads(read(policy_path))["policies"]
    ok("apps: policies.json parses")
except Exception as exc:  # noqa: BLE001
    bad("apps: policies.json does not parse (%s)" % exc)

if policy:
    home = policy.get("HomepageLocation", "")
    if home.startswith("file:///usr/share/metaos/start/"):
        ok("apps: homepage is the local start page")
    else:
        bad("apps: HomepageLocation is %r" % home)
    if policy.get("RestoreOnStartup") == 4:
        ok("apps: startup opens the listed page, not the first-run tab")
    else:
        bad("apps: RestoreOnStartup is %r" % policy.get("RestoreOnStartup"))

if not start_page.is_file():
    bad("apps: meta-start.html is missing")
else:
    html = read(start_page)
    if re.search(r"<title>[^<]+</title>", html) and 'charset="utf-8"' in html:
        ok("apps: start page has a title and a charset")
    else:
        bad("apps: start page lacks a title or charset")
    if 'aria-label="Search the web"' in html:
        ok("apps: search field has an accessible label")
    else:
        bad("apps: search field has no aria-label")
    if 'href="#main"' in html and 'id="main"' in html and "a.skip" in html:
        ok("apps: the start page has a skip link to its content")
    else:
        bad("apps: the start page has no skip link")
    if ":focus-visible" in html:
        ok("apps: the start page has a keyboard-only focus style")
    else:
        bad("apps: the start page has no :focus-visible style")
    if "prefers-reduced-motion" in html:
        ok("apps: the start page honours reduced motion")
    else:
        bad("apps: the start page ignores prefers-reduced-motion")
    if re.search(r"outline:\s*none", html):
        bad("apps: the start page removes an outline without a replacement")
    else:
        ok("apps: the start page never removes an outline")
    remote_css = re.findall(r"@import\s+url\(['\"]?(https?://[^)'\"]+)", html)
    remote_font = re.findall(r"@font-face", html)
    if remote_css:
        bad("apps: start page imports remote CSS: %s" % ", ".join(remote_css))
    else:
        ok("apps: start page imports no remote CSS")
    if remote_font:
        bad("apps: start page declares @font-face (a font file must ship)")
    else:
        ok("apps: start page declares no @font-face")

    remote = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    if remote:
        bad("apps: start page loads remote assets: %s" % ", ".join(remote))
    else:
        ok("apps: start page loads no remote assets (works offline)")

# --- frozen colour contract -------------------------------------------
tokens_path = ISO / "contracts" / "tokens.json"
pin_path = ISO / "contracts" / "PIN.md"
css_file = ISO / "apps" / "chromium" / "tokens.css"

tokens = None
try:
    tokens = json.loads(read(tokens_path))
    ok("tokens: frozen contract vendored (%d colours)" % len(tokens))
except Exception as exc:  # noqa: BLE001
    bad("tokens: contract does not parse (%s)" % exc)

if tokens:
    not_hex = [k for k, v in tokens.items() if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(v))]
    if not_hex:
        bad("tokens: not hex colours: %s" % ", ".join(not_hex))
    else:
        ok("tokens: every colour is a 6-digit hex value")
    if set(tokens) >= {"blue", "white", "black"}:
        ok("tokens: blue, white and black are present")
    else:
        bad("tokens: the contract is missing blue/white/black")

try:
    pin = read(pin_path)
    digest = hashlib.sha256(read(tokens_path).encode("utf-8")).hexdigest()
    if digest in pin:
        ok("tokens: vendored file matches its recorded sha256")
    else:
        bad("tokens: sha256 does not match PIN.md (contract edited without a pin update)")
except FileNotFoundError:
    bad("tokens: PIN.md is missing")

if css_file.is_file():
    ok("tokens: tokens.css exists")
else:
    bad("tokens: tokens.css is missing (run node iso/tools/tokens_to_css.mjs)")

gen = subprocess.run(
    ["node", str(ISO / "tools" / "tokens_to_css.mjs"), "--check"],
    capture_output=True, text=True,
)
if gen.returncode == 0:
    ok("tokens: tokens.css is exactly what the generator produces")
else:
    bad("tokens: tokens.css is stale (%s)" % (gen.stderr.strip() or gen.stdout.strip()))

if start_page.is_file():
    page = read(start_page)
    raw = re.findall(r"#[0-9a-fA-F]{3,8}\b", page)
    if raw:
        bad("apps: start page carries raw hex colours: %s" % ", ".join(raw))
    else:
        ok("apps: start page carries no raw colours, only token variables")
    if 'href="tokens.css"' in page:
        ok("apps: start page links the generated token stylesheet")
    else:
        bad("apps: start page does not link tokens.css")

# --- wallpaper and GTK theme ------------------------------------------
wallpaper = ISO / "theme" / "wallpaper" / "meta-wallpaper.png"
if not wallpaper.is_file():
    bad("theme: meta-wallpaper.png is missing (run iso/tools/make_wallpaper.py)")
else:
    head = wallpaper.read_bytes()[:33]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        bad("theme: wallpaper is not a PNG")
    else:
        width, height, depth, colour = struct.unpack(">IIBB", head[16:26])
        if (width, height) == (1920, 1080):
            ok("theme: wallpaper is 1920x1080")
        else:
            bad("theme: wallpaper is %dx%d, expected 1920x1080" % (width, height))
        if (depth, colour) == (8, 6):
            ok("theme: wallpaper is 8-bit RGBA")
        else:
            bad("theme: wallpaper depth %d colour type %d" % (depth, colour))

gtk_css = ISO / "theme" / "gtk" / "metaos.css"
if not gtk_css.is_file():
    bad("theme: metaos.css is missing (run iso/tools/tokens_to_gtk.py)")
elif tokens:
    css = read(gtk_css)
    absent = [name for name, value in tokens.items()
              if "@define-color meta_%s %s;" % (name, value) not in css]
    if absent:
        bad("theme: gtk.css has no definition for %s" % ", ".join(sorted(absent)))
    else:
        ok("theme: every frozen token has a GTK colour name")
    hexes = re.findall(r"#[0-9A-Fa-f]{6}\b", css)
    if len(hexes) == len(tokens):
        ok("theme: gtk.css carries no colour outside the contract")
    else:
        bad("theme: gtk.css has %d hex value(s) for %d token(s)" % (len(hexes), len(tokens)))

for tool, label in (("make_wallpaper.py", "wallpaper"),
                    ("tokens_to_gtk.py", "gtk.css"),
                    ("tokens_to_grub.py", "grub theme")):
    run = subprocess.run([sys.executable, str(ISO / "tools" / tool), "--check"],
                         capture_output=True, text=True)
    if run.returncode == 0:
        ok("theme: %s is exactly what the generator produces" % label)
    else:
        bad("theme: %s is stale (%s)" % (label, (run.stdout + run.stderr).strip()))

# --- desktop backdrop channel -----------------------------------------
backdrop = ISO / "theme" / "xfce4-desktop.xml"
BACKDROP_TARGET = "/usr/share/metaos/theme/meta-wallpaper.png"
if not backdrop.is_file():
    bad("theme: xfce4-desktop.xml is missing")
else:
    try:
        channel = ET.parse(str(backdrop)).getroot()
        values = [el.get("value") for el in channel.iter("property")]
        if channel.get("name") != "xfce4-desktop":
            bad("theme: backdrop channel is %r, expected 'xfce4-desktop'" % channel.get("name"))
        elif BACKDROP_TARGET not in values:
            bad("theme: the backdrop channel never points at %s" % BACKDROP_TARGET)
        else:
            ok("theme: the backdrop channel points at the installed wallpaper")
    except ET.ParseError as exc:
        bad("theme: xfce4-desktop.xml does not parse (%s)" % exc)

# --- login screen ------------------------------------------------------
GREETER_CONF = ISO / "theme" / "lightdm" / "lightdm-gtk-greeter.conf"
GREETER_THEME = ISO / "theme" / "lightdm" / "themes" / "MetaOS" / "index.theme"
GREETER_CSS = ISO / "theme" / "lightdm" / "themes" / "MetaOS" / "gtk-3.0" / "gtk.css"
GREETER_BG = "/usr/share/metaos/theme/greeter-wallpaper.png"

greeter_wall = ISO / "theme" / "wallpaper" / "greeter-wallpaper.png"
if not greeter_wall.is_file():
    bad("lightdm: greeter-wallpaper.png is missing (run iso/tools/make_wallpaper.py)")
else:
    head = greeter_wall.read_bytes()[:33]
    width, height = struct.unpack(">II", head[16:24])
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        bad("lightdm: greeter wallpaper is not a PNG")
    elif (width, height) != (1920, 1080):
        bad("lightdm: greeter wallpaper is %dx%d, expected 1920x1080" % (width, height))
    else:
        ok("lightdm: greeter wallpaper is a 1920x1080 PNG")

if not GREETER_CONF.is_file():
    bad("lightdm: lightdm-gtk-greeter.conf is missing")
else:
    cfg = ini(GREETER_CONF)
    if not cfg.has_section("greeter"):
        bad("lightdm: greeter conf has no [greeter] section")
    else:
        greeter = cfg["greeter"]
        if greeter.get("background") == GREETER_BG:
            ok("lightdm: greeter uses the MetaOS backdrop")
        else:
            bad("lightdm: greeter background is %r" % greeter.get("background"))
        if greeter.get("theme-name") == "MetaOS":
            ok("lightdm: greeter asks for the MetaOS theme")
        else:
            bad("lightdm: greeter theme-name is %r" % greeter.get("theme-name"))

if not GREETER_THEME.is_file():
    bad("lightdm: themes/MetaOS/index.theme is missing")
else:
    idx = ini(GREETER_THEME)
    if idx.get("Desktop Entry", "Name", fallback="") == "MetaOS":
        ok("lightdm: the theme directory names itself MetaOS")
    else:
        bad("lightdm: index.theme Name is %r"
            % idx.get("Desktop Entry", "Name", fallback=""))

if not GREETER_CSS.is_file():
    bad("lightdm: themes/MetaOS/gtk-3.0/gtk.css is missing")
elif tokens:
    sheet = read(GREETER_CSS)
    absent = [name for name, value in tokens.items()
              if "@define-color meta_%s %s;" % (name, value) not in sheet]
    if absent:
        bad("lightdm: greeter.css has no definition for %s" % ", ".join(sorted(absent)))
    else:
        ok("lightdm: every frozen token reaches the login screen")

# --- boot menu ---------------------------------------------------------
GRUB_DIR = ISO / "boot" / "grub" / "themes" / "metaos"
GRUB_TXT = GRUB_DIR / "theme.txt"
GRUB_DROPIN = ISO / "boot" / "grub" / "metaos-theme.cfg"
GRUB_TARGET = "/boot/grub/themes/metaos/theme.txt"

if not GRUB_TXT.is_file():
    bad("grub: theme.txt is missing (run iso/tools/tokens_to_grub.py)")
else:
    body = read(GRUB_TXT)
    image = re.search(r'desktop-image:\s*"([^"]+)"', body)
    if not image:
        bad("grub: theme.txt names no desktop-image")
    elif not (GRUB_DIR / image.group(1)).is_file():
        bad("grub: theme image %r is not next to theme.txt" % image.group(1))
    else:
        ok("grub: the theme image ships beside theme.txt (%s)" % image.group(1))

    needed = ("left", "top", "width", "height", "item_color", "selected_item_color")
    if "+ boot_menu" not in body:
        bad("grub: theme.txt has no boot_menu block")
    else:
        absent = [key for key in needed if not re.search(r"\b%s\s*=" % key, body)]
        if absent:
            bad("grub: boot_menu is missing %s" % ", ".join(absent))
        else:
            ok("grub: the boot menu block has geometry and both colours")

    if tokens:
        values = {value.upper() for value in tokens.values()}
        stray = sorted({hit.upper() for hit in re.findall(r"#[0-9A-Fa-f]{6}\b", body)} - values)
        if stray:
            bad("grub: colours outside the contract: %s" % ", ".join(stray))
        else:
            ok("grub: every colour in the boot theme is a contract colour")

if not GRUB_DROPIN.is_file():
    bad("grub: metaos-theme.cfg is missing")
else:
    dropin = read(GRUB_DROPIN)
    if re.search(r'^GRUB_THEME="?%s"?\s*$' % re.escape(GRUB_TARGET), dropin, re.M):
        ok("grub: the drop-in points at the shipped theme")
    else:
        bad("grub: the drop-in does not set GRUB_THEME to %s" % GRUB_TARGET)
    if re.search(r"^GRUB_CMDLINE_LINUX(_DEFAULT)?=", dropin, re.M):
        bad("grub: the drop-in rewrites the kernel command line")
    else:
        ok("grub: the drop-in leaves the kernel command line alone")

# --- no stub markers ---------------------------------------------------
bad_marks = []
for path in ISO.rglob("*"):
    # tools/ holds the checkers themselves; their own source names the
    # markers they look for, so scanning them would always fail.
    if path.parent.name == "tools":
        continue
    if path.is_file() and path.suffix in {
        ".md", ".conf", ".desc", ".script", ".html", ".json", ".desktop",
        ".dockitem", ".plymouth", ".py", ".qss",
    }:
        body = read(path)
        # Assembled, not literal, so this file does not trip its own scan.
        for mark in ("TO" + "DO", "FIX" + "ME", "PLACE" + "HOLDER"):
            if mark in body:
                bad_marks.append("%s contains %s" % (path.relative_to(ISO), mark))
if bad_marks:
    for note in bad_marks:
        bad("stub marker: " + note)
else:
    ok("no TODO/FIXME/PLACEHOLDER markers in the ISO lane")

# --- summary -----------------------------------------------------------
if AS_JSON:
    print(json.dumps({
        "counts": {"pass": len(passes), "fail": len(fails), "skip": len(skips)},
        "pass": passes,
        "fail": fails,
        "skip": skips,
    }, indent=2))
else:
    print()
    print("%d passed, %d failed, %d skipped" % (len(passes), len(fails), len(skips)))
    if fails:
        for note in fails:
            print("  failed: " + note)
sys.exit(1 if fails else 0)
