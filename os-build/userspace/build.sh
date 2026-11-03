#!/bin/bash
# MetaOS userspace build pipeline — one link base per program.
#
# Cargo cannot give per-bin linker arguments in one invocation, so this loops:
# each program is a separate cargo build with its own RUSTFLAGS and
# `--defsym=__base`, then verify_bases.py reads the produced ELF headers and
# refuses an overlap. A single `cargo build --bins` links every program at the
# same address, which the kernel loader then refuses at boot ("address in use").
#
# Usage:
#   os-build/userspace/build.sh                 # every bin in bases.txt
#   os-build/userspace/build.sh hello sleeper   # named bins only
#   PROFILE=debug os-build/userspace/build.sh   # default is release
#
# Runs on macOS or Linux; needs the x86_64-unknown-none target installed
# (`rustup target add x86_64-unknown-none`).
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
USER_DIR="$HERE/user"
BASES="$HERE/bases.txt"
PROFILE=${PROFILE:-release}
TARGET=x86_64-unknown-none
RUSTUP_HOME=${RUSTUP_HOME:-$HOME/.rustup}
CARGO=${CARGO:-cargo}

say()  { printf 'ubuild: %s\n' "$*"; }
die()  { printf 'ubuild: ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

[ -f "$BASES" ] || die "missing $BASES"

# rustc needs the precompiled core for this target unless build-std is used.
# Homebrew's rustc shadows rustup on this Mac and has no core for
# x86_64-unknown-none; rustup's toolchain does. Probe instead of guessing.
toolchain_has_core() {  # toolchain_has_core <rustc-command...>
    local libdir
    libdir=$("$@" --print target-libdir --target "$TARGET" 2>/dev/null) || return 1
    ls "$libdir"/libcore-*.rlib >/dev/null 2>&1
}

if command -v rustup >/dev/null 2>&1 \
    && ! rustup target list --installed 2>/dev/null | grep -qx "$TARGET"; then
    die "target $TARGET not installed: rustup target add $TARGET"
fi

CARGO_CMD=()
if have "$CARGO" && toolchain_has_core "$(command -v rustc)"; then
    CARGO_CMD=("$CARGO")
    say "toolchain: PATH cargo ($(rustc -V | awk '{print $2}'))"
elif command -v rustup >/dev/null 2>&1 && toolchain_has_core rustup run stable rustc; then
    # `rustup run stable cargo` alone is NOT enough: cargo resolves `rustc`
    # from PATH, which is the Homebrew one without core for this target.
    # Point RUSTC at the toolchain's own rustc as well.
    TC_BIN=$(dirname "$(rustup which --toolchain stable rustc)")
    CARGO_CMD=("$TC_BIN/cargo")
    export RUSTC="$TC_BIN/rustc"
    say "toolchain: rustup stable ($TC_BIN, RUSTC pinned)"
elif toolchain_has_core "$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc"; then
    TC="$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin"
    CARGO_CMD=("$TC/cargo")
    export RUSTC="$TC/rustc"
    say "toolchain: $TC"
else
    die "no toolchain on this machine has core for $TARGET; run: rustup target add $TARGET"
fi

if [ $# -gt 0 ]; then
    bins=("$@")
else
    # No mapfile: macOS ships bash 3.2, and this script must run there.
    bins=()
    while IFS= read -r b; do bins+=("$b"); done \
        < <(awk '!/^[[:space:]]*#/ && NF >= 2 {print $1}' "$BASES")
fi
[ "${#bins[@]}" -gt 0 ] || die "bases.txt lists no programs"

base_of() {
    awk -v b="$1" '!/^[[:space:]]*#/ && NF >= 2 && $1 == b {print $2; exit}' "$BASES"
}

# A plain variable, not an array: bash 3.2 (macOS) treats an empty
# "${arr[@]}" as an unbound variable under set -u, which broke the debug
# build the first time. Unquoted expansion below is deliberate.
PROFILE_ARG=""
[ "$PROFILE" = "release" ] && PROFILE_ARG="--release"
out_dir="$USER_DIR/target/$TARGET/$PROFILE"

for bin in "${bins[@]}"; do
    base=$(base_of "$bin")
    [ -n "$base" ] || die "no base for '$bin' in bases.txt (add a unique slot)"
    say "building $bin at $base"
    # All flags repeated here on purpose: RUSTFLAGS must be self-contained,
    # because cargo's target rustflags may or may not be merged depending on
    # version, and a silently dropped -T would put the program back at the
    # default base — the exact bug this script exists to prevent.
    (
        cd "$USER_DIR"
        RUSTFLAGS="-C relocation-model=static -C code-model=large -C link-arg=-no-pie -C link-arg=-T$USER_DIR/link.ld -C link-arg=--defsym=__base=$base" \
            "${CARGO_CMD[@]}" build --target "$TARGET" $PROFILE_ARG --bin "$bin"
    )
done

say "verifying ELF bases"
python3 "$HERE/verify_bases.py" --bases "$BASES" --dir "$out_dir" "${bins[@]}"
say "done: $out_dir"
