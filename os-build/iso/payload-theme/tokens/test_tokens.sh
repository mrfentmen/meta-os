#!/bin/sh
# test_tokens.sh — prove the generated theme still agrees with the tokens.
#
# Run: sh os-build/iso/payload-theme/tokens/test_tokens.sh
# Exits 0 only when every row passes. No row is skipped silently: a missing
# python3 or a missing file is a FAIL, because a checker that cannot run is not
# a pass.
#
# What this catches that the generator cannot check about itself:
#   - a hand-edit to one of the four generated files (drift);
#   - a token change that produces a file a consumer would reject (bad XML,
#     plank colour out of range, alpha maths off by one);
#   - the one assertion theme_proof.sh makes about gtk.css (that it names Inter);
#   - Ubuntu leaking back into a visible surface.
set -u
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
THEME=$(dirname -- "$HERE")
fail=0
pass=0

ok() { echo "PASS $1"; pass=$((pass + 1)); }
no() { echo "FAIL $1: $2"; fail=$((fail + 1)); }

if ! command -v python3 >/dev/null 2>&1; then
  echo "FAIL python3: not on PATH, cannot verify tokens at all" >&2
  exit 1
fi

# ---- 1. the token file itself
if python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$HERE/meta.tokens.json" 2>/dev/null; then
  ok "tokens: meta.tokens.json parses"
else
  no "tokens" "meta.tokens.json is not valid JSON"
fi

# ---- 2. no drift
drift=$(python3 "$HERE/gen_theme.py" --check 2>&1)
if [ $? -eq 0 ]; then
  ok "drift: all four generated files match the tokens"
else
  no "drift" "$(echo "$drift" | sed -n 's/^FAIL  //p' | tr '\n' ' ')"
fi

# ---- 3. gtk.css contracts
GTK="$THEME/gtk/gtk.css"
if [ -f "$GTK" ]; then
  # theme_proof.sh line ~186 greps exactly this string on the target.
  if grep -q "'Inter'" "$GTK"; then
    ok "gtk: names 'Inter' (theme_proof.sh's font row)"
  else
    no "gtk" "no 'Inter' in font-family — theme_proof.sh will fail on the image"
  fi
  if grep -q '@define-color meta_accent #4f7ec2;' "$GTK"; then
    ok "gtk: accent is #4f7ec2 from the tokens"
  else
    no "gtk" "accent is not the token value"
  fi
  opens=$(grep -c '{' "$GTK"); closes=$(grep -c '}' "$GTK")
  if [ "$opens" -eq "$closes" ]; then
    ok "gtk: braces balance ($opens blocks)"
  else
    no "gtk" "unbalanced braces: $opens open, $closes close"
  fi
  # A GTK parse error makes the desktop fall back to Adwaita silently, which is
  # exactly the "why does it look like Ubuntu again" bug. This is the cheapest
  # structural check available without a GTK runtime.
  bad=$(python3 - "$GTK" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
# Walk the text and require that every block closes on a declaration: the last
# significant character before a } must be ; or {. Catches a missing semicolon
# anywhere, single-line blocks included, which a line-based rule cannot.
problems = []
depth = 0
last = ""
for ch in src:
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth < 0:
            problems.append("closing brace with no open block")
            depth = 0
        elif last not in (";", "{", "}"):
            problems.append("block closes on a declaration without ;")
    if not ch.isspace():
        last = ch
if depth != 0:
    problems.append("unclosed block")
if not problems:
    # a rule with no selector at all is a GTK parse error too
    if re.search(r"\{\s*\}", re.sub(r"[^{}]+\{[^{}]*\}", "", src)) is not None:
        problems.append("empty selector")
print(" ".join(problems[:3]))
PY
)
  if [ -z "$bad" ]; then
    ok "gtk: every declaration terminates and every block closes"
  else
    no "gtk" "$bad"
  fi
  if grep -qi 'ubuntu\|xubuntu' "$GTK"; then
    no "gtk" "brand string present"
  else
    ok "gtk: no ubuntu/xubuntu string"
  fi
else
  no "gtk" "gtk/gtk.css missing (apply.sh preflight would refuse the theme)"
fi

