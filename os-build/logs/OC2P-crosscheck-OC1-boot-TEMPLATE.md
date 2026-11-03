# OC2P cross-check template — OC1 boot evidence (READ-ONLY, no VM)

Scope: recompute shas, grep posted serials, inspect posted PNGs. OC1 files
are read, never edited. No QEMU, no boots, no writes.

## 0. Inputs (fill before running)

- `STATUS=<OC1-STATUS-file>` (OC1 posts serial + screendumps + shas per OC123 T3)
- `ISO=<ISO-bytes-as-copied-by-OC1>` + `ISO_SHA=<sha-from-OC3-status>`
- `SERIAL=<posted-QEMU-serial-log>`
- `SHOTS=<dir-with-posted-PNGs>` (8 per `screenshots/iso/PROOF_PLAN.md`:
  H2-grub, H2-splash, H4-greeter, H6-desktop, H8-installer, H8-installed,
  H10-doctor, H12-boot; T3 minimum: login, desktop, dock, launcher, one-app-open+close each)
- `MANIFEST=agent-layer/MANIFEST.md`

```sh
ls -la "$STATUS" "$SERIAL" "$ISO" 2>&1
ls -la "$SHOTS" 2>&1
```

## 1. ISO sha recompute

```sh
shasum -a 256 "$ISO"
grep -i -E "[0-9a-f]{64}" "$STATUS"
```

- [ ] `shasum` == `$ISO_SHA` == STATUS sha → AGREE (paste both) / mismatch → DISAGREE

## 2. No-panic grep

```sh
grep -i -E "panic|oops|failed" "$SERIAL" || echo "CLEAN"
wc -l "$SERIAL"; tail -20 "$SERIAL"
```

- [ ] Clean (or named-benign lines quoted) → AGREE / hits pasted → DISAGREE

## 3. PNGs + login visible

```sh
for f in H2-grub H2-splash H4-greeter H6-desktop H8-installer H8-installed H10-doctor H12-boot; do test -f "$SHOTS/$f.png" && echo "OK $f" || echo "MISSING $f"; done
```

- [ ] 8 present (or T3-minimum + fallback declared) → AGREE / unnamed gaps → DISAGREE
- [ ] H4-greeter shows login, H6-desktop shows wallpaper+dock+panel (state what is seen)

## 4. Desktop / dock / launcher / one-app-open each

- [ ] Desktop (H6) → AGREE / DISAGREE (path)
- [ ] Dock incl. agent-status → AGREE / DISAGREE (path)
- [ ] Launcher → AGREE / DISAGREE (path)
- [ ] One-app-open+close each (or named TryExec/NoDisplay degraded) → AGREE / DISAGREE (paths)

## 5. Drop-in shas (OC1 runs target-side, OC2 checks posted log)

```sh
grep -E "DROPIN (OK|FAIL|SKIP)" "$STATUS" || echo "NO DROPIN LINES POSTED"
shasum -a 256 agent-layer/MANIFEST.md
```

- [ ] All `OK … sha matches`, no FAIL → AGREE / any FAIL → DISAGREE

## 6. Enabled + active (SKIP honest without user systemd)

- [ ] enabled + active OK, or `SKIP: no systemctl` → AGREE / `FAIL NOT enabled/active` → DISAGREE

## 7. No keys in env

```sh
grep -i -E "BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|sk-[A-Za-z0-9]{20,}|password" "$STATUS" || echo "CLEAN"
```

- [ ] `OK … no key material`, nothing secret in evidence → AGREE / hit → DISAGREE

---

VERDICT: AGREE / DISAGREE — evidence: `$STATUS $SERIAL $ISO $SHOTS` (filled values here)
