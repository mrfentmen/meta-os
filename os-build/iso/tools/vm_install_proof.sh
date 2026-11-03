#!/bin/bash
# MetaOS 1.0 -- VM install proof harness (boot + installer lane).
#
# Produces the artifact the 12-hour plan asks for: screendumps from a real
# QEMU run, one per stage, plus the serial log and an INDEX.md that says what
# each frame is supposed to show.
#
# Two modes:
#   --dry                 no ISO needed: boots empty firmware and takes one
#                         screendump. Proves the QMP + framebuffer plumbing.
#   --iso <file.iso>      fresh disk, boot the ISO, snapshot the stages, then
#                         (--reboot) boot the installed disk and snapshot the
#                         login screen.
#
# Calamares cannot be driven headlessly (no unattended mode), so the install
# itself is a walkthrough: this harness snapshots every stage and can inject
# a key sequence (--keys ret,ret,...). Add --vnc to attach and click by hand;
# the screendumps are the proof either way.
#
# Claim label: --dry is runnable on this Mac; --iso is UNRUN until a Linux
# host (or an Intel Mac with an ISO) runs it.
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
PROOF="$HERE/../proof/$STAMP"
ISO=""
DRY=0
KEYS=""
REBOOT=0
VNC=0
WAIT_SPLASH=${WAIT_SPLASH:-25}
WAIT_DESKTOP=${WAIT_DESKTOP:-150}
WAIT_INSTALLER=${WAIT_INSTALLER:-75}
WAIT_KEY=${WAIT_KEY:-6}
WAIT_LOGIN=${WAIT_LOGIN:-90}
DISK_SIZE=${DISK_SIZE:-24G}

say() { printf 'proof: %s\n' "$*"; }
die() { printf 'proof: ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --dry) DRY=1 ;;
        --iso) ISO=${2:-}; shift || true ;;
        --keys) KEYS=${2:-}; shift || true ;;
        --reboot) REBOOT=1 ;;
        --vnc) VNC=1 ;;
        --work) PROOF=${2:-}; shift || true ;;
        -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
    shift
done

have qemu-system-x86_64 || die "qemu-system-x86_64 not installed"
have qemu-img || die "qemu-img not installed"
have python3 || die "python3 not installed"
[ "$DRY" = "1" ] || [ -n "$ISO" ] || die "give --iso <file.iso> or --dry"
[ "$DRY" = "1" ] || [ -f "$ISO" ] || die "ISO not found: $ISO"

mkdir -p "$PROOF"
SOCK="$PROOF/qmp.sock"
PIDFILE="$PROOF/qemu.pid"
rm -f "$SOCK" "$PIDFILE"

# One accelerator decision, stated in the log: KVM where the kernel gives it,
# TCG everywhere else (including Apple silicon, which cannot HVF an x86 guest).
ACCEL_ARGS=(-accel "tcg,thread=multi" -cpu max)
if [ -e /dev/kvm ] && [ -w /dev/kvm ]; then
    ACCEL_ARGS=(-enable-kvm -cpu max)
fi
START_EPOCH=$(date +%s)
say "accel: ${ACCEL_ARGS[*]}"
say "clock starts here; every frame is stamped T+seconds from this line"

qmp() { python3 "$HERE/qmp.py" --socket "$SOCK" "$@"; }

cleanup() {
    if [ -f "$PIDFILE" ]; then
        local pid
        pid=$(cat "$PIDFILE" 2>/dev/null || true)
        if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi
}
trap cleanup EXIT

wait_for_socket() {
    for _ in $(seq 1 120); do
        [ -S "$SOCK" ] && return 0
        sleep 0.25
    done
    return 1
}

shot() {  # shot <name> <label>
    qmp screendump "$PROOF/$1.png" >/dev/null
    local elapsed=$(( $(date +%s) - START_EPOCH ))
    printf '| %s.png | T+%ss | %s |\n' "$1" "$elapsed" "$2" >> "$PROOF/INDEX.md"
    say "captured $1 at T+${elapsed}s — $2"
}

