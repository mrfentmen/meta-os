#!/usr/bin/env bash
# iso/tools/apply.sh — install the MetaOS ISO lane into a target root.
#
# This copies files. It does not build an ISO, run Calamares, or boot
# anything. Point --root at a Cubic chroot, or at a staging directory when
# you only want to inspect the tree it would produce.
#
#   iso/tools/apply.sh --root DIR [--dry-run] [--verify] [--revert]
#
# Every source is required. A missing one is reported by name and the run
# exits 1, because a half-applied base is worse than an untouched one.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="$(cd "$HERE/.." && pwd)"

ROOT=""
DRY=0
VERIFY=0
REVERT=0
copied=0
planned=0
fail=0

usage() {
  cat <<'USAGE'
usage: iso/tools/apply.sh --root DIR [--dry-run] [--verify] [--revert]

  --root DIR    target root (a Cubic chroot or a staging directory)
  --dry-run     print what would be installed, write nothing
  --verify      run meta-doctor against the root after installing
  --revert      remove exactly the files the last install recorded
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --root)    ROOT="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --verify)  VERIFY=1; shift ;;
    --revert)  REVERT=1; shift ;;
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
MANIFEST="$ROOT/var/lib/metaos/apply-manifest.txt"

# Revert removes what the last run recorded and nothing else. A guessed list
# would sooner or later delete a file the base image owns.
if [ "$REVERT" = "1" ]; then
  if [ ! -f "$MANIFEST" ]; then
    echo "apply: no manifest at $MANIFEST, nothing to revert"
    exit 0
  fi
  removed=0
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    if [ -f "$ROOT$rel" ] || [ -L "$ROOT$rel" ]; then
      rm -f "$ROOT$rel" && removed=$((removed + 1))
    fi
  done < "$MANIFEST"
  rm -f "$MANIFEST"
  # Only our own tree: nothing else is pruned, because empty directories
  # elsewhere belong to the base image.
  find "$ROOT/usr/share/metaos" -type d -empty -delete 2>/dev/null || true
  echo "apply: removed $removed file(s)"
  exit 0
fi

MANIFEST_TMP=""
if [ "$DRY" != "1" ]; then
  MANIFEST_TMP="$(mktemp "${TMPDIR:-/tmp}/metaos-apply.XXXXXX")"
  trap 'rm -f "$MANIFEST_TMP"' EXIT
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
    [ -n "$MANIFEST_TMP" ] && printf '%s\n' "$dst" >> "$MANIFEST_TMP"
  else
    echo "FAILED   $dst" >&2
    fail=$((fail + 1))
  fi
}

