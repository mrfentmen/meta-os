#!/usr/bin/env python3
"""MetaOS boot/installer lane config validator.

Runs anywhere with python3. YAML is parsed through Ruby's psych (the repo
build Mac has no PyYAML); if ruby is absent those checks are SKIPped, never
counted as passes.

What it proves, and what it does not:
  PASS  the configs are structurally valid, cross-referenced, and the assets
        are the ones the manifest recorded
  NOT   that Calamares, Plymouth or the installer run. That is the VM proof
        (tools/vm_install_proof.sh) on a Linux host. Nothing here is a
        substitute for it.

Exit 0 only when there are zero FAILs.
"""

import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = os.path.dirname(HERE)
CAL = os.path.join(ISO, "calamares")
MODS = os.path.join(CAL, "modules")
BRAND = os.path.join(CAL, "branding", "metaos")
PLY = os.path.join(ISO, "plymouth", "metaos")

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results = []


def record(state, name, detail=""):
    results.append((state, name, detail))
    print(f"  [{state}] {name}" + (f" — {detail}" if detail else ""))


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


RUBY = shutil.which("ruby")


def yaml_load(path):
    """Parse a YAML file via ruby+json. Returns (ok, data_or_error)."""
    if not RUBY:
        return None, "ruby missing"
    code = "require 'yaml'; require 'json'; puts JSON.dump(YAML.load_file(ARGV[0]))"
    proc = subprocess.run(
        [RUBY, "-e", code, path], capture_output=True, text=True
    )
    if proc.returncode != 0:
        first = (proc.stderr or "").strip().splitlines()
        return False, first[0] if first else "ruby parse failed"
    try:
        return True, json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return False, f"json round-trip: {exc}"


def check_yaml_tree():
    files = [
        os.path.join(CAL, "settings.conf"),
        os.path.join(CAL, "branding", "metaos", "branding.desc"),
    ]
    files += sorted(
        os.path.join(MODS, f) for f in os.listdir(MODS) if f.endswith(".conf")
    )
    if not RUBY:
        record(SKIP, "yaml parse", "ruby not installed; PyYAML absent on this Mac")
        return {}
    parsed = {}
    bad = 0
    for path in files:
        ok, data = yaml_load(path)
        if ok is None:
            record(SKIP, f"yaml {os.path.relpath(path, ISO)}", data)
            continue
        if not ok:
            record(FAIL, f"yaml {os.path.relpath(path, ISO)}", str(data))
            bad += 1
        else:
            parsed[os.path.relpath(path, ISO)] = data
    if bad == 0:
        record(PASS, "yaml parse", f"{len(files)} files")
    return parsed


def check_settings(parsed):
    key = "calamares/settings.conf"
    data = parsed.get(key)
    if data is None:
        record(SKIP, "settings sequence", "settings.conf did not parse")
        return
    seq = data.get("sequence") or []
    show, exe = [], []
    for block in seq:
        if isinstance(block, dict):
            show += block.get("show") or []
            exe += block.get("exec") or []
    if not show or not exe:
        record(FAIL, "settings sequence", f"show={len(show)} exec={len(exe)}")
        return
    # Core modules with no config file of their own in this lane.
    no_config = {"mount"}
    missing = [
        m for m in show + exe
        if m not in no_config and not os.path.exists(os.path.join(MODS, f"{m}.conf"))
    ]
    if missing:
        record(FAIL, "settings -> module configs", "missing: " + ", ".join(sorted(set(missing))))
    else:
        record(PASS, "settings -> module configs", f"{len(set(show + exe))} modules, all present")

    inst = data.get("instances") or []
    inst_missing = [
        i.get("config") for i in inst
        if isinstance(i, dict) and not os.path.exists(os.path.join(MODS, i.get("config", "")))
    ]
    if inst_missing:
        record(FAIL, "settings -> instance configs", "missing: " + ", ".join(map(str, inst_missing)))
    else:
        record(PASS, "settings -> instance configs", f"{len(inst)} instance(s)")

    if data.get("branding") != "metaos":
        record(FAIL, "settings branding", f"expected metaos, got {data.get('branding')!r}")
    else:
        record(PASS, "settings branding", "metaos")
    if data.get("disable-cancel") is not True:
        record(FAIL, "settings disable-cancel", "must be true: a cancelled install leaves a dead disk")
    else:
        record(PASS, "settings disable-cancel", "true")


