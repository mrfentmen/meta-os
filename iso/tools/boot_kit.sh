#!/usr/bin/env bash
# iso/tools/boot_kit.sh — build the boot image on a machine that has the tools.
#
#   boot_kit.sh --check          report every prerequisite, exit 1 if any is missing
#   boot_kit.sh --build [--out DIR]
#
# --check exists because the boot machine may not have the same toolchain as
# the machine the code was written on. It names what is missing instead of
# failing three steps later with a compiler error.
#
# --build runs four real commands and stops at the first failure:
#   1. userspace    (kernel/build.rs embeds these; without them the kernel
#                    build panics with the exact path it wanted)
#   2. kernel ELF   (cargo +nightly build --target x86_64-unknown-none)
#   3. builder      (cargo +nightly build, in rk007-builder)
#   4. disk image   (rk007-builder <elf> <image>)
# It does not boot anything. The QEMU command is printed at the end.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT_DIR="${TMPDIR:-/tmp}"
BUILDER_DIR="${RK007_BUILDER:-}"

usage() {
  cat <<'USAGE'
usage: iso/tools/boot_kit.sh --check
       iso/tools/boot_kit.sh --build [--out DIR] [--builder DIR]

  --check      report rustup, nightly, rust-src, llvm-tools-preview, qemu
  --build      build userspace, kernel, builder and image; print the QEMU line
  --out DIR    where the image goes (default: $TMPDIR)
  --builder    rk007-builder directory (default: os-build/layer1/rk007-builder)
USAGE
}

MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE="check"; shift ;;
    --build) MODE="build"; shift ;;
    --out)   OUT_DIR="${2:-}"; shift 2 ;;
    --builder) BUILDER_DIR="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "boot_kit: unknown argument $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$MODE" ] || { usage >&2; exit 2; }
[ -n "$OUT_DIR" ] && [ -d "$OUT_DIR" ] || { echo "boot_kit: --out is not a directory: $OUT_DIR" >&2; exit 2; }

missing=0
say() {
  local state="$1" name="$2" note="${3:-}"
  printf '%-8s %-26s %s\n' "$state" "$name" "$note"
}

check() {
  # check <label> <command...> — present, or counted missing
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    say OK "$label"
  else
    say MISSING "$label"
    missing=$((missing + 1))
  fi
}

run_checks() {
  echo "boot_kit: prerequisites on $(uname -s) $(uname -m)"
  check "rustup" rustup --version
  check "cargo" cargo --version
  check "nightly toolchain" rustup run nightly rustc --version
  check "rust-src" rustup component list --toolchain nightly
  check "llvm-tools-preview" bash -c 'rustup component list --toolchain nightly --installed | grep -q llvm-tools'
  check "qemu-system-x86_64" qemu-system-x86_64 --version
  check "python3" python3 --version

  if [ "$missing" -ne 0 ]; then
    echo
    echo "boot_kit: $missing prerequisite(s) missing."
    echo "  rustup component add rust-src llvm-tools-preview --toolchain nightly"
    echo "  qemu: install it from your package manager; it is not vendored here"
    return 1
  fi
  echo
  echo "boot_kit: all prerequisites present"
  return 0
}

if [ "$MODE" = "check" ]; then
  run_checks
  exit $?
fi

run_checks || exit 1

KERNEL_DIR="$ROOT/kernel"
[ -n "$BUILDER_DIR" ] || BUILDER_DIR="$ROOT/os-build/layer1/rk007-builder"
IMAGE="$OUT_DIR/metaos-rk007.img"

USER_DIR="$ROOT/os-build/userspace/user"

echo
echo "== 1/4 userspace binaries"
if ! (cd "$USER_DIR" && cargo build --target x86_64-unknown-none --bins); then
  echo "boot_kit: userspace build failed" >&2
  exit 1
fi
for bin in hello sleeper crasher; do
  if [ ! -f "$USER_DIR/target/x86_64-unknown-none/debug/$bin" ]; then
    echo "boot_kit: userspace binary missing after build: $bin" >&2
    exit 1
  fi
done
say OK "userspace binaries" "hello, sleeper, crasher"

echo
echo "== 2/4 kernel ELF"
if ! (cd "$KERNEL_DIR" && cargo +nightly build --target x86_64-unknown-none); then
  echo "boot_kit: kernel build failed" >&2
  exit 1
fi
ELF="$KERNEL_DIR/target/x86_64-unknown-none/debug/metaos-kernel"
if [ ! -f "$ELF" ]; then
  echo "boot_kit: kernel ELF not found at $ELF" >&2
  exit 1
fi
say OK "kernel ELF" "$(wc -c < "$ELF" | tr -d ' ') bytes"

echo
echo "== 3/4 image builder"
if [ ! -d "$BUILDER_DIR" ]; then
  echo "boot_kit: builder not found at $BUILDER_DIR" >&2
  echo "  it lives on branch bond/rk007 at os-build/layer1/rk007-builder." >&2
  echo "  merge that branch, or clone it and pass --builder DIR." >&2
  exit 1
fi
if ! (cd "$BUILDER_DIR" && cargo +nightly build); then
  echo "boot_kit: builder build failed" >&2
  exit 1
fi
say OK "builder" "$BUILDER_DIR/target/debug/rk007-builder"

echo
echo "== 4/4 disk image"
if ! "$BUILDER_DIR/target/debug/rk007-builder" "$ELF" "$IMAGE"; then
  echo "boot_kit: image build failed" >&2
  exit 1
fi
say OK "image" "$IMAGE ($(wc -c < "$IMAGE" | tr -d ' ') bytes)"

echo
echo "boot it with:"
echo "  qemu-system-x86_64 -drive format=raw,file=$IMAGE -serial file:$OUT_DIR/boot.txt \\"
echo "    -display none -no-reboot -m 512M"
echo
echo "then judge it with:"
echo "  python3 $ROOT/iso/tools/boot_log_verdict.py $OUT_DIR/boot.txt"
