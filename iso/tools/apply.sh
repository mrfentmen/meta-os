#!/usr/bin/env bash
# iso/tools/apply.sh — install the MetaOS ISO lane into a target root.
#
# This copies files. It does not build an ISO, run Calamares, or boot
# anything. Point --root at a Cubic chroot, or at a staging directory when
# you only want to inspect the tree it would produce.
#
#   iso/tools/apply.sh --root DIR [--user NAME] [--dry-run]
#
# Every source is required. A missing one is reported by name and the run
# exits 1, because a half-applied base is worse than an untouched one.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="$(cd "$HERE/.." && pwd)"

ROOT=""
USER_NAME="meta"
DRY=0
copied=0
planned=0
fail=0

usage() {
  cat <<'USAGE'
usage: iso/tools/apply.sh --root DIR [--user NAME] [--dry-run]

  --root DIR    target root (a Cubic chroot or a staging directory)
  --user NAME   user that receives the Plank dock items (default: meta)
  --dry-run     print what would be installed, write nothing
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --root)    ROOT="${2:-}"; shift 2 ;;
    --user)    USER_NAME="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "apply: unknown argument $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$ROOT" ]; then
  echo "apply: --root is required" >&2
  usage >&2
  exit 2
fi

# Strip a trailing slash so "/" becomes empty and is refused below.
ROOT="${ROOT%/}"
if [ -z "$ROOT" ]; then
  echo "apply: refusing to write to the filesystem root" >&2
  exit 2
fi
if [ ! -d "$ROOT" ]; then
  echo "apply: not a directory: $ROOT" >&2
  exit 2
fi
if [ -z "$USER_NAME" ]; then
  echo "apply: --user cannot be empty" >&2
  exit 2
fi

put() {
  local src="$1" dst="$2" mode="${3:-644}"
  if [ ! -f "$src" ]; then
    echo "MISSING  $src" >&2
    fail=$((fail + 1))
    return
  fi
  if [ "$DRY" = "1" ]; then
    echo "would install  $dst"
    planned=$((planned + 1))
    return
  fi
  mkdir -p "$(dirname "$ROOT$dst")"
  if install -m "$mode" "$src" "$ROOT$dst"; then
    copied=$((copied + 1))
  else
    echo "FAILED   $dst" >&2
    fail=$((fail + 1))
  fi
}

echo "apply: root $ROOT, user $USER_NAME"

for f in "$ISO"/plymouth/metaos/*; do
  put "$f" "/usr/share/plymouth/themes/metaos/$(basename "$f")"
done

put "$ISO/calamares/settings.conf" "/etc/calamares/settings.conf"
for f in "$ISO"/calamares/branding/meta/*; do
  put "$f" "/etc/calamares/branding/meta/$(basename "$f")"
done
for f in "$ISO"/calamares/modules/*.conf; do
  put "$f" "/etc/calamares/modules/$(basename "$f")"
done

for f in "$ISO"/apps/desktop/*.desktop; do
  put "$f" "/usr/share/applications/$(basename "$f")"
done
for f in "$ISO"/apps/plank/*.dockitem; do
  put "$f" "/home/$USER_NAME/.config/plank/dock1/launchers/$(basename "$f")"
done

put "$ISO/apps/agent-status/meta-agent-status.py" "/usr/local/bin/meta-agent-status" 755
put "$ISO/apps/chromium/meta-start.html" "/usr/share/metaos/start/meta-start.html"
put "$ISO/apps/chromium/tokens.css" "/usr/share/metaos/start/tokens.css"
put "$ISO/apps/chromium/policies.json" "/etc/chromium/policies/managed/metaos.json"

put "$ISO/theme/wallpaper/meta-wallpaper.png" "/usr/share/metaos/theme/meta-wallpaper.png"
put "$ISO/theme/gtk/metaos.css" "/usr/share/metaos/theme/gtk.css"
put "$ISO/theme/xfce4-desktop.xml" "/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"

if [ "$DRY" = "1" ]; then
  echo "apply: dry run, $planned file(s) planned, $fail missing"
else
  echo "apply: $copied file(s) installed, $fail missing"
fi

[ "$fail" -eq 0 ] || exit 1
exit 0
