#!/usr/bin/env bash
# Assemble the Java pack folder and pp_modernised.zip from the repo tree, plus the Sparkles and
# Dungeons and Taverns compatibility patch, pp_modernised_compat.zip.
# Usage: build_java.sh REPO_DIR OUT_DIR
set -euo pipefail
REPO="$1"; OUT="$2"
NAME="PP-Modernised"
mkdir -p "$OUT"
rm -rf "${OUT:?}/$NAME"
rsync -a --delete \
	--exclude '.git' --exclude '.github' --exclude '*.zip' --exclude 'tools/' \
	--exclude 'bedrock/' --exclude 'compat/' --exclude 'Pixel Perfection Legacy Old Paintings/' \
	--exclude '*.md' --exclude '.gitignore' \
	"$REPO/" "$OUT/$NAME/"
cp "$REPO"/LICENSE.md "$REPO"/CREDITS.md "$OUT/$NAME/" 2>/dev/null || true
rm -f "$OUT/pp_modernised.zip"
(cd "$OUT/$NAME" && zip -q -r -X "../pp_modernised.zip" .)
echo "built $OUT/pp_modernised.zip ($(du -h "$OUT/pp_modernised.zip" | cut -f1))"
python3 -I "$(dirname "$0")/build_compat.py" "$REPO" "$OUT"
rm -f "$OUT/pp_modernised_compat.zip"
(cd "$OUT/PP-Modernised-Compat" && zip -q -r -X "../pp_modernised_compat.zip" .)
echo "built $OUT/pp_modernised_compat.zip ($(du -h "$OUT/pp_modernised_compat.zip" | cut -f1))"
