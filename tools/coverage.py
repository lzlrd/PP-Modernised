"""Compare texture path coverage of resource packs against a vanilla asset tree.

Usage: python3 -I coverage.py VANILLA_TEXTURES PACK_A_TEXTURES PACK_B_TEXTURES OUT_DIR
"""
import os
import sys
from collections import Counter


def list_pngs(root):
	found = set()
	for directory, _, files in os.walk(root):
		for name in files:
			if name.endswith(".png"):
				found.add(os.path.relpath(os.path.join(directory, name), root))
	return found


def by_top_dir(paths):
	return Counter(p.split("/")[0] if "/" in p else "." for p in paths).most_common()


def main():
	vanilla_root, a_root, b_root, out_dir = sys.argv[1:5]
	vanilla = list_pngs(vanilla_root)
	a = list_pngs(a_root)
	b = list_pngs(b_root)
	print("vanilla textures:", len(vanilla))
	print("A covers:", len(vanilla & a), "| B covers:", len(vanilla & b))
	print("A or B covers:", len(vanilla & (a | b)))
	print("both cover (art choice):", len(vanilla & a & b))
	print("only A:", len(vanilla & (a - b)), "| only B:", len(vanilla & (b - a)))
	missing_b = vanilla - b
	missing_both = vanilla - a - b
	print("B missing by dir:", by_top_dir(missing_b))
	print("A and B both missing by dir:", by_top_dir(missing_both))
	os.makedirs(out_dir, exist_ok=True)
	with open(os.path.join(out_dir, "b_missing.txt"), "w") as f:
		f.write("\n".join(sorted(missing_b)))
	with open(os.path.join(out_dir, "both_missing.txt"), "w") as f:
		f.write("\n".join(sorted(missing_both)))


if __name__ == "__main__":
	main()
