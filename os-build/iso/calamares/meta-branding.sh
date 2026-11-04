#!/bin/sh
# MetaOS 1.0 -- runs INSIDE the target chroot during Calamares exec.
#
# Installed at /usr/local/lib/metaos/meta-branding.sh by provision.sh and
# called by the `meta-branding` shellprocess instance. Everything here edits
# the installed system; nothing here touches the running live session.
#
# Rules kept deliberately: log every step, keep going on a soft failure but
# print a WARN into the install log, and never leave the target booting to a
# text console. A hard failure (set -e) aborts the install rather than
# producing a half-branded disk.
set -eu

LOG=/var/log/metaos-install.log
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "== meta-branding $(date -u '+%Y-%m-%dT%H:%M:%SZ') =="

# 1. Hostname and hosts entry.
printf 'metaos\n' > /etc/hostname
if grep -q '^127\.0\.1\.1' /etc/hosts; then
    sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tmetaos/' /etc/hosts
else
    printf '127.0.1.1\tmetaos\n' >> /etc/hosts
fi
echo "hostname: metaos"

# 2. Release marker. Contract values (R3: previously stamped the wrong ID_LIKE
# and short names; the live image carries "Meta OS 1.0 (Ribbon)" with
# ID_LIKE=debian, so the installed system must match). No URL beyond
# metaos.local by design (see branding.desc).
cat > /etc/metaos-release <<'RELEASE'
NAME="Meta OS"
VERSION="1.0 (Ribbon)"
VERSION_ID="1.0"
VERSION_CODENAME=ribbon
ID=metaos
ID_LIKE=debian
LOGO=metaos
PRETTY_NAME="Meta OS 1.0 (Ribbon)"
HOME_URL="https://metaos.local"
SUPPORT_URL="https://metaos.local/support"
BUG_REPORT_URL="https://metaos.local/issues"
RELEASE
if [ -f /etc/os-release ] && [ ! -f /etc/os-release.base-flavour ]; then
    cp -f /etc/os-release /etc/os-release.base-flavour
fi
cp -f /etc/metaos-release /etc/os-release
echo "release: /etc/metaos-release installed (base flavour kept as os-release.base-flavour)"

# 3. Splash on the INSTALLED system.
if [ -d /usr/share/plymouth/themes/metaos ]; then
    mkdir -p /etc/plymouth
    cat > /etc/plymouth/plymouthd.conf <<'PLYMOUTH'
[Daemon]
Theme=metaos
ShowDelay=0
DeviceTimeout=8
PLYMOUTH
    if command -v plymouth-set-default-theme >/dev/null 2>&1; then
        # -R rebuilds the initramfs; without it the first boot still shows
        # the base flavour's splash baked into the old initrd.
        if ! plymouth-set-default-theme -R metaos; then
            echo "WARN: plymouth-set-default-theme -R failed; theme set but initramfs not rebuilt"
        fi
    else
        echo "WARN: plymouth-set-default-theme missing; theme config written, initramfs not rebuilt"
    fi
else
    echo "WARN: /usr/share/plymouth/themes/metaos missing in target; splash stays base flavour"
fi

# 4. The installed system must never launch the installer again.
rm -f /etc/xdg/autostart/metaos-install.desktop

# 5. Boot to the login screen, not a text console.
if systemctl enable lightdm.service; then
    echo "displaymanager: lightdm enabled"
else
    echo "WARN: could not enable lightdm.service"
fi
if systemctl set-default graphical.target; then
    echo "target: graphical.target"
else
    echo "WARN: could not set graphical.target as default"
fi

# 6. No autologin on the installed system: the login screen is the product's
#    front door until the boss says otherwise.
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/90-metaos.conf <<'LIGHTDM'
[Seat:*]
autologin-user=
autologin-user-timeout=0
LIGHTDM
echo "lightdm: autologin disabled on the installed system"

# 7. Landing zone for the desktop theme owned by OC1's lane.
mkdir -p /usr/share/metaos

echo "== meta-branding done =="
exit 0
