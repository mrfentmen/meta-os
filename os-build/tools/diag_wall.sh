#!/bin/sh
# Temporary in-guest diagnostic: wallpaper / terminal / session state.
# Non-interactive on purpose: a pager or a interactive prompt would hang the
# pipeline that ships the output off the guest.
export PAGER=cat SYSTEMD_PAGER=cat GIT_PAGER=cat
echo "== xrandr"
xrandr 2>&1 | head -4
echo "== meta-live"
pgrep -af meta-live 2>&1 | head -3
echo "== unit"
systemctl --user is-active metaos-livebg.service 2>&1
journalctl --user -u metaos-livebg.service --no-pager -n 8 2>&1 | tail -8
echo "== loop frames"
ls /usr/share/metaos/studio-loop 2>/dev/null | wc -l
ls -l /usr/share/metaos/studio-loop/loop-00.jpg 2>&1 | head -2
echo "== session log"
grep -iE "livebg|wallpaper|terminal|meta-desktop" /tmp/metaos-session.log 2>&1 | tail -8
echo "== terminal rc"
ls -l "$HOME/.config/xfce4/terminal/terminalrc" 2>&1
echo "== windows"
wmctrl -l 2>&1 | head -6
echo "== end"
