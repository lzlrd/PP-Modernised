"""Assemble the PP Modernised compatibility patch for Sparkles and Dungeons and Taverns.

Both packs ship files at the same paths as PP Modernised, so whichever loads higher wins outright:
- Sparkles' wither skeleton skins 2-8 and 10 and its properties replace PPL's biome variants (2-9).
- Dungeons and Taverns' own chart, map and key textures replace PPL's.

The patch loads above both. It carries a merged wither_skeleton.properties (from compat/), PPL's
wither skeleton skins moved to 11-18 with their LabPBR specular maps, empty specular maps for
Sparkles' skins so PPL's maps for the old 2-9 don't land on Sparkles' art, and PPL's D&T textures.

Usage: python3 -I build_compat.py REPO_DIR OUT_DIR
Writes OUT_DIR/PP-Modernised-Compat; build_java.sh zips it to pp_modernised_compat.zip.
"""
import os
import shutil
import struct
import sys
import zlib

SKELETON = "assets/minecraft/optifine/random/entity/skeleton"
PPL_SKINS = range(2, 10)
SKIN_OFFSET = 9
SPARKLES_SKINS = list(range(2, 9)) + [10]


def png_size(path):
	with open(path, "rb") as f:
		head = f.read(24)
	return struct.unpack(">II", head[16:24])


def blank_png(path, width, height):
	"""Write a fully transparent RGBA PNG, which LabPBR shaders read the same as no specular map."""
	def chunk(kind, data):
		body = kind + data
		return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
	raw = b"".join(b"\x00" + b"\x00" * (width * 4) for _ in range(height))
	with open(path, "wb") as f:
		f.write(b"\x89PNG\r\n\x1a\n")
		f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
		f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
		f.write(chunk(b"IEND", b""))


def main():
	repo, out = sys.argv[1:3]
	pack = os.path.join(out, "PP-Modernised-Compat")
	if os.path.exists(pack):
		shutil.rmtree(pack)
	shutil.copytree(os.path.join(repo, "compat"), pack)
	shutil.copy(os.path.join(repo, "pack.png"), pack)
	for name in ("LICENSE.md", "CREDITS.md"):
		shutil.copy(os.path.join(repo, name), pack)

	src = os.path.join(repo, SKELETON)
	dst = os.path.join(pack, SKELETON)
	os.makedirs(dst, exist_ok=True)
	for i in PPL_SKINS:
		for suffix in ("", "_s", "_n", "_e"):
			f = os.path.join(src, "wither_skeleton%d%s.png" % (i, suffix))
			if os.path.exists(f):
				shutil.copy(f, os.path.join(dst, "wither_skeleton%d%s.png" % (i + SKIN_OFFSET, suffix)))
	for i in SPARKLES_SKINS:
		f = os.path.join(src, "wither_skeleton%d_s.png" % i)
		if os.path.exists(f):
			w, h = png_size(f)
			blank_png(os.path.join(dst, "wither_skeleton%d_s.png" % i), w, h)

	items = os.path.join(repo, "assets", "dnt", "textures", "item")
	copied = 0
	for directory, _, names in os.walk(items):
		for name in sorted(names):
			if not name.endswith(".png") or name.endswith(("_n.png", "_s.png", "_e.png")):
				continue
			rel = os.path.relpath(os.path.join(directory, name), repo)
			os.makedirs(os.path.dirname(os.path.join(pack, rel)), exist_ok=True)
			shutil.copy(os.path.join(repo, rel), os.path.join(pack, rel))
			copied += 1
	print("compat: %d wither skeleton skins moved to %d-%d, %d D&T textures" % (
		len(PPL_SKINS), PPL_SKINS[0] + SKIN_OFFSET, PPL_SKINS[-1] + SKIN_OFFSET, copied))


if __name__ == "__main__":
	main()
