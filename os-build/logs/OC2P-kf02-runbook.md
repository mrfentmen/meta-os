# OC2P KF-02 runbook — EXACT execution-day sequence (DO NOT RUN until demo target ready + Pax call)

- Fences: NO `kernel/` edits (Rowan's pen). Scratch worktree + `/tmp` only. No commit, no push.
  Leave this file and the plan file uncommitted for parent review.
- Default target (pre-filled): `rowan/bootloader-spike @717e7ffb`. If Pax names a newer SHA,
  substitute it in Step 0 only — everything else is unchanged.
- Provenance: recipe replay of OC2P-kf01-corrected (VERDICT + boot/image/build logs).
  gate.sh verbatim is NOT used (its `cargo bootimage` + `bootimage-*.bin` path are 0.9-only;
  see plan §2 automation gap). This runbook is the 0.11 gate-equivalent.
- Timing reference: kernel alive ~4 s; `sleeper: bad call refused` is the boot-complete signal;
  gate deadline 480 s. KF-01 STATUS example: `STATUS tasks=8 ticks=5507 heap_free_kb=255`
  (ticks/heap vary — grep prefix only).

## Step 0 — scratch worktree (detached, clean check)

```sh
git -C /Users/test/meta-os-500 fetch origin rowan/bootloader-spike
git -C /Users/test/meta-os-500 worktree add --detach /tmp/oc2p-kf02-wt 717e7ffb
git -C /tmp/oc2p-kf02-wt status --short
git -C /tmp/oc2p-kf02-wt log --oneline -1
mkdir -p /tmp/oc2p-kf02 /tmp/oc2p-kf02-img
```

## Step 1 — toolchain env (record versions first)

```sh
NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
export PATH="$NIGHTLY:$PATH"
export RUSTC_BOOTSTRAP=1
FLAGS="-C relocation-model=static -C code-model=large -C link-arg=-no-pie"
cargo --version
qemu-system-x86_64 --version | head -1
rustc --version
```

## Step 2 — userspace prebuild (exact gate.sh per-pair loop, in scratch tree)

```sh
cd /tmp/oc2p-kf02-wt/os-build/userspace/user
for pair in "hello:0x600000000000" "sleeper:0x610000000000" "crasher:0x620000000000" "readkey:0x630000000000"; do
  b=${pair%%:*}; base=${pair##*:}
  sed "s/0x620000000000/$base/" link.ld > "/tmp/link-$b.ld"
  RUSTFLAGS="$FLAGS -C link-arg=-T/tmp/link-$b.ld" cargo build --target x86_64-unknown-none --bin "$b"
done
cd /tmp/oc2p-kf02-wt
```

## Step 3 — kernel (record expected bootimage fail, then branch-supported build)

```sh
(cd /tmp/oc2p-kf02-wt/kernel && cargo bootimage); echo "cargo-bootimage-exit=$?"
(cd /tmp/oc2p-kf02-wt/kernel && cargo check); echo "cargo-check-exit=$?"
(cd /tmp/oc2p-kf02-wt/kernel && cargo build --target x86_64-unknown-none); echo "cargo-build-exit=$?"
ls -l /tmp/oc2p-kf02-wt/kernel/target/x86_64-unknown-none/debug/metaos-kernel
file /tmp/oc2p-kf02-wt/kernel/target/x86_64-unknown-none/debug/metaos-kernel
```

## Step 4 — host image tool (tooling only, never committed) + image

```sh
rustup target add x86_64-unknown-uefi
cat > /tmp/oc2p-kf02-img/Cargo.toml <<'EOF'
[package]
name = "imgtool"
version = "0.1.0"
edition = "2021"

[dependencies]
bootloader = "=0.11.17"

[workspace]
EOF
mkdir -p /tmp/oc2p-kf02-img/src
cat > /tmp/oc2p-kf02-img/src/main.rs <<'EOF'
use std::path::PathBuf;
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: imgtool <kernel-elf> <out-img>");
        std::process::exit(2);
    }
    let kernel = PathBuf::from(&args[1]);
    let out = PathBuf::from(&args[2]);
    println!("imgtool: kernel={} out={}", kernel.display(), out.display());
    let boot = bootloader::BiosBoot::new(&kernel);
    match boot.create_disk_image(&out) {
        Ok(()) => println!("imgtool: IMAGE OK {}", out.display()),
        Err(e) => {
            eprintln!("imgtool: IMAGE FAIL {:?}", e);
            std::process::exit(1);
        }
    }
}
EOF
cd /tmp/oc2p-kf02-img && cargo build; echo "imgtool-build-exit=$?"
/tmp/oc2p-kf02-img/target/debug/imgtool /tmp/oc2p-kf02-wt/kernel/target/x86_64-unknown-none/debug/metaos-kernel /tmp/oc2p-kf02/metaos-bios.img; echo "imgtool-run-exit=$?"
ls -l /tmp/oc2p-kf02/metaos-bios.img
file /tmp/oc2p-kf02/metaos-bios.img
```

## Step 5 — triple boot (N = 1, 2, 3; run the whole block three times)

Per boot (replace N with 1, then 2, then 3 — all paths already absolute):

```sh
N=1
LOG=/tmp/oc2p-kf02/serial-kf02-boot$N.log; MON=/tmp/oc2p-kf02/mon-kf02-boot$N.sock
rm -f "$LOG" "$MON" /tmp/oc2p-kf02/qemu-boot$N.pid
qemu-system-x86_64 -drive format=raw,file=/tmp/oc2p-kf02/metaos-bios.img -display none -no-reboot -m 512M -serial file:$LOG -monitor unix:$MON,server,nowait &
echo $! > /tmp/oc2p-kf02/qemu-boot$N.pid
deadline=480; waited=0
while [ $waited -lt $deadline ]; do
  sleep 10; waited=$((waited+10))
  if grep -aq "sleeper: bad call refused" "$LOG" 2>/dev/null; then break; fi
done
grep -a -c "sleeper: bad call refused" "$LOG"
python3 /tmp/oc2p-kf02-wt/os-build/tools/drive.py --monitor "$MON" help status
sleep 5
python3 /tmp/oc2p-kf02-wt/os-build/tools/drive.py --monitor "$MON" ps
sleep 5
python3 -c "import socket,time; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect('$MON'); s.settimeout(2); time.sleep(0.3)
try: s.recv(65536)
except Exception: pass
s.sendall(b'screendump /tmp/oc2p-kf02/fb$N-a.ppm\n'); time.sleep(0.5)
try: s.recv(65536)
except Exception: pass"
sleep 2
python3 -c "import socket,time; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect('$MON'); s.settimeout(2); time.sleep(0.3)
try: s.recv(65536)
except Exception: pass
s.sendall(b'screendump /tmp/oc2p-kf02/fb$N-b.ppm\n'); time.sleep(0.5)
try: s.recv(65536)
except Exception: pass"
sleep 2
sips -s format png /tmp/oc2p-kf02/fb$N-a.ppm --out /tmp/oc2p-kf02/fb$N-a.png
sips -s format png /tmp/oc2p-kf02/fb$N-b.ppm --out /tmp/oc2p-kf02/fb$N-b.png
md5 /tmp/oc2p-kf02/fb$N-a.ppm /tmp/oc2p-kf02/fb$N-b.ppm
ls -l /tmp/oc2p-kf02/fb$N-a.png /tmp/oc2p-kf02/fb$N-b.png
```

Note: the two `python3 -c` screendump lines use single-quoted shell `$MON`/`$N` expansion
inside double quotes as written — copy-paste exactly as above with N set; shell expands them.

## Step 6 — per-boot grep checklist (run after EACH boot; all must pass all 3 times)

K6 triple-boot + bad-syscall-99 + crasher-isolation list, taken from gate.sh L39/L49–L57:

```sh
N=1
LOG=/tmp/oc2p-kf02/serial-kf02-boot$N.log
for pat in "META OS KERNEL - alive" "mem summary: K4 up" "HELLO FROM USERSPACE" "user exit code 0" "task killed" "user readkey: entry" "sleeper: bad call refused" "user bad syscall 99 refused" "commands: status help" "STATUS tasks="; do printf "%-28s %s\n" "$pat" "$(grep -a -c "$pat" "$LOG")"; done
echo "--- loader refused (want 0) ---"; grep -a -c "loader refused" "$LOG" || true
echo "--- panics/triple (want 0) ---"; grep -a -c "panicked" "$LOG" || true; grep -a -c "PANIC" "$LOG" || true; grep -a -c "triple fault" "$LOG" || true
echo "--- STATUS line ---"; grep -a "STATUS tasks=" "$LOG"
echo "--- K6 isolation line ---"; grep -a "task killed" "$LOG"
echo "--- K6 bad-syscall lines ---"; grep -a "bad syscall 99 refused\|bad call refused" "$LOG"
```

Pass rule per boot: every `want` pattern count ≥ 1 (except `STATUS`/`commands` which require
the Step-5 drive.py typing — if 0, the drive attach failed, re-run Step 5 typing before killing
QEMU); `loader refused`/`panicked`/`PANIC`/`triple fault` all 0.

## Step 7 — kill, verdict, evidence (per boot, then closeout)

```sh
N=1
kill "$(cat /tmp/oc2p-kf02/qemu-boot$N.pid)"
sleep 1
rm -f /tmp/oc2p-kf02/mon-kf02-boot$N.sock
ls -l /tmp/oc2p-kf02/serial-kf02-boot$N.log
```

Closeout (after all 3 boots GREEN):

```sh
ls -l /tmp/oc2p-kf02/
git -C /tmp/oc2p-kf02-wt status --short
cp /tmp/oc2p-kf02/serial-kf02-boot1.log /Users/test/meta-os-500/os-build/logs/OC2P-kf02-boot1.log
cp /tmp/oc2p-kf02/serial-kf02-boot2.log /Users/test/meta-os-500/os-build/logs/OC2P-kf02-boot2.log
cp /tmp/oc2p-kf02/serial-kf02-boot3.log /Users/test/meta-os-500/os-build/logs/OC2P-kf02-boot3.log
```

Do NOT commit. Report `{ built, imaged, booted x3 }` + shas to parent.

## Biggest execution-day risk

The 0.9-path trap: running `os-build/gate.sh` verbatim (or pointing QEMU at
`kernel/target/.../bootimage-metaos-kernel.bin`) silently tests the WRONG/nonexistent image —
`cargo bootimage` exits 1 on 0.11 and no such bin exists. Mitigation is already in this runbook
(Step 3 records the expected fail, Step 4 builds `metaos-bios.img` via nightly imgtool, Step 5
boots that img). Second risk: imgtool's `bootloader 0.11.17` build.rs requires nightly cargo
with `-Zbuild-std` + `x86_64-unknown-uefi` target (stable build fails exit 101) — Step 4 does
this first. If either prerequisite regresses (new nightly, new bootloader), stop and file
verbatim logs per the OC2P-004 correction rule; do not work around inside `kernel/`.
