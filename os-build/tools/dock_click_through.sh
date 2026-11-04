#!/bin/sh
# dock_click_through.sh — click every dock tile in the live session and record
# which window each one opens.
#
# Why xdotool and not the hypervisor: QEMU's input-send-event never reached the
# usb-tablet in this harness (no cursor, no clicks), so the pointer was driven
# from inside the guest instead. The click, the plank item and the .desktop are
# all real; only the host-to-guest pointer transport is bypassed.
#
# Windows opened by a tile are killed by pid, not closed with wmctrl: `wmctrl -c`
# on a terminal pops "There is still a process running" and the modal dialog then
# swallows every later click, which silently poisons the rest of the run.
#
# Usage (inside the guest, as the session user):
#   DISPLAY=:0 sh dock_click_through.sh
set -u
export DISPLAY="${DISPLAY:-:0}"

# plank owns several windows: the dock itself and a 10x10 helper. Picking the
# first id got the helper, so every computed click landed in the wallpaper and
# all 27 tiles reported NOTHING. Choose the window that is actually the bar.
DOCK=""
for w in $(xdotool search --class plank 2>/dev/null); do
  eval "$(xdotool getwindowgeometry --shell "$w")"
  if [ "${WIDTH:-0}" -gt 400 ]; then DOCK=$w; break; fi
done
[ -n "$DOCK" ] || { echo "no plank bar window — is the dock running?"; exit 1; }
eval "$(xdotool getwindowgeometry --shell "$DOCK")"
echo "dock window $DOCK at ${X},${Y} size ${WIDTH}x${HEIGHT}"
# icons sit on the bottom edge of that box, not in its middle
CY=$(( Y + HEIGHT - 40 ))

LAUNCHERS=$(ls "$HOME/.config/plank/dock1/launchers" 2>/dev/null | sort)
N=$(echo "$LAUNCHERS" | grep -c . )
echo "dock items: $N"

ids() { xdotool search --onlyvisible --name '.*' 2>/dev/null | sort; }

i=0
for f in $LAUNCHERS; do
  cx=$(( X + (WIDTH * (2 * i + 1)) / (2 * N) ))
  cy=$CY
  before=$(ids)
  xdotool mousemove "$cx" "$cy" click 1
  sleep 3
  after=$(ids)
  new=$(printf '%s\n' "$after" | grep -vxF "$before" | head -3)
  if [ -n "$new" ]; then
    name="-"
    for w in $new; do
      n=$(xdotool getwindowname "$w" 2>/dev/null)
      [ -n "$n" ] && [ "$n" != "-" ] && { name="$n"; break; }
    done
    echo "TILE $f -> OPENED \"$name\""
    for w in $new; do
      pid=$(xdotool getwindowpid "$w" 2>/dev/null)
      [ -n "${pid:-}" ] && kill "$pid" 2>/dev/null
    done
    sleep 1
    for w in $new; do
      pid=$(xdotool getwindowpid "$w" 2>/dev/null)
      [ -n "${pid:-}" ] && kill -9 "$pid" 2>/dev/null
    done
  else
    echo "TILE $f -> NOTHING"
  fi
  i=$((i + 1))
done
echo "done: $i tiles clicked"
