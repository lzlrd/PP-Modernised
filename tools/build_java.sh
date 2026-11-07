#!/usr/bin/env bash
# Assemble the Java pack folder and zip from the repo tree.
# Usage: build_java.sh REPO_DIR OUT_DIR
set -euo pipefail
REPO="$1"; OUT="$2"
NAME="PP-Modernised"
mkdir -p "$OUT"
rm -rf "${OUT:?}/$NAME"
rsync -a --delete \
	--exclude '.git' --exclude '.github' --exclude '*.zip' --exclude 'tools/' \
	--exclude 'bedrock/' --exclude 'Pixel Perfection Legacy Old Paintings/' \
	--exclude '*.md' --exclude '.gitignore' \
	"$REPO/" "$OUT/$NAME/"
cp "$REPO"/LICENSE.md "$REPO"/CREDITS.md "$OUT/$NAME/" 2>/dev/null || true
rm -f "$OUT/$NAME.zip"
(cd "$OUT/$NAME" && zip -q -r -X "../$NAME.zip" .)
echo "built $OUT/$NAME.zip ($(du -h "$OUT/$NAME.zip" | cut -f1))"