echo "apply: root $ROOT"

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
# Dock items go to a shared directory, never to a home guessed at install
# time: Calamares creates the account after this runs, with a name the user
# types. meta-first-login copies them into the real $HOME at first login.
for f in "$ISO"/apps/plank/*.dockitem; do
  put "$f" "/usr/share/metaos/dock/$(basename "$f")"
done

put "$ISO/apps/agent-status/meta-agent-status.py" "/usr/local/bin/meta-agent-status" 755
put "$ISO/apps/chromium/meta-start.html" "/usr/share/metaos/start/meta-start.html"
put "$ISO/apps/chromium/tokens.css" "/usr/share/metaos/start/tokens.css"
put "$ISO/apps/chromium/policies.json" "/etc/chromium/policies/managed/metaos.json"

put "$ISO/theme/wallpaper/meta-wallpaper.png" "/usr/share/metaos/theme/meta-wallpaper.png"
put "$ISO/theme/wallpaper/meta-wallpaper-2560x1440.png" "/usr/share/metaos/theme/meta-wallpaper-2560x1440.png"
put "$ISO/theme/wallpaper/meta-wallpaper-1366x768.png" "/usr/share/metaos/theme/meta-wallpaper-1366x768.png"
put "$ISO/theme/wallpaper/meta-wallpaper-3840x2160.png" "/usr/share/metaos/theme/meta-wallpaper-3840x2160.png"
put "$ISO/theme/gtk/metaos.css" "/usr/share/metaos/theme/gtk.css"
put "$ISO/theme/xfce4-desktop.xml" "/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"

# First-login work: the dock, wallpaper and colours belong to whoever logs in,
# and that account does not exist until after the install.
put "$ISO/base/meta-first-login.sh" "/usr/local/bin/meta-first-login" 755
put "$ISO/base/meta-doctor.py" "/usr/local/bin/meta-doctor" 755
put "$ISO/base/autostart/meta-first-login.desktop" "/etc/xdg/autostart/meta-first-login.desktop"

# Login screen: greeter config, its backdrop, and the theme it asks for.
put "$ISO/theme/lightdm/lightdm-gtk-greeter.conf" "/etc/lightdm/lightdm-gtk-greeter.conf"
put "$ISO/theme/wallpaper/greeter-wallpaper.png" "/usr/share/metaos/theme/greeter-wallpaper.png"
put "$ISO/theme/wallpaper/greeter-wallpaper-2560x1440.png" "/usr/share/metaos/theme/greeter-wallpaper-2560x1440.png"
put "$ISO/theme/wallpaper/greeter-wallpaper-3840x2160.png" "/usr/share/metaos/theme/greeter-wallpaper-3840x2160.png"
put "$ISO/theme/wallpaper/greeter-wallpaper-1366x768.png" "/usr/share/metaos/theme/greeter-wallpaper-1366x768.png"
put "$ISO/theme/wallpaper/greeter-active.png" "/usr/share/metaos/theme/greeter-active.png"
put "$ISO/theme/lightdm/meta-greeter-setup.sh" "/usr/local/bin/meta-greeter-setup" 755
put "$ISO/theme/lightdm/lightdm.conf.d/90-metaos-greeter.conf" "/etc/lightdm/lightdm.conf.d/90-metaos-greeter.conf"
put "$ISO/theme/lightdm/themes/MetaOS/index.theme" "/usr/share/themes/MetaOS/index.theme"
put "$ISO/theme/lightdm/themes/MetaOS/gtk-3.0/gtk.css" "/usr/share/themes/MetaOS/gtk-3.0/gtk.css"

# Boot menu: the theme lives where GRUB looks, and a drop-in sets it without
# touching the base image's own /etc/default/grub.
put "$ISO/boot/grub/themes/metaos/theme.txt" "/boot/grub/themes/metaos/theme.txt"
put "$ISO/boot/grub/themes/metaos/meta-grub.png" "/boot/grub/themes/metaos/meta-grub.png"
put "$ISO/boot/grub/metaos-theme.cfg" "/etc/default/grub.d/metaos-theme.cfg"

# Desktop shell: panel, settings channels, lock, icons, fonts, terminal.
for f in "$ISO"/theme/xfce4/xfconf/xfce-perchannel-xml/*.xml; do
  put "$f" "/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/$(basename "$f")"
done
put "$ISO/theme/icons/MetaOS/index.theme" "/usr/share/icons/MetaOS/index.theme"
for f in "$ISO"/theme/icons/MetaOS/places/48/*.svg; do
  put "$f" "/usr/share/icons/MetaOS/places/48/$(basename "$f")"
done
put "$ISO/theme/fonts/local.conf" "/etc/fonts/local.conf"
put "$ISO/apps/terminal/metaos.theme" "/usr/share/xfce4/terminal/colorschemes/MetaOS.theme"
put "$ISO/apps/terminal/terminalrc" "/etc/xdg/xfce4/terminal/terminalrc"
put "$ISO/apps/welcome/meta-welcome.py" "/usr/local/bin/meta-welcome" 755
put "$ISO/apps/welcome/welcome.css" "/usr/share/metaos/welcome/welcome.css"
put "$ISO/apps/welcome/palette.json" "/usr/share/metaos/welcome/palette.json"

# Agent layer: runtime, six units, env template, login hook and the health
# cadence. One stager, so this path and provision.sh cannot drift apart.
if [ "$DRY" = "1" ]; then
  echo "would stage  agent layer (runtime, 6 units, cadence)"
else
  mkdir -p "$ROOT/etc" "$ROOT/usr"
  if sh "$ISO/../agent-layer/stage.sh" "$ROOT" >/dev/null; then
    # Record what the stager wrote, or --revert leaves 59 files behind.
    sh "$ISO/../agent-layer/stage.sh" "$ROOT" --list >> "$MANIFEST_TMP"
    echo "apply: agent layer staged"
  else
    echo "FAILED   agent layer" >&2
    fail=$((fail + 1))
  fi
fi

if [ "$DRY" = "1" ]; then
  echo "apply: dry run, $planned file(s) planned, $fail missing"
  [ "$fail" -eq 0 ] || exit 1
  exit 0
fi

mkdir -p "$(dirname "$MANIFEST")" && install -m 644 "$MANIFEST_TMP" "$MANIFEST" || fail=$((fail + 1))
echo "apply: $copied file(s) installed, $fail missing, manifest $MANIFEST"

if [ "$VERIFY" = "1" ] && [ "$fail" -eq 0 ]; then
  echo
  echo "apply: verifying the tree"
  python3 "$ISO/base/meta-doctor.py" --root "$ROOT" || fail=$((fail + 1))
fi

[ "$fail" -eq 0 ] || exit 1
exit 0
