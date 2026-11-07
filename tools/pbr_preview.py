"""Preview LabPBR maps: albedo, decoded normal, height, AO, smoothness, F0, emission, and a relit tile.

Usage: python3 -I pbr_preview.py TEXTURE_DIR OUT_PNG name [name ...]
The relit tile lights a 3x3 tiling of the texture from the upper left using the normal map
(DirectX Y-down), so bumps should read as raised with highlights on their top-left edges.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

S = 6


def up(arr):
	img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
	return img.resize((img.size[0] * S, img.size[1] * S), Image.NEAREST).convert("RGB")


def main():
	tdir, out = sys.argv[1:3]
	names = sys.argv[3:]
	tiles = []
	for name in names:
		alb = np.asarray(Image.open(os.path.join(tdir, name + ".png")).convert("RGBA")).astype(np.float64)
		n = np.asarray(Image.open(os.path.join(tdir, name + "_n.png")).convert("RGBA")).astype(np.float64)
		s = np.asarray(Image.open(os.path.join(tdir, name + "_s.png")).convert("RGBA")).astype(np.float64)
		w = alb.shape[1]
		alb, n, s = alb[:w], n[:w], s[:w]
		nx = n[..., 0] / 255 * 2 - 1
		ny = n[..., 1] / 255 * 2 - 1
		nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
		light = np.array([-0.6, -0.6, 0.53])
		light /= np.linalg.norm(light)
		lam = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1) * (n[..., 2] / 255)
		relit = alb[..., :3] * (0.25 + 0.95 * lam[..., None])
		relit = np.tile(relit, (3, 3, 1))
		grey = lambda c: np.repeat(c[..., None], 3, axis=2)
		panels = [alb[..., :3], n[..., :3] * [1, 1, 0] + [0, 0, 128], grey(n[..., 3]), grey(n[..., 2]), grey(s[..., 0]),
			grey(np.where(s[..., 1] >= 230, 255, s[..., 1] * 4)), grey(s[..., 3])]
		row = [up(p) for p in panels]
		rel = Image.fromarray(np.clip(relit, 0, 255).astype(np.uint8)).resize((w * 3 * 2, w * 3 * 2), Image.NEAREST)
		tiles.append((name, row, rel))
	pw = 16 * S
	width = 7 * (pw + 4) + 16 * 3 * 2 + 10
	height = len(tiles) * (max(pw, 96) + 18) + 18
	sheet = Image.new("RGB", (width, height), (30, 30, 30))
	d = ImageDraw.Draw(sheet)
	for i, label in enumerate(["albedo", "normal", "height", "AO", "smooth", "F0/metal", "emission", "relit 3x3"]):
		d.text((i * (pw + 4) + 2, 2), label, fill=(255, 255, 255))
	for r, (name, row, rel) in enumerate(tiles):
		y = 18 + r * (max(pw, 96) + 18)
		for i, img in enumerate(row):
			sheet.paste(img.crop((0, 0, pw, pw)), (i * (pw + 4), y))
		sheet.paste(rel, (7 * (pw + 4), y))
		d.text((2, y + pw + 2), name, fill=(255, 255, 0))
	sheet.save(out)
	print(out, sheet.size)


if __name__ == "__main__":
	main()