def check_branding(parsed):
    data = parsed.get("calamares/branding/metaos/branding.desc")
    if data is None:
        record(SKIP, "branding.desc", "did not parse")
        return
    strings = data.get("strings") or {}
    if strings.get("productName") != "MetaOS":
        record(FAIL, "branding productName", f"got {strings.get('productName')!r}")
    else:
        record(PASS, "branding productName", "MetaOS")
    images = data.get("images") or {}
    expect = {"productLogo": (256, 256), "productIcon": (128, 128), "productWelcome": (640, 400)}
    for key, dims in expect.items():
        name = images.get(key)
        if not name:
            record(FAIL, f"branding image {key}", "key missing")
            continue
        path = os.path.join(BRAND, name)
        if not os.path.exists(path):
            record(FAIL, f"branding image {key}", f"file missing: {name}")
            continue
        got = png_size(path)
        if got != dims:
            record(FAIL, f"branding image {key}", f"{name} is {got}, expected {dims}")
        else:
            record(PASS, f"branding image {key}", f"{name} {got[0]}x{got[1]}")
    if not os.path.exists(os.path.join(BRAND, "stylesheet.qss")):
        record(FAIL, "branding stylesheet", "stylesheet.qss missing")
    else:
        record(PASS, "branding stylesheet", "present")


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return (-1, -1)
    w = int.from_bytes(head[16:20], "big")
    h = int.from_bytes(head[20:24], "big")
    return (w, h)


def check_plymouth():
    descriptor = os.path.join(PLY, "metaos.plymouth")
    cp = configparser.ConfigParser()
    try:
        cp.read(descriptor)
    except configparser.Error as exc:
        record(FAIL, "plymouth .plymouth ini", str(exc))
        return
    if cp.get("Plymouth Theme", "ModuleName", fallback="") != "script":
        record(FAIL, "plymouth module", "must be 'script'")
    else:
        record(PASS, "plymouth module", "script")
    image_dir = cp.get("script", "ImageDir", fallback="")
    script_file = cp.get("script", "ScriptFile", fallback="")
    if os.path.isabs(image_dir) and image_dir.endswith("/themes/metaos"):
        record(PASS, "plymouth ImageDir", image_dir)
    else:
        record(FAIL, "plymouth ImageDir", f"unexpected: {image_dir!r}")
    local_script = os.path.join(PLY, os.path.basename(script_file))
    if os.path.exists(local_script):
        record(PASS, "plymouth ScriptFile", os.path.basename(script_file))
    else:
        record(FAIL, "plymouth ScriptFile", f"missing {script_file}")

    script = read(os.path.join(PLY, "metaos.script"))
    refs = re.findall(r'Image\("([^"]+)"\)', script)
    missing = [r for r in refs if not os.path.exists(os.path.join(PLY, r))]
    if missing:
        record(FAIL, "plymouth image refs", "missing: " + ", ".join(sorted(set(missing))))
    else:
        record(PASS, "plymouth image refs", ", ".join(sorted(set(refs))))

    if script.count("{") != script.count("}"):
        record(FAIL, "plymouth brace balance", f"{script.count('{')} open, {script.count('}')} close")
    elif script.count("(") != script.count(")"):
        record(FAIL, "plymouth paren balance", f"{script.count('(')} open, {script.count(')')} close")
    else:
        record(PASS, "plymouth brace/paren balance", "balanced")

    # Deliberate restrictions: no trig, no loops, no font files. A future
    # edit that adds them needs a real plymouth run before it ships.
    banned = [t for t in ("Math.", "for (", "loadfont", ".ttf") if t in script]
    if banned:
        record(FAIL, "plymouth conservative-subset", "found: " + ", ".join(banned))
    else:
        record(PASS, "plymouth conservative-subset", "no trig/loops/fonts")
    if "Plymouth.SetRefreshFunction" not in script:
        record(FAIL, "plymouth refresh hook", "SetRefreshFunction missing")
    else:
        record(PASS, "plymouth refresh hook", "present")