start_vm() {  # start_vm <boot-order> <with-cdrom 0|1>
    local boot=$1 with_cdrom=$2
    local args=(
        -machine q35 -m 4096 -smp 2 "${ACCEL_ARGS[@]}"
        -display none -vga std
        -qmp "unix:$SOCK,server=on,wait=off"
        -serial "file:$PROOF/serial.log"
        -pidfile "$PIDFILE"
        -daemonize
    )
    if [ "$with_cdrom" = "1" ]; then
        args+=(-drive "file=$PROOF/disk.qcow2,if=virtio,format=qcow2" -cdrom "$ISO" -boot "order=$boot,menu=off")
    elif [ -f "$PROOF/disk.qcow2" ]; then
        args+=(-drive "file=$PROOF/disk.qcow2,if=virtio,format=qcow2" -boot "order=$boot,menu=off")
    else
        args+=(-nodefaults -boot "order=n")
    fi
    if [ "$VNC" = "1" ]; then
        args+=(-vnc 127.0.0.1:7)
    fi
    qemu-system-x86_64 "${args[@]}"
    wait_for_socket || die "QMP socket never appeared; see $PROOF"
}

cat > "$PROOF/INDEX.md" <<HEADER
# MetaOS 1.0 install proof — $STAMP

Mode: $( [ "$DRY" = "1" ] && echo "DRY (harness plumbing, not an install)" || echo "ISO install walkthrough" )
Host: $(uname -s) $(uname -m), qemu $(qemu-system-x86_64 --version | head -1 | awk '{print $4}')
ISO: ${ISO:-none}
Accel: ${ACCEL_ARGS[*]}

Every frame below is QEMU's framebuffer via QMP screendump — a real VM,
not a mock. Interpret them in order; a stage with no frame did not happen.

The at column is wall-clock T+seconds from harness start, including QEMU
launch. Under TCG it is an upper bound on boot time, not hardware speed;
say so if you quote it. The H+2 box asks for "login under 60s" — only a
frame whose stage is the login screen and whose at value is under 60
answers it. (No backticks in this block: the heredoc is unquoted so the
shell would execute them; that bug mangled the first INDEX.md.)

| frame | at | expected |
|---|---|---|
HEADER

if [ "$DRY" = "1" ]; then
    say "dry run: booting firmware with no disk (plumbing test only)"
    start_vm n 0
    qmp wait 4000 >/dev/null
    shot "00-harness-dry" "DRY: firmware screen; proves QMP screendump works, not a Meta boot"
    qmp quit >/dev/null || true
    say "dry proof written to $PROOF"
    exit 0
fi

say "creating fresh target disk ($DISK_SIZE)"
qemu-img create -f qcow2 "$PROOF/disk.qcow2" "$DISK_SIZE" >/dev/null

say "booting ISO (stage 1/2: splash in ${WAIT_SPLASH}s)"
start_vm d 1
qmp wait $((WAIT_SPLASH * 1000)) >/dev/null
shot "01-splash" "Meta splash: ring mark + block wordmark on ink, 12-dot progress ring"

say "waiting ${WAIT_DESKTOP}s for the live desktop (TCG is slow; this is not a hang)"
qmp wait $((WAIT_DESKTOP * 1000)) >/dev/null
shot "02-live-desktop" "live session desktop; installer autostarts 8s after login"

say "waiting ${WAIT_INSTALLER}s for the installer window"
qmp wait $((WAIT_INSTALLER * 1000)) >/dev/null
shot "03-installer-welcome" "Calamares welcome, Meta branding, no dead support links"

if [ -n "$KEYS" ]; then
    n=0
    IFS=',' read -r -a seq <<< "$KEYS"
    for key in "${seq[@]}"; do
        n=$((n + 1))
        key=$(printf '%s' "$key" | tr -d ' ')
        [ -n "$key" ] || continue
        say "key $n: $key"
        qmp key "$key" >/dev/null
        qmp wait $((WAIT_KEY * 1000)) >/dev/null
        shot "$(printf '04-key-%02d-%s' "$n" "$key")" "after key '$key' (walkthrough step $n)"
    done
    say "walkthrough keys done. If the operator had to type anything (the user"
    say "password is NOT preseedable), attach with --vnc and re-run that stage."
else
    say "no --keys given: stopping at the installer welcome frame."
    say "attach with --vnc 127.0.0.1:7 to drive the walkthrough by hand."
fi

if [ "$REBOOT" = "1" ]; then
    say "stage 2/2: quitting live VM, booting the installed disk"
    qmp quit >/dev/null || true
    sleep 3
    rm -f "$SOCK" "$PIDFILE"
    start_vm c 0
    say "waiting ${WAIT_LOGIN}s for the login screen"
    qmp wait $((WAIT_LOGIN * 1000)) >/dev/null
    shot "05-installed-login" "installed system: Meta splash, then LightDM login (no autologin)"
    qmp quit >/dev/null || true
fi

say "proof written to $PROOF"
say "claim rule: only frames in this directory count as install evidence."
