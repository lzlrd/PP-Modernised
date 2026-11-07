"""Give flat block models real depth by extruding their textures, like item models do.

Every zero-thickness textured plane in a target block's models becomes a set of 1px-deep boxes
following the texture's opaque pixels: front and back faces carry the art, and only edges that
border transparency get side faces. Planes on animated textures, rotated face UVs, or that would
need more than MAX_ELEMENTS boxes stay flat.

Usage: python3 -I make3d.py VANILLA_ASSETS PACK_ASSETS BLOCKS_FILE LOG_FILE
BLOCKS_FILE lists block ids (one per line) whose blockstate models should be made 3D.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

MAX_ELEMENTS = 160
DEPTH = 1.0
AXES = {"x": 0, "y": 1, "z": 2}
FACE_AXIS = {"north": (2, -1), "south": (2, 1), "west": (0, -1), "east": (0, 1), "down": (1, -1), "up": (1, 1)}
AXIS_FACE = {(2, -1): "north", (2, 1): "south", (0, -1): "west", (0, 1): "east", (1, -1): "down", (1, 1): "up"}
# Default UV per face from an element's from/to (vanilla's auto-UV rules).
AUTO_UV = {
	"down": lambda f, t: [f[0], 16 - t[2], t[0], 16 - f[2]],
	"up": lambda f, t: [f[0], f[2], t[0], t[2]],
	"north": lambda f, t: [16 - t[0], 16 - t[1], 16 - f[0], 16 - f[1]],
	"south": lambda f, t: [f[0], 16 - t[1], t[0], 16 - f[1]],
	"west": lambda f, t: [f[2], 16 - t[1], t[2], 16 - f[1]],
	"east": lambda f, t: [16 - t[2], 16 - t[1], 16 - f[2], 16 - f[1]],
}


def norm(ref):
	return ref if ":" in ref else "minecraft:" + ref


def split(ref):
	ns, path = norm(ref).split(":", 1)
	return ns, path


class Assets:
	def __init__(self, vanilla, pack):
		self.roots = [pack, vanilla]
		self.pack = pack

	def find(self, sub, ref, ext):
		ns, path = split(ref)
		for root in self.roots:
			p = os.path.join(root, ns, sub, path + ext)
			if os.path.exists(p):
				return p
		return None

	def json(self, sub, ref):
		p = self.find(sub, ref, ".json")
		if not p:
			return None
		with open(p, encoding="utf-8-sig") as f:
			return json.load(f)


def resolve(assets, name, depth=0):
	"""Return merged textures, elements and ambient occlusion along the parent chain."""
	data = assets.json("models", name) or {}
	tex, elements, ao = {}, None, None
	if data.get("parent") and depth < 30 and not data["parent"].startswith("builtin"):
		tex, elements, ao = resolve(assets, norm(data["parent"]), depth + 1)
		tex = dict(tex)
	tex.update(data.get("textures", {}))
	if "elements" in data:
		elements = data["elements"]
	if "ambientocclusion" in data:
		ao = data["ambientocclusion"]
	return tex, elements, ao


def lookup(tex, ref):
	seen = set()
	while isinstance(ref, str) and ref.startswith("#") and ref not in seen:
		seen.add(ref)
		ref = tex.get(ref[1:])
	if isinstance(ref, dict):
		ref = ref.get("sprite")
	return ref


def plane_mapper(face, el, uv):
	"""Return f(u, v) -> 3D point on the plane for face-local uv coordinates."""
	f, t = el["from"], el["to"]
	u1, v1, u2, v2 = uv
	du = (u2 - u1) or 1e-9
	dv = (v2 - v1) or 1e-9

	def lerp(a, b, s):
		return a + (b - a) * s

	def m(u, v):
		su, sv = (u - u1) / du, (v - v1) / dv
		if face == "north":
			return [lerp(t[0], f[0], su), lerp(t[1], f[1], sv), f[2]]
		if face == "south":
			return [lerp(f[0], t[0], su), lerp(t[1], f[1], sv), f[2]]
		if face == "east":
			return [f[0], lerp(t[1], f[1], sv), lerp(t[2], f[2], su)]
		if face == "west":
			return [f[0], lerp(t[1], f[1], sv), lerp(f[2], t[2], su)]
		if face == "up":
			return [lerp(f[0], t[0], su), f[1], lerp(f[2], t[2], sv)]
		return [lerp(f[0], t[0], su), f[1], lerp(t[2], f[2], sv)]
	return m


def extrude(el, tex, assets):
	"""Return a list of elements replacing a flat plane element, or None to keep it."""
	f, t = el.get("from"), el.get("to")
	if not f or not t:
		return None
	thin = [i for i in range(3) if abs(t[i] - f[i]) < 0.01]
	if len(thin) != 1:
		return None
	n = thin[0]
	faces = el.get("faces") or {}
	front = None
	for name in ("north", "south", "east", "west", "up", "down"):
		if name in faces and FACE_AXIS[name][0] == n:
			front = name
			break
	if front is None:
		return None
	spec = faces[front]
	if spec.get("rotation", 0) != 0:
		return None
	ref = lookup(tex, spec.get("texture", ""))
	if not isinstance(ref, str):
		return None
	png = assets.find("textures", ref, ".png")
	if not png or os.path.exists(png + ".mcmeta"):
		return None
	img = np.asarray(Image.open(png).convert("RGBA"))
	W = img.shape[1]
	H = img.shape[0]
	if H != W:
		return None
	uv = spec.get("uv") or AUTO_UV[front](f, t)
	scale = W / 16.0
	pu1, pu2 = sorted((uv[0] * scale, uv[2] * scale))
	pv1, pv2 = sorted((uv[1] * scale, uv[3] * scale))
	x0, x1 = int(round(pu1)), int(round(pu2))
	y0, y1 = int(round(pv1)), int(round(pv2))
	if x1 <= x0 or y1 <= y0:
		return None
	alpha = img[y0:y1, x0:x1, 3] > 16
	if not alpha.any():
		return []
	mapper = plane_mapper(front, el, uv)
	plane = f[n]
	# Extrude toward the nearer block face for planes hugging a wall/floor, else centre it.
	if plane >= 15:
		lo, hi = plane, min(16.0, plane + DEPTH)
	elif plane <= 1:
		lo, hi = max(0.0, plane - DEPTH), plane
		if hi - lo < 0.25:
			lo, hi = plane, plane + DEPTH
	else:
		lo, hi = plane - DEPTH / 2, plane + DEPTH / 2
	back = AXIS_FACE[(n, -FACE_AXIS[front][1])]
	common = {k: v for k, v in el.items() if k in ("rotation", "shade", "light_emission")}
	base_face = {k: v for k, v in spec.items() if k in ("tintindex",)}

	def face_dir(du, dv):
		"""World face name for moving one texture pixel in (du, dv)."""
		a = mapper((x0 + 0.5) / scale, (y0 + 0.5) / scale)
		b = mapper((x0 + 0.5 + du) / scale, (y0 + 0.5 + dv) / scale)
		d = [b[i] - a[i] for i in range(3)]
		i = int(np.argmax(np.abs(d)))
		return AXIS_FACE[(i, 1 if d[i] > 0 else -1)]

	left, right, top, bottom = face_dir(-1, 0), face_dir(1, 0), face_dir(0, -1), face_dir(0, 1)
	flip_u = front in ("north", "south", "east", "west")
	out = []
	h, w = alpha.shape
	for row in range(h):
		col = 0
		while col < w:
			if not alpha[row, col]:
				col += 1
				continue
			start = col
			while col < w and alpha[row, col]:
				col += 1
			end = col  # exclusive
			# Split the run where top/bottom exposure changes.
			seg = start
			while seg < end:
				up_open = row == 0 or not alpha[row - 1, seg]
				down_open = row == h - 1 or not alpha[row + 1, seg]
				stop = seg + 1
				while stop < end and (row == 0 or not alpha[row - 1, stop]) == up_open and \
						(row == h - 1 or not alpha[row + 1, stop]) == down_open:
					stop += 1
				gx0, gx1 = x0 + seg, x0 + stop
				gy0, gy1 = y0 + row, y0 + row + 1
				ua, va = gx0 / scale, gy0 / scale
				ub, vb = gx1 / scale, gy1 / scale
				# Map the run's corners from face uv space onto the plane.
				p1 = mapper(ua, va)
				p2 = mapper(ub, vb)
				lo3 = [min(p1[i], p2[i]) for i in range(3)]
				hi3 = [max(p1[i], p2[i]) for i in range(3)]
				lo3[n], hi3[n] = lo, hi
				fu1, fu2 = (ua, ub) if uv[2] >= uv[0] else (ub, ua)
				fv1, fv2 = (va, vb) if uv[3] >= uv[1] else (vb, va)
				fuv = [round(fu1, 4), round(fv1, 4), round(fu2, 4), round(fv2, 4)]
				buv = [fuv[2], fuv[1], fuv[0], fuv[3]] if flip_u else [fuv[0], fuv[3], fuv[2], fuv[1]]
				el_faces = {front: dict(base_face, uv=fuv, texture=spec["texture"]),
					back: dict(base_face, uv=buv, texture=spec["texture"])}
				px_uv = lambda gx, gy: [round(gx / scale, 4), round(gy / scale, 4), round((gx + 1) / scale, 4), round((gy + 1) / scale, 4)]
				if seg == start:
					el_faces[left] = dict(base_face, uv=px_uv(gx0, gy0), texture=spec["texture"])
				if stop == end:
					el_faces[right] = dict(base_face, uv=px_uv(gx1 - 1, gy0), texture=spec["texture"])
				strip = [round(ua, 4), round(va, 4), round(ub, 4), round(vb, 4)]
				if up_open:
					el_faces[top] = dict(base_face, uv=strip, texture=spec["texture"])
				if down_open:
					el_faces[bottom] = dict(base_face, uv=strip, texture=spec["texture"])
				out.append(dict(common, **{"from": [round(v, 4) for v in lo3], "to": [round(v, 4) for v in hi3], "faces": el_faces}))
				seg = stop
	return out


def models_for_block(assets, block):
	state = assets.json("blockstates", block)
	found = []

	def walk(node):
		if isinstance(node, dict):
			for k, v in node.items():
				if k == "model" and isinstance(v, str):
					found.append(norm(v))
				else:
					walk(v)
		elif isinstance(node, list):
			for i in node:
				walk(i)
	walk(state or {})
	return sorted(set(found))


def main():
	vanilla, pack, blocks_file, log_file = sys.argv[1:5]
	assets = Assets(vanilla, pack)
	log = []
	done = set()
	for block in [b.strip() for b in open(blocks_file) if b.strip() and not b.startswith("#")]:
		for model in models_for_block(assets, block):
			if model in done:
				continue
			done.add(model)
			tex, elements, ao = resolve(assets, model)
			if not elements:
				continue
			new, changed = [], 0
			for el in elements:
				res = extrude(el, tex, assets)
				if res is None:
					new.append(el)
				else:
					new.extend(res)
					changed += 1
			if not changed:
				log.append("%s\tkept\tno flat plane to extrude" % model)
				continue
			if len(new) > MAX_ELEMENTS:
				log.append("%s\tkept\t%d boxes would be too heavy" % (model, len(new)))
				continue
			out = {"textures": tex, "elements": new}
			if ao is not None:
				out["ambientocclusion"] = ao
			ns, path = split(model)
			dest = os.path.join(pack, ns, "models", path + ".json")
			os.makedirs(os.path.dirname(dest), exist_ok=True)
			with open(dest, "w") as f:
				json.dump(out, f, separators=(",", ":"))
			log.append("%s\t3d\t%d planes -> %d boxes" % (model, changed, len(new)))
	with open(log_file, "w") as f:
		f.write("\n".join(log) + "\n")
	print(sum(1 for l in log if "\t3d\t" in l), "models made 3D;", sum(1 for l in log if "\tkept\t" in l), "kept")


if __name__ == "__main__":
	main()
