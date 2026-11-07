#!/usr/bin/env bash
# Load the showcase world in the headless 26.3 client and screenshot each view.
# Usage: shoot.sh GAME_DIR OUT_DIR VIEWS_FILE [extra commands file]
set -u
G="$1"; OUT="$2"; VIEWS="$3"; EXTRA="${4:-}"
mkdir -p "$OUT"
export DISPLAY=:99
rm -rf "${G:?}/logs"
/home/claude/scripts/runclient.sh "$G" 2400 --quickPlaySingleplayer showcase >/dev/null 2>&1 &
for i in $(seq 1 200); do
	grep -q 'joined the game' "$G/logs/latest.log" 2>/dev/null && break
	sleep 5
done
sleep 25
cmd() {
	xdotool key --clearmodifiers t
	sleep 1.5
	xdotool type --delay 30 "$1"
	sleep 0.5
	xdotool key Return
}
xdotool key F1
cmd "/function ppm:build"
sleep 8
cmd "/function ppm:grid"
sleep 8
if [ -n "$EXTRA" ]; then
	while read -r line; do [ -n "$line" ] && cmd "$line" && sleep 3; done < "$EXTRA"
fi
while read -r view; do
	[ -z "$view" ] && continue
	cmd "/function ppm:view_$view"
	sleep "${SHOT_WAIT:-18}"
	import -window root "$OUT/$view.png"
done < "$VIEWS"
pkill -f 'mcclient/runtime/bin/java'
sleep 3
echo "screenshots in $OUT"
