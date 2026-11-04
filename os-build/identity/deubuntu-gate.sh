#!/bin/sh
# deubuntu-gate.sh — fail if stock-distro strings appear in anything we ship.
#
# Scans the two trees this lane owns (os-build/identity/ and
# os-build/iso/payload-theme/) for case-insensitive `ubuntu|xubuntu`.
# Every hit must match a documented allowlist entry (a legitimate
# dependency name, license name, or technical identifier — never brand
# prose) or the gate FAILS with file:line. The gate skips itself.
#
# Two tiers, because scripts and shipped content are different risks:
#   STRICT — files installed verbatim into the image (identity/*,
#     greeter confs, grub theme, splash, gtk, panel, dock, icons,
#     terminal profile, .desktop launchers). Only the font-dependency
#     allowlist applies here, plus two documented technical-identifier
#     comments (each names the exact file).
#   TOOLING — build scripts, proofs, docs (*.sh, *.md, *.py, KEYS.md).
#     Never shipped to the image; comment lines and documented removal
#     operations are allowed, everything else fails.
#
# Usage: sh os-build/identity/deubuntu-gate.sh [REPO_ROOT] (default: repo
#   root derived from this script's path). Exit 0 PASS, 1 FAIL.
set -eu

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO="${1:-$(CDPATH= cd -- "$HERE/../.." && pwd)}"
IDENT="$REPO/os-build/identity"
PAYLOAD="$REPO/os-build/iso/payload-theme"
SELF="deubuntu-gate.sh"

fail=0
say_fail() { echo "GATE-FAIL: $1"; fail=1; }

# --- allowlist reasons (printed with each allowed hit in --verbose) ---
# A1 font family / package / path: fonts-ubuntu, Ubuntu Mono, truetype/ubuntu
# A2 license name: Ubuntu Font Licence 1.0
# A3 gtk font fallback stack: font-family 'Ubuntu' (generic fallback, not branding)
# A4 stock-account technical identifier in 10-metaos-live.conf header comment
#    (names the base account rename_user.sh removes; prose, not brand)
# A5 tooling comments + removal operations (*.sh/*.md/*.py/KEYS.md only):
#    shell/xml comments, s/Ubuntu|/Xubuntu|/ removal seds, grep patterns,
#    OLD=ubuntu assignment, ubuntu* globs, /home/ubuntu fixup paths,
#    design.ubuntu.com URL (font upstream), lightdm-gtk-greeter upstream ref
# A6 absence-claim messages in proofs/docs ("no ubuntu…", "full name Ubuntu",
#    "no Apple/Ubuntu/Xubuntu marks") — the gate's own vocabulary

is_fontdep() {
  case "$1" in
    *fonts-ubuntu*|*Ubuntu\ Mono*|*UbuntuMono*|*truetype/ubuntu*|*Ubuntu\ Font\ Licence*|*font-family:*Ubuntu*) return 0 ;;
  esac
  return 1
}

is_tooling_allowed() {
  line="$1"
  case "$line" in
    *\#*|*\<!--*) return 0 ;;            # comment lines
    *s/Xubuntu/Meta\ OS/g*|*s/Ubuntu/Meta\ OS/g*) return 0 ;;  # the removal itself
    *OLD=ubuntu*|*ubuntu\**|*/home/ubuntu*|*USERNAME*|*grep*ubuntu*|*say*ubuntu*) return 0 ;; # identifiers/patterns/messages
    *design.ubuntu.com*|*Xubuntu/lightdm-gtk-greeter*|*\'ubuntu\'*|*\`ubuntu\`*) return 0 ;; # upstream refs / quoted identifier
    *Inter*Ubuntu*|*Ubuntu*Inter*) return 0 ;;      # font-stack prose in docs
    *no\ ubuntu*|*no\ Ubuntu*|*full\ name\ Ubuntu*|*no\ Apple/Ubuntu*) return 0 ;; # A6 absence-claim messages in proofs/docs
  esac
  return 1
}

scan_strict() {
  # $1 = file, $2+ = extra allowed exact-substring (file-scoped A4)
  f="$1"; extra="$2"
  grep -in -I 'ubuntu\|xubuntu' "$f" 2>/dev/null | while IFS= read -r hit; do
    body=$(printf '%s' "$hit" | sed 's/^[0-9]*://')
    if is_fontdep "$body"; then continue; fi
    case "$body" in *"$extra"*) [ -n "$extra" ] && continue ;; esac
    echo "GATE-FAIL: STRICT $f: $hit"
  done
}

# --- collect text files (skip binaries, skip self) ---
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
found_fail=0

check_file() {
  f="$1"
  case "$f" in *"$SELF") return 0 ;; esac
  rel=${f#"$REPO"/}
  case "$f" in
    *.sh|*.md|*.py|*KEYS.md|*INSTALL.md)
      # TOOLING tier (build scripts, proofs, docs — never shipped to the image).
      grep -in -I 'ubuntu\|xubuntu' "$f" 2>/dev/null | while IFS= read -r hit; do
        body=$(printf '%s' "$hit" | sed 's/^[0-9]*://')
        if is_fontdep "$body" || is_tooling_allowed "$body"; then continue; fi
        echo "GATE-FAIL: TOOLING $f: $hit"
      done | { grep . && found_fail=1 || true; }
      ;;
    *)
      case "$rel" in
        os-build/identity/*|os-build/iso/payload-theme/identity/*|\
os-build/iso/payload-theme/greeter/*.conf|\
os-build/iso/payload-theme/grub/theme.txt|\
os-build/iso/payload-theme/splash/metaos.plymouth|\
os-build/iso/payload-theme/splash/metaos.script|\
os-build/iso/payload-theme/gtk/*|os-build/iso/payload-theme/xfwm4/*|\
os-build/iso/payload-theme/panel/*|os-build/iso/payload-theme/dock/*|\
os-build/iso/payload-theme/icons/*|\
os-build/iso/payload-theme/terminal/*|\
os-build/iso/payload-theme/apps/*.desktop)
          # STRICT tier (installed verbatim into the image).
          # A4 file-scoped allowance: backtick-quoted stock-account
          # identifier in the 10-metaos-live.conf header comment.
          extra=""
          case "$rel" in *10-metaos-live.conf) extra="\`ubuntu\`" ;; esac
          out=$(scan_strict "$f" "$extra")
          [ -n "$out" ] && { echo "$out"; found_fail=1; }
          ;;
      esac
      ;;
  esac
}

# enumerate (portable: no mapfile)
find "$IDENT" "$PAYLOAD" -type f ! -name "$SELF" 2>/dev/null | sort | while IFS= read -r f; do
  # binary sniff: skip files grep -I would skip, cheaply
  if grep -Iq . "$f" 2>/dev/null; then
    check_file "$f"
  fi
done > "$tmp" 2>&1 || true
# NOTE: found_fail is set inside a subshell pipeline above; recompute: any
# GATE-FAIL line in the captured output means failure.
cat "$tmp"
if grep -q 'GATE-FAIL' "$tmp"; then
  echo "deubuntu-gate: FAIL"
  exit 1
fi
echo "deubuntu-gate: PASS (allowlist: A1 font dep, A2 licence, A3 gtk fallback, A4 stock-account comment, A5 tooling comments/removal ops)"
