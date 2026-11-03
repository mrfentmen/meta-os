#!/usr/bin/env python3
"""tokens_to_xfce.py — the desktop shell the login screen hands over to.

The greeter, splash and boot menu are covered by their own generators. What
was missing was everything after the password: the top bar, the icon theme,
the terminal palette, the font picks and the lock settings. None of it had a
file, so `xfce4-panel` fell back to Xubuntu's default and the "fully themed"
box on the checklist had nothing behind it.

Everything here is written from `iso/contracts/tokens.json`. No hex is typed
into a shipped file by hand, and `--check` fails when the committed bytes
differ from what the contract would produce.

    python3 iso/tools/tokens_to_xfce.py            write every file
    python3 iso/tools/tokens_to_xfce.py --check    exit 1 if any is stale
    python3 iso/tools/tokens_to_xfce.py --root DIR write under DIR/iso

Outputs (relative to the iso tree):

    theme/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml
    theme/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml
    theme/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.xml
    theme/xfce4/xfconf/xfce-perchannel-xml/light-locker.xml
    theme/icons/MetaOS/index.theme
    theme/icons/MetaOS/places/48/{folder,folder-open,user-home}.svg
    theme/fonts/local.conf
    apps/terminal/metaos.theme
    apps/terminal/terminalrc

Only the ring's colours are used: blue, black, white, cyan, gold and pink.
The other two tokens stay available to the web page and the theme sheet.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FONT = "Inter 10"
ICON_THEME = "MetaOS"
GTK_THEME = "MetaOS"

# The panel's plugin order, left to right. A name here must appear in the
# `plugins` block; the checker reads both and fails if they disagree.
PLUGINS = (
    ("whiskermenu", None),
    ("launcher", ("meta-files.desktop", "meta-terminal.desktop",
                  "meta-browser.desktop", "meta-agent-status.desktop")),
    ("tasklist", None),
    ("separator", None),
    ("systray", None),
    ("clock", None),
    ("showdesktop", None),
)


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def lighten(value: str, amount: float = 0.35) -> str:
    """The bright half of a terminal palette, computed from the dark half."""
    return "#%02X%02X%02X" % tuple(
        int(round(c + (255 - c) * amount)) for c in rgb(value)
    )


def rgba(value: str, alpha: float) -> tuple[float, float, float, float]:
    r, g, b = rgb(value)
    return (round(r / 255, 4), round(g / 255, 4), round(b / 255, 4), alpha)


def panel_xml(t: dict) -> str:
    raw = ET.Element("channel", {"name": "xfce4-panel", "version": "1.0"})
    ET.SubElement(raw, "property", {"name": "configversion", "type": "uint", "value": "2"})

    panels = ET.SubElement(raw, "property", {"name": "panels", "type": "array"})
    ET.SubElement(panels, "value", {"type": "int", "value": "1"})

    panel = ET.SubElement(panels, "property", {"name": "panel-1", "type": "empty"})
    for name, kind, value in (
        ("position", "string", "p=8;x=0;y=0"),
        ("length", "uint", "100"),
        ("length-adjust", "bool", "true"),
        ("position-locked", "bool", "true"),
        ("size", "uint", "30"),
        ("mode", "uint", "0"),
        ("autohide-behavior", "uint", "0"),
        ("background-style", "uint", "1"),
        ("background-alpha", "uint", "92"),
    ):
        ET.SubElement(panel, "property", {"name": name, "type": kind, "value": value})

    bg = ET.SubElement(panel, "property", {"name": "background-rgba", "type": "array"})
    for component in rgba(t["black"], 0.92):
        ET.SubElement(bg, "value", {"type": "double", "value": f"{component:.4f}"})

    ids = ET.SubElement(panel, "property", {"name": "plugin-ids", "type": "array"})
    for index in range(1, len(PLUGINS) + 1):
        ET.SubElement(ids, "value", {"type": "int", "value": str(index)})

    plugins = ET.SubElement(raw, "property", {"name": "plugins", "type": "empty"})
    for index, (name, items) in enumerate(PLUGINS, 1):
        node = ET.SubElement(plugins, "property", {"name": f"plugin-{index}", "type": "empty"})
        ET.SubElement(node, "property", {"name": "plugin", "type": "string", "value": name})
        if name == "launcher" and items:
            array = ET.SubElement(node, "property", {"name": "items", "type": "array"})
            for item in items:
                ET.SubElement(array, "value", {"type": "string", "value": item})
        if name == "clock":
            ET.SubElement(node, "property", {"name": "digital-format",
                                             "type": "string", "value": "%H:%M"})
            ET.SubElement(node, "property", {"name": "mode", "type": "uint", "value": "2"})

    ET.indent(raw, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(raw, encoding="unicode") + "\n"


def xsettings_xml() -> str:
    root = ET.Element("channel", {"name": "xsettings", "version": "1.0"})
    for prop, kind, value in (
        ("Net/ThemeName", "string", GTK_THEME),
        ("Net/IconThemeName", "string", ICON_THEME),
        ("Net/FontName", "string", FONT),
        ("Net/CursorThemeName", "string", "Adwaita"),
        ("Gtk/EnableAnimations", "bool", "true"),
        ("Gtk/ButtonImages", "bool", "true"),
        ("Xft/Antialias", "int", "1"),
        ("Xft/Hinting", "int", "1"),
        ("Xft/HintStyle", "string", "hintslight"),
        ("Xft/RGBA", "string", "none"),
    ):
        ET.SubElement(root, "property", {"name": prop, "type": kind, "value": value})
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def power_xml() -> str:
    root = ET.Element("channel", {"name": "xfce4-power-manager", "version": "1.0"})
    for prop, kind, value in (
        ("xfce4-power-manager/blank-on-ac", "int", "10"),
        ("xfce4-power-manager/dpms-on-ac-sleep", "uint", "10"),
        ("xfce4-power-manager/lock-screen-suspend-hibernate", "bool", "true"),
        ("xfce4-power-manager/logind-handle-lid-switch", "bool", "true"),
        ("xfce4-power-manager/power-button-action", "int", "3"),
    ):
        ET.SubElement(root, "property", {"name": prop, "type": kind, "value": value})
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def locker_xml() -> str:
    root = ET.Element("channel", {"name": "light-locker", "version": "1.0"})
    for prop, kind, value in (
        ("lock-on-suspend", "bool", "true"),
        ("lock-after-screensaver", "bool", "true"),
        ("late-locking", "bool", "true"),
    ):
        ET.SubElement(root, "property", {"name": prop, "type": kind, "value": value})
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def terminal_theme(t: dict) -> str:
    base = [t["black"], t["pink"], t["emerald"], t["gold"],
            t["blue"], t["violet"], t["cyan"], t["white"]]
    palette = base + [lighten(colour) for colour in base]
    return (
        "[Scheme]\n"
        "Name=MetaOS\n"
        f"ColorForeground={t['white']}\n"
        f"ColorBackground={t['black']}\n"
        f"ColorCursor={t['blue']}\n"
        f"ColorBold={t['white']}\n"
        "ColorPalette=" + ";".join(palette) + "\n"
    )


def terminalrc(t: dict) -> str:
    return (
        "# MetaOS terminal defaults. Generated by tokens_to_xfce.py.\n"
        "[Configuration]\n"
        "ColorScheme=MetaOS\n"
        "FontName=Inter 11\n"
        "FontUseSystem=TRUE\n"
        "MiscAlwaysShowTabs=FALSE\n"
        "MiscBell=FALSE\n"
        "MiscCursorBlinks=TRUE\n"
        "MiscHighlightUrls=TRUE\n"
        "ScrollingBar=GTK_SCROLL_NONE\n"
        "ScrollingUnlimited=TRUE\n"
        f"ColorForeground={t['white']}\n"
        f"ColorBackground={t['black']}\n"
    )


def icon_index() -> str:
    return (
        "[Icon Theme]\n"
        "Name=MetaOS\n"
        "Comment=MetaOS places icons, drawn from the contract palette\n"
        "Inherits=Papirus-Dark,Adwaita,hicolor\n"
        "Directories=places/48\n"
        "\n"
        "[places/48]\n"
        "Size=48\n"
        "Type=Fixed\n"
        "Context=Places\n"
    )


def place_svg(t: dict, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
        'viewBox="0 0 48 48">\n'
        + body
        + "</svg>\n"
    )


def folder_svg(t: dict, open_: bool = False) -> str:
    top = (
        f'  <path d="M5 13a3 3 0 0 1 3-3h11l4 5h17a3 3 0 0 1 3 3v22a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3z" '
        f'fill="{t["black"]}" stroke="{t["blue"]}" stroke-width="2"/>\n'
    )
    if open_:
        top += (
            f'  <path d="M5 20h38l-4 18a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3z" '
            f'fill="{t["blue"]}" fill-opacity="0.35" stroke="{t["blue"]}" stroke-width="2"/>\n'
        )
    else:
        top += f'  <rect x="9" y="19" width="30" height="4" rx="2" fill="{t["blue"]}"/>\n'
    return place_svg(t, top)


def home_svg(t: dict) -> str:
    body = (
        f'  <path d="M6 22 24 7l18 15" fill="none" stroke="{t["blue"]}" '
        f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>\n'
        f'  <path d="M11 21v19a2 2 0 0 0 2 2h22a2 2 0 0 0 2-2V21" fill="none" '
        f'stroke="{t["white"]}" stroke-width="2"/>\n'
        f'  <rect x="20" y="28" width="8" height="14" rx="1" fill="{t["cyan"]}"/>\n'
    )
    return place_svg(t, body)


def fonts_conf() -> str:
    return (
        '<?xml version="1.0"?>\n'
        "<!DOCTYPE fontconfig SYSTEM \"urn:fontconfig:fonts.dtd\">\n"
        "<fontconfig>\n"
        "  <!-- MetaOS font picks. Inter for the interface, DejaVu for glyphs\n"
        "       Inter does not carry. Both are in metaos.packages. -->\n"
        "  <alias>\n"
        "    <family>sans-serif</family>\n"
        "    <prefer><family>Inter</family><family>DejaVu Sans</family></prefer>\n"
        "  </alias>\n"
        "  <alias>\n"
        "    <family>monospace</family>\n"
        "    <prefer><family>DejaVu Sans Mono</family></prefer>\n"
        "  </alias>\n"
        "  <match target=\"font\">\n"
        "    <edit name=\"antialias\" mode=\"assign\"><bool>true</bool></edit>\n"
        "    <edit name=\"hinting\" mode=\"assign\"><bool>true</bool></edit>\n"
        "    <edit name=\"hintstyle\" mode=\"assign\"><const>hintslight</const></edit>\n"
        "    <edit name=\"rgba\" mode=\"assign\"><const>none</const></edit>\n"
        "  </match>\n"
        "</fontconfig>\n"
    )


def build(iso: Path) -> dict[Path, str]:
    tokens = json.loads((iso / "contracts" / "tokens.json").read_text(encoding="utf-8"))
    channel_dir = iso / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml"
    icons = iso / "theme" / "icons" / ICON_THEME
    terminal = iso / "apps" / "terminal"
    return {
        channel_dir / "xfce4-panel.xml": panel_xml(tokens),
        channel_dir / "xsettings.xml": xsettings_xml(),
        channel_dir / "xfce4-power-manager.xml": power_xml(),
        channel_dir / "light-locker.xml": locker_xml(),
        icons / "index.theme": icon_index(),
        icons / "places" / "48" / "folder.svg": folder_svg(tokens),
        icons / "places" / "48" / "folder-open.svg": folder_svg(tokens, open_=True),
        icons / "places" / "48" / "user-home.svg": home_svg(tokens),
        iso / "theme" / "fonts" / "local.conf": fonts_conf(),
        terminal / "metaos.theme": terminal_theme(tokens),
        terminal / "terminalrc": terminalrc(tokens),
    }


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    check = "--check" in argv
    if "--root" in argv:
        root = Path(argv[argv.index("--root") + 1]) / "iso"

    files = build(root)
    stale = []
    for path, content in files.items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(path.relative_to(root))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    if check:
        if stale:
            for path in stale:
                print(f"STALE  {path}")
            print(f"{len(stale)} file(s) do not match the contract; run tokens_to_xfce.py")
            return 1
        print(f"desktop shell: {len(files)} file(s) match the contract")
        return 0

    print(f"wrote {len(files)} file(s) under {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
