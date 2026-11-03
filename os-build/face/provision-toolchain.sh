#!/bin/bash
# os-build/face/provision-toolchain.sh — guest-side toolchain provision.
# Runs INSIDE the carrier guest as relay (passwordless sudo) during the
# image build (os-build/face/build-image.sh provision phase) or by hand
# over SSH for a live guest. Pinned versions live in the header.
#
# Pins:
OPENCODE_VERSION="${OPENCODE_VERSION:-2.2.0}"   # SST installer --version pin
FREEBUBFF_NPM="${FREEBUBFF_NPM:-freebuff@0.2.35}" # attempt only (Mac-only?)
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "provision: apt update"
sudo apt-get update
echo "provision: apt install git nodejs npm chromium"
sudo apt-get install -y git nodejs npm chromium

echo "provision: opencode $OPENCODE_VERSION (v2 installer)"
curl -fsSL https://opencode.ai/v2/install -o /tmp/oc-install.sh
bash /tmp/oc-install.sh --version "$OPENCODE_VERSION" --no-modify-path
OC_BIN="$HOME/.opencode/bin/opencode"
[ -x "$OC_BIN" ] || OC_BIN="$HOME/.local/bin/opencode"
sudo ln -sf "$OC_BIN" /usr/local/bin/opencode
command -v opencode

echo "provision: versions"
opencode --version
node --version
git --version
chromium --version

echo "provision: freebuff attempt ($FREEBUBFF_NPM)"
if sudo npm install -g "$FREEBUBFF_NPM"; then
  echo "provision: freebuff installed"
  (freebuff --version || echo "provision: freebuff binary would not run")
else
  echo "provision: FREEBUBFF_INSTALL_FAILED rc=$? (recorded, not fatal)"
fi
echo "provision: done"