def check_preseed(parsed):
    checks = [
        ("calamares/modules/welcome.conf", lambda d: d.get("required") is False,
         "welcome not blocking"),
        ("calamares/modules/keyboard.conf", lambda d: d.get("layout") == "us",
         "keyboard us"),
        ("calamares/modules/partition.conf",
         lambda d: d.get("initialPartitioningChoice") == "erase"
         and d.get("userSwapChoices") == ["none"],
         "partition: erase + no swap"),
        ("calamares/modules/users.conf",
         lambda d: (d.get("user") or {}).get("login") == "meta"
         and d.get("allowWeakPasswords") is False,
         "user meta, weak passwords refused"),
        ("calamares/modules/unpackfs.conf",
         lambda d: (d.get("unpack") or [{}])[0].get("source") == "/cdrom/casper/filesystem.squashfs",
         "unpack from /cdrom/casper"),
        ("calamares/modules/packages.conf",
         lambda d: not (d.get("install") or []),
         "no network installs during setup"),
        ("calamares/modules/meta-branding.conf",
         lambda d: d.get("dontChroot") is False
         and (d.get("script") or [""])[0] == "/usr/local/lib/metaos/meta-branding.sh",
         "in-target hook, absolute path"),
        ("calamares/modules/finished.conf",
         lambda d: d.get("restartNowChecked") is True,
         "reboot pre-checked"),
    ]
    for key, predicate, label in checks:
        data = parsed.get(key)
        if data is None:
            record(SKIP, f"preseed {label}", f"{key} did not parse")
            continue
        try:
            ok = predicate(data)
        except Exception as exc:  # noqa: BLE001 - a malformed shape is a FAIL, with the reason
            record(FAIL, f"preseed {label}", f"{type(exc).__name__}: {exc}")
            continue
        record(PASS if ok else FAIL, f"preseed {label}", key)


def check_hook_path_crossref():
    provision = read(os.path.join(ISO, "provision.sh"))
    hook = "/usr/local/lib/metaos/meta-branding.sh"
    if hook in provision and os.path.exists(os.path.join(CAL, "meta-branding.sh")):
        record(PASS, "hook path crossref", hook)
    else:
        record(FAIL, "hook path crossref", f"{hook} not installed by provision.sh")
    if 'exec calamares' in read(os.path.join(ISO, "provision.sh")):
        record(PASS, "autostart exec", "calamares launched from autostart")
    else:
        record(FAIL, "autostart exec", "no calamares exec line in provision.sh")


def check_manifest():
    path = os.path.join(ISO, "assets", "MANIFEST.json")
    if not os.path.exists(path):
        record(FAIL, "asset manifest", "assets/MANIFEST.json missing")
        return
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    bad = []
    for entry in data.get("assets", []):
        asset = os.path.join(ISO, entry["path"])
        if not os.path.exists(asset):
            bad.append(f"{entry['path']} missing")
            continue
        digest = hashlib.sha256(open(asset, "rb").read()).hexdigest()
        if digest != entry["sha256"]:
            bad.append(f"{entry['path']} hash drift")
    if bad:
        record(FAIL, "asset manifest", "; ".join(bad))
    else:
        record(PASS, "asset manifest", f"{len(data.get('assets', []))} assets match sha256")


FORBIDDEN = re.compile(r"\b(Apple|macOS|Cupertino|Helvetica|SF Pro|Aqua)\b", re.IGNORECASE)


