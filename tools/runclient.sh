#!/usr/bin/env bash
# Launch the 26.3 client headlessly under Xvfb with Mesa software rendering.
# Usage: runclient.sh GAME_DIR SECONDS [extra game args...]
# Leaves the X display on :99 while the game runs; the caller takes screenshots.
set -u
GAME_DIR="$1"; SECONDS_TO_RUN="$2"; shift 2
CLIENT=/home/claude/mcclient
export DISPLAY=:99
if ! xdpyinfo -display :99 >/dev/null 2>&1; then
	Xvfb :99 -screen 0 1280x720x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
	sleep 2
fi
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS=2
export SDL_VIDEO_FORCE_EGL="${SDL_VIDEO_FORCE_EGL:-0}"
mkdir -p "$GAME_DIR"
cd "$GAME_DIR" || exit 1
timeout "$SECONDS_TO_RUN" "$CLIENT/runtime/bin/java" -Xmx3G -Xss2M \
	-Djava.library.path="$GAME_DIR/natives" \
	-cp "$(cat "$CLIENT/${CLASSPATH_FILE:-classpath.txt}")" ${MAIN_CLASS:-net.minecraft.client.main.Main} \
	--username Diab --version 26.3 --gameDir "$GAME_DIR" \
	--assetsDir "$CLIENT/assets" --assetIndex 34 \
	--uuid 00000000-0000-0000-0000-000000000001 --accessToken 0 --userType legacy \
	--width "${WIN_W:-1280}" --height "${WIN_H:-720}" "$@" >"$GAME_DIR/stdout.log" 2>&1
echo "client exited with $?"
