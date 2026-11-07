"""Render vanilla-vs-pack comparison sheets for a list of texture paths.

Usage: python3 -I contact_sheet.py VANILLA_TEXTURES PACK_TEXTURES LIST_FILE OUT_PNG [COLUMNS]
Each cell shows the vanilla texture (left) and the pack texture (right), first animation frame
only, upscaled with nearest-neighbour onto a checkerboard so transparency is visible.
"""
import os
import sys

from PIL import Image, ImageDraw

CELL = 96


def checker(size):
	img = Image.new("RGBA", size, (200, 200, 200, 255))
	d = ImageDraw.Draw(img)
	for y in range(0, size[1], 8):
		for x in range(0, size[0], 8):
			if (x // 8 + y // 8) % 2:
				d.rectangle([x, y, x + 7, y + 7], fill=(150, 150, 150, 255))
	return img


def thumb(path):
	box = checker((CELL, CELL))
	if not os.path.exists(path):
		ImageDraw.Draw(box).line([0, 0, CELL, CELL], fill=(255, 0, 0, 255), width=3)
		return box
	img = Image.open(path).convert("RGBA")
	w, h = img.size
	if h > w and h % w == 0:
		img = img.crop((0, 0, w, w))
	scale = max(1, min(CELL // img.size[0], CELL // img.size[1]))
	img = img.resize((img.size[0] * scale, img.size[1] * scale), Image.NEAREST)
	if img.size[0] > CELL or img.size[1] > CELL:
		img.thumbnail((CELL, CELL), Image.NEAREST)
	box.alpha_composite(img, ((CELL - img.size[0]) // 2, (CELL - img.size[1]) // 2))
	return box


def main():
	vroot, proot, list_file, out = sys.argv[1:5]
	cols = int(sys.argv[5]) if len(sys.argv) > 5 else 6
	paths = [p.strip() for p in open(list_file) if p.strip()]
	rows = (len(paths) + cols - 1) // cols
	cw, ch = CELL * 2 + 12, CELL + 16
	sheet = Image.new("RGBA", (cols * cw, rows * ch), (40, 40, 40, 255))
	d = ImageDraw.Draw(sheet)
	for i, p in enumerate(paths):
		x, y = (i % cols) * cw, (i // cols) * ch
		sheet.alpha_composite(thumb(os.path.join(vroot, p)), (x, y))
		sheet.alpha_composite(thumb(os.path.join(proot, p)), (x + CELL + 4, y))
		d.text((x + 2, y + CELL + 2), p.split("/")[-1][:34], fill=(255, 255, 255, 255))
	sheet.save(out)
	print(out, sheet.size)


if __name__ == "__main__":
	main()
