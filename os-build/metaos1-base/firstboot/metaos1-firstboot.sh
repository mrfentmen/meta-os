#!/bin/sh
# MetaOS 1.0 first-boot setup (Hana lane, slice 1).
# Runs once via metaos1-firstboot.service. Idempotent, non-interactive,
# network-free, credential-free.
#   - Applies the system mimeapps defaults into the console user's
#     ~/.config/mimeapps.list ONLY if that file does not already exist
#     (a user's own choice is never overwritten).
#   - Writes /var/lib/metaos1-firstboot.done so later boots skip it.
# It never prompts, never sets or reads a password, never writes a
# secret, and never contacts any service. If anything here fails, the
# script still exits 0: a base default must never block a login.
set -u
DONE_FILE=/var/lib/metaos1-firstboot.done
SYSTEM_DEFAULTS=/etc/xdg/mimeapps.list

if [ -f "$DONE_FILE" ]; then
    exit 0
fi

# Console user: the first UID >= 1000 with a home directory, if any.
CONSOLE_USER=""
for candidate in /home/*; do
    if [ -d "$candidate" ]; then
        CONSOLE_USER=$(basename "$candidate")
        break
    fi
done

if [ -n "${CONSOLE_USER:-}" ] && [ -f "$SYSTEM_DEFAULTS" ]; then
    USER_CONFIG="/home/$CONSOLE_USER/.config/mimeapps.list"
    if [ ! -f "$USER_CONFIG" ]; then
        mkdir -p "/home/$CONSOLE_USER/.config" 2>/dev/null || true
        cp "$SYSTEM_DEFAULTS" "$USER_CONFIG" 2>/dev/null || true
        chown "$CONSOLE_USER:$CONSOLE_USER" "$USER_CONFIG" 2>/dev/null || true
    fi
fi

mkdir -p /var/lib 2>/dev/null || true
touch "$DONE_FILE" 2>/dev/null || true
exit 0
