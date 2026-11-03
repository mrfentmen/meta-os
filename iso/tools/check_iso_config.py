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
import subprocess
import sys
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
passes, fails, skips = [], [], []


def ok(msg):
    passes.append(msg)
    print("PASS  " + msg)


def bad(msg):
    fails.append(msg)
    print("FAIL  " + msg)


def skip(msg):
    skips.append(msg)
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
    if slideshow and (branding.parent / slideshow).is_file():
        ok("calamares: slideshow file exists")
    else:
        bad("calamares: slideshow %r does not exist" % slideshow)

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

locale_cfg = module_conf("locale.conf")
if locale_cfg:
    if locale_cfg.get("region") and locale_cfg.get("zone"):
        ok("calamares: locale preseeded to %s/%s"
           % (locale_cfg.get("region"), locale_cfg.get("zone")))
    else:
        bad("calamares: locale.conf has no region/zone")

# --- desktop entries ---------------------------------------------------
# Binaries the base image already supplies.
SYSTEM_APPS = {"thunar", "xfce4-terminal", "xfce4-settings-manager", "chromium"}
# Binaries this lane ships. The value is the file that must exist.
SHIPPED_APPS = {"meta-agent-status": Path("apps") / "agent-status" / "meta-agent-status.py"}
APPS = SYSTEM_APPS | set(SHIPPED_APPS)

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
        bad("apps: %s runs %r, which is neither a system app nor a shipped one"
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
print()
print("%d passed, %d failed, %d skipped" % (len(passes), len(fails), len(skips)))
if fails:
    for note in fails:
        print("  failed: " + note)
    sys.exit(1)
sys.exit(0)