# ---- 4. xfwm4/themerc contracts
XM="$THEME/xfwm4/themerc"
if [ -f "$XM" ]; then
  if grep -q '^button_layout=O|SHMC$' "$XM"; then
    ok "xfwm4: only the menu button on the left, three on the right"
  else
    no "xfwm4" "button_layout is not O|SHMC"
  fi
  miss=""
  for k in active_color_1 active_hilight_1 inactive_text_color title_alignment; do
    grep -q "^$k=" "$XM" || miss="$miss $k"
  done
  [ -z "$miss" ] && ok "xfwm4: every key xfwm4 requires is present" || no "xfwm4" "missing:$miss"
  grep -qi 'ubuntu' "$XM" && no "xfwm4" "brand string present" || ok "xfwm4: no ubuntu string"
else
  no "xfwm4" "xfwm4/themerc missing"
fi

# ---- 5. plank dock.theme contracts
DK="$THEME/dock/dock.theme"
if [ -f "$DK" ]; then
  bad=$(python3 - "$DK" <<'PY'
import sys
vals = {}
for line in open(sys.argv[1]):
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
problems = []
if "[PlankTheme]" not in open(sys.argv[1]).read():
    problems.append("no [PlankTheme] header")
for key in ("TopColor", "LineColor", "UrgentDotColor"):
    v = vals.get(key)
    if v is None:
        problems.append("missing " + key)
        continue
    parts = v.split(";;")
    if len(parts) != 4:
        problems.append(key + " not r;;g;;b;;a (" + v + ")")
        continue
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        problems.append(key + " has a non-integer channel")
        continue
    if any(n < 0 or n > 255 for n in nums):
        problems.append(key + " channel outside 0..255")
# 0.72 alpha over 255 channels: plank truncates, so accept 183..184 but nothing wider
alpha = int(vals.get("TopColor", "0;;0;;0;;0").split(";;")[3] or 0)
if alpha not in (183, 184):
    problems.append("dock alpha %d is not 0.72*255" % alpha)
print(" ".join(problems[:3]))
PY
)
  if [ -z "$bad" ]; then
    ok "plank: colours are r;;g;;b;;a in range, alpha matches the 0.72 token"
  else
    no "plank" "$bad"
  fi
  grep -qi 'ubuntu' "$DK" && no "plank" "brand string present" || ok "plank: no ubuntu string"
else
  no "plank" "dock/dock.theme missing"
fi

# ---- 6. panel xml contracts
PN="$THEME/panel/xfce4-panel.xml"
if [ -f "$PN" ]; then
  bad=$(python3 - "$PN" <<'PY'
import sys, xml.dom.minidom
path = sys.argv[1]
try:
    doc = xml.dom.minidom.parse(path)
except Exception as exc:
    print("not valid XML: %s" % exc)
    raise SystemExit(0)
problems = []
src = open(path).read()
if 'value="30"' not in src:
    problems.append("panel size is not 30 px")
if not src.count('<value type="int" value="6"/>') >= 1:
    problems.append("plugin id 6 not in the id list")
for plug in ("applicationsmenu", "tasklist", "clock", "systray"):
    if plug not in src:
        problems.append("no %s plugin" % plug)
if src.count('value="separator"') != 2:
    problems.append("clock is not centred between two separators")
# every plugin id in the panel must exist in the plugins block
ids = []
for prop in doc.getElementsByTagName("property"):
    if prop.getAttribute("name") == "plugin-ids":
        for v in prop.getElementsByTagName("value"):
            ids.append(v.getAttribute("value"))
declared = [p.getAttribute("name") for p in doc.getElementsByTagName("property")
            if p.getAttribute("name").startswith("plugin-") and p.getAttribute("type") != "empty"]
missing = [i for i in ids if ("plugin-" + i) not in declared]
if missing:
    problems.append("ids with no plugin: " + ",".join(missing))
print(" ".join(problems[:3]))
PY
)
  if [ -z "$bad" ]; then
    ok "panel: valid XML, 30 px, six plugins, clock centred"
  else
    no "panel" "$bad"
  fi
  grep -qi 'ubuntu' "$PN" && no "panel" "brand string present" || ok "panel: no ubuntu string"
else
  no "panel" "panel/xfce4-panel.xml missing"
fi

echo "----"
echo "tokens: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
