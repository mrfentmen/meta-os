#!/bin/sh
# install-tools.sh (OS-142): provision the dev carrier from the
# manifest. Adaptation, stated: the task file assumes a Debian
# carrier image, but no OS image was ever delivered and the dev
# carrier is this Mac — so this script provisions macOS via brew.
# The Debian-image variant belongs in the image bake when a Linux
# host runs it (linux-only tools are marked, not faked here).
# Idempotent: safe to rerun; every step logs what it did.
set -eu
export PATH="$HOME/.cargo/bin:$PATH"
log() { echo "install-tools: $*"; }

have() { command -v "$1" >/dev/null 2>&1; }

if ! have brew; then
  log "Homebrew missing — install from https://brew.sh, then rerun"
  exit 1
fi

# OS-133..140, Mac-provisionable subset.
for pkg in qemu jq ripgrep ffmpeg sqlite python@3.14 node; do
  if brew list "$pkg" >/dev/null 2>&1; then
    log "present: $pkg"
  else
    log "installing: $pkg"
    brew install "$pkg" || log "FAILED (non-fatal): $pkg"
  fi
done

# Rust lives under rustup, not brew (OS-002 owns it; checked, not installed here).
if have rustup; then log "present: rustup"; else log "MISSING: rustup (see OS-002)"; fi
if have cargo; then log "present: cargo"; else log "MISSING: cargo"; fi

# Smoke list: one line per tool, version or MISSING (OS-145 input).
for t in qemu-system-x86_64 jq rg ffmpeg sqlite3 python3 node npm git curl rustc cargo bootimage; do
  if have "$t"; then
    log "smoke: $t -> $("$t" --version 2>/dev/null | head -1 || echo ok)"
  else
    log "smoke: $t MISSING"
  fi
done
log "done (linux-only tools: mformat/mtools/grub-mkstandalone — image bake only, not this host)"
