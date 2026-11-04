#!/bin/sh
# qemu_guard.sh — one no-boot guard for every tool that can start QEMU.
#
# Source it, then call qemu_guard "<tool-name>" before the first QEMU launch:
#
#   . "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/qemu_guard.sh"
#   qemu_guard "show_os.sh"
#
# The flag is read from the exported environment ONLY (via printenv, never a
# shell variable, CLI flag, or file). A wrapper script therefore cannot allow
# a boot by setting a local variable: only METAOS_ALLOW_QEMU=1 present in the
# guarded process's environment allows it. The documented allow path is:
#
#   METAOS_ALLOW_QEMU=1 sh os-build/tools/show_os.sh
#
# Refusal names the tool and the flag and exits 2. Fail-closed: if printenv is
# missing, or the value is anything but exactly "1", the tool refuses.
# POSIX sh only (no bashisms, no `local`); safe under `set -eu`.
qemu_guard() {
  _qemu_tool=${1:-this tool}
  _qemu_allow=
  if command -v printenv >/dev/null 2>&1; then
    _qemu_allow=$(printenv METAOS_ALLOW_QEMU 2>/dev/null || true)
  fi
  if [ "$_qemu_allow" = "1" ]; then
    unset _qemu_tool _qemu_allow
    return 0
  fi
  echo "refused: ${_qemu_tool} boots QEMU. set METAOS_ALLOW_QEMU=1 to allow it." >&2
  exit 2
}
