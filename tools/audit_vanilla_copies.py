"""Find pack textures that are pixel-identical (or near) to the vanilla texture at the same path.

Usage: python3 -I audit_vanilla_copies.py VANILLA_TEXTURES PACK_TEXTURES OUT_FILE
"""
import os
import sys

import numpy as np
from PIL import Image


def load(path):
	img = Image.open(path).convert("RGBA")
	arr = np.asarray(img, dtype=np.int16)
	# Ignore colour under fully transparent pixels.
	arr = arr.copy()
	arr[arr[..., 3] == 0] = 0
	return arr


def main():
	vanilla_root, pack_root, out_file = sys.argv[1:4]
	identical, near = [], []
	for directory, _, files in os.walk(pack_root):
		for name in files:
			if not name.endswith(".png"):
				continue
			rel = os.path.relpath(os.path.join(directory, name), pack_root)
			vpath = os.path.join(vanilla_root, rel)
			if not os.path.exists(vpath):
				continue
			try:
				a = load(os.path.join(pack_root, rel))
				b = load(vpath)
			except Exception as exc:  # Unreadable image: report and carry on.
				print("unreadable", rel, exc)
				continue
			if a.shape != b.shape:
				continue
			diff = np.abs(a - b)
			changed = np.count_nonzero(diff.max(axis=-1) > 8)
			if changed == 0:
				identical.append(rel)
			elif changed / (a.shape[0] * a.shape[1]) < 0.02:
				near.append(rel)
	with open(out_file, "w") as f:
		f.write("# identical\n" + "\n".join(sorted(identical)) + "\n# near (<2% pixels changed)\n" + "\n".join(sorted(near)) + "\n")
	print("identical:", len(identical), "near:", len(near))


if __name__ == "__main__":
	main()