def check_originality():
    # Scan only what ships in the image: the plymouth payload, the Calamares
    # payload and the provisioner. tools/ and assets/ necessarily spell the
    # forbidden words in code and docstrings ("no Apple artwork"), and they
    # are never copied into the ISO, so scanning them is a false positive.
    fonts, bad_strings = [], []
    text_ext = {".conf", ".desc", ".qss", ".sh", ".script", ".plymouth"}
    shipped = [
        os.path.join(ISO, "plymouth"),
        os.path.join(ISO, "calamares"),
    ]
    targets = []
    for base in shipped:
        for root, _dirs, files in os.walk(base):
            for name in files:
                targets.append(os.path.join(root, name))
    targets.append(os.path.join(ISO, "provision.sh"))
    for path in targets:
        if os.path.relpath(path, ISO).startswith(("work", "proof")):
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext in {".ttf", ".otf", ".woff", ".woff2", ".icns"}:
            fonts.append(os.path.relpath(path, ISO))
            continue
        if ext not in text_ext:
            continue
        for lineno, line in enumerate(read(path).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", "/*", "*", ";")):
                continue
            if FORBIDDEN.search(line):
                bad_strings.append(f"{os.path.relpath(path, ISO)}:{lineno}")
    if fonts:
        record(FAIL, "original assets (fonts/icons)", "found: " + ", ".join(fonts))
    else:
        record(PASS, "original assets (fonts/icons)", "no font or .icns files shipped")
    if bad_strings:
        record(FAIL, "original assets (strings)", "Apple-adjacent values at " + ", ".join(bad_strings))
    else:
        record(PASS, "original assets (strings)", "no Apple-adjacent values outside comments")


def check_scripts():
    shells = [
        (os.path.join(ISO, "provision.sh"), "sh"),
        (os.path.join(CAL, "meta-branding.sh"), "sh"),
        (os.path.join(ISO, "build_iso.sh"), "bash"),
        (os.path.join(HERE, "vm_install_proof.sh"), "bash"),
    ]
    for path, shell in shells:
        proc = subprocess.run([shell, "-n", path], capture_output=True, text=True)
        if proc.returncode != 0:
            record(FAIL, f"{shell} -n {os.path.relpath(path, ISO)}", proc.stderr.strip().splitlines()[0])
        else:
            record(PASS, f"{shell} -n {os.path.relpath(path, ISO)}", "syntax ok")

    py_files = [
        os.path.join(ISO, "assets", "make_assets.py"),
        os.path.join(HERE, "qmp.py"),
        os.path.join(HERE, "check_configs.py"),
    ]
    py_bad = []
    for path in py_files:
        try:
            compile(read(path), path, "exec")
        except SyntaxError as exc:
            py_bad.append(f"{os.path.basename(path)}:{exc.lineno}")
    record(FAIL if py_bad else PASS, "python syntax", "; ".join(py_bad) if py_bad else f"{len(py_files)} files")


def check_pngs():
    bad = []
    for root, _dirs, files in os.walk(ISO):
        if "work" in root.split(os.sep) or "proof" in root.split(os.sep):
            continue
        for name in files:
            if not name.endswith(".png"):
                continue
            path = os.path.join(root, name)
            if png_size(path)[0] <= 0:
                bad.append(os.path.relpath(path, ISO))
    record(FAIL if bad else PASS, "png headers", ", ".join(bad) if bad else "all readable")


def main():
    print("MetaOS boot/installer lane — config validation")
    print(f"lane root: {os.path.relpath(ISO, os.path.dirname(ISO))}")
    if not RUBY:
        print("note: ruby missing -> yaml checks skipped (not counted as passes)")
    parsed = check_yaml_tree()
    check_settings(parsed)
    check_branding(parsed)
    check_preseed(parsed)
    check_plymouth()
    check_hook_path_crossref()
    check_manifest()
    check_originality()
    check_scripts()
    check_pngs()

    counts = {PASS: 0, FAIL: 0, SKIP: 0}
    for state, _name, _detail in results:
        counts[state] += 1
    print(f"\n{counts[PASS]} pass, {counts[FAIL]} fail, {counts[SKIP]} skip")
    if counts[FAIL]:
        print("FAIL — do not call this lane verified")
        return 1
    print("PASS on structure only. ISO build and VM install remain UNRUN on this host.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
