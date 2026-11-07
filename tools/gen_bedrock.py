"""Finish the Bedrock/Geyser pack for PP Modernised from GeyserMC Thunder's conversion.

- Removes Java-only leftovers Thunder copies across (LabPBR _n/_s maps, OptiFine _e overlays,
  unused converted block geometry).
- Animates PPL's animated block textures with flipbook entries, or crops them to the first frame
  where Bedrock has no atlas tile to animate, so strips never render squashed.
- Adds Vibrant Visuals texture sets (heightmap + MERS) built from the Java LabPBR maps.
- Adds Geyser custom item mappings and icons for Dungeons and Taverns keys.
- Writes a manifest with stable UUIDs, the pbr capability and the pack version.

Usage: python3 -I gen_bedrock.py THUNDER_DIR JAVA_PACK_DIR THUNDER_TEXTURE_MAP BEDROCK_REF_DIR DNT_DATAPACK_DIR VERSION OUT_DIR
THUNDER_DIR is the unzipped Thunder .mcpack; OUT_DIR receives the finished pack folder,
geyser_custom_mappings/pp_modernised_dnt.json and a report.
"""
import json
import os
import re
import shutil
import sys
import uuid

import numpy as np
from PIL import Image

NS = uuid.UUID("6b1f2c3e-9a51-4c0e-8f7e-5d2a7c4b9e10")


def load_bedrock_json(path):
	text = open(path, encoding="utf-8-sig").read()
	return json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))


def texture_paths(entry):
	"""All texture paths referenced by a terrain_texture entry."""
	t = entry.get("textures")
	out = []
	items = t if isinstance(t, list) else [t]
	for it in items:
		if isinstance(it, str):
			out.append(it)
		elif isinstance(it, dict):
			if "path" in it:
				out.append(it["path"])
			for v in it.get("variations", []):
				out.append(v.get("path"))
	return [p for p in out if p]


def image_path(base):
	for ext in (".png", ".tga"):
		if os.path.exists(base + ext):
			return base + ext
	return None


def main():
	thunder, java, tex_map, ref, dnt, version, out = sys.argv[1:8]
	report = []
	pack = os.path.join(out, "PP-Modernised")
	if os.path.exists(pack):
		shutil.rmtree(pack)
	shutil.copytree(thunder, pack)
	tdir = os.path.join(pack, "textures")
	jtex = os.path.join(java, "assets", "minecraft", "textures")

	# 1. Drop Java-only leftovers.
	removed = 0
	for directory, _, names in os.walk(tdir):
		for name in names:
			if re.search(r"_(n|s|e|e_s)\.(png|tga)$", name) or name.endswith(".mcmeta"):
				os.remove(os.path.join(directory, name))
				removed += 1
	geo = os.path.join(pack, "models", "blocks")
	if os.path.isdir(geo):
		shutil.rmtree(geo)
	report.append("removed %d Java-only texture files and Thunder's unused converted block geometry" % removed)

	block_map = json.load(open(tex_map)).get("block", {})
	java_for = {}
	for jname in os.listdir(os.path.join(jtex, "block")):
		if not jname.endswith(".png") or re.search(r"_(n|s|e|e_s)\.png$", jname):
			continue
		j = jname[:-4]
		b = block_map.get(j, j)
		if isinstance(b, list):
			b = b[0]
		if isinstance(b, dict):
			b = next(iter(b.values()))
		java_for.setdefault(b, j)

	# 2. Animated strips.
	terrain = load_bedrock_json(os.path.join(ref, "terrain_texture.json"))["texture_data"]
	tiles_for = {}
	for key, entry in terrain.items():
		for p in texture_paths(entry):
			tiles_for.setdefault(p, []).append(key)
	flipbook = []
	animated, cropped = 0, 0
	bdir = os.path.join(tdir, "blocks")
	for name in sorted(os.listdir(bdir)):
		if not name.endswith((".png", ".tga")):
			continue
		path = os.path.join(bdir, name)
		img = Image.open(path)
		w, h = img.size
		if h <= w or h % w:
			continue
		b = name[:-4]
		rel = "textures/blocks/" + b
		tiles = tiles_for.get(rel, [])
		j = java_for.get(b)
		meta = {}
		if j and os.path.exists(os.path.join(jtex, "block", j + ".png.mcmeta")):
			meta = json.load(open(os.path.join(jtex, "block", j + ".png.mcmeta"), encoding="utf-8-sig")).get("animation", {})
		if tiles:
			frames = []
			for f in meta.get("frames", []):
				if isinstance(f, dict):
					frames.extend([f["index"]] * max(1, round(f.get("time", meta.get("frametime", 1)) / max(1, meta.get("frametime", 1)))))
				else:
					frames.append(f)
			frames = [f for f in frames if f < h // w]
			for tile in tiles:
				entry = {"flipbook_texture": rel, "atlas_tile": tile, "ticks_per_frame": int(meta.get("frametime", 1))}
				if frames:
					entry["frames"] = frames
				if meta.get("interpolate"):
					entry["blend_frames"] = True
				flipbook.append(entry)
			animated += 1
		else:
			img.crop((0, 0, w, w)).save(path)
			cropped += 1
	if flipbook:
		with open(os.path.join(tdir, "flipbook_textures.json"), "w") as f:
			json.dump(flipbook, f, indent="\t")
	report.append("animated %d block textures with flipbooks; cropped %d strips with no Bedrock atlas tile to their first frame" % (animated, cropped))

	# 3. Vibrant Visuals texture sets from LabPBR.
	sets = 0
	for b, j in sorted(java_for.items()):
		npath = os.path.join(jtex, "block", j + "_n.png")
		spath = os.path.join(jtex, "block", j + "_s.png")
		color = image_path(os.path.join(bdir, b))
		if not (color and os.path.exists(npath) and os.path.exists(spath)):
			continue
		n = np.asarray(Image.open(npath).convert("RGBA")).astype(np.float64)
		s = np.asarray(Image.open(spath).convert("RGBA")).astype(np.float64)
		cw, ch = Image.open(color).size
		if n.shape[1] != cw or n.shape[0] < ch:
			continue
		n, s = n[:ch], s[:ch]
		height = np.clip(n[..., 3], 0, 255)
		metal = np.where(s[..., 1] >= 230, 255, 0)
		emissive = np.where(s[..., 3] < 255, s[..., 3] / 254.0 * 255, 0)
		rough = (1 - s[..., 0] / 255.0) ** 2 * 255
		sss = np.where(s[..., 2] >= 65, (s[..., 2] - 65) / 190.0 * 255, 0)
		mers = np.stack([metal, emissive, rough, sss], axis=-1)
		Image.fromarray(height.astype(np.uint8), "L").save(os.path.join(bdir, b + "_heightmap.png"), optimize=True)
		Image.fromarray(np.clip(mers, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(bdir, b + "_mers.png"), optimize=True)
		with open(os.path.join(bdir, b + ".texture_set.json"), "w") as f:
			json.dump({"format_version": "1.21.30", "minecraft:texture_set": {
				"color": b, "metalness_emissive_roughness_subsurface": b + "_mers", "heightmap": b + "_heightmap"}}, f, indent="\t")
		sets += 1
	report.append("added %d Vibrant Visuals texture sets (heightmap + MERS)" % sets)

	# 4. Dungeons and Taverns keys -> Geyser custom items.
	keys = []
	for directory, _, names in os.walk(os.path.join(dnt, "data")):
		for name in names:
			if not name.endswith(".json") or "loot_table" not in directory:
				continue
			text = open(os.path.join(directory, name), encoding="utf-8-sig").read()
			for m in re.finditer(r'"name"\s*:\s*"minecraft:(ominous_trial_key|trial_key)".{0,400}?"floats"\s*:\s*\[\s*([0-9.]+)\s*\].{0,200}?"translate"\s*:\s*"item\.dnt\.([a-z_]+)"\s*,\s*"fallback"\s*:\s*"([^"]+)"', text, re.S):
				keys.append((m.group(1), float(m.group(2)), m.group(3), m.group(4)))
	keys = sorted(set(keys))
	items = {}
	item_tex = {}
	dnt_tex = os.path.join(java, "assets", "dnt", "textures", "item", "keys")
	for item, value, key, label in keys:
		src = os.path.join(dnt_tex, key + ".png")
		if not os.path.exists(src):
			report.append("no PPL texture for D&T key " + key)
			continue
		dest_rel = "textures/items/dnt/" + key
		os.makedirs(os.path.join(pack, "textures", "items", "dnt"), exist_ok=True)
		img = Image.open(src)
		if img.size[1] > img.size[0]:
			img = img.crop((0, 0, img.size[0], img.size[0]))
		img.save(os.path.join(pack, dest_rel + ".png"))
		ident = "ppm:dnt_" + key
		item_tex[ident.replace(":", ".")] = {"textures": dest_rel}
		items.setdefault("minecraft:" + item, []).append({
			"type": "definition",
			"model": "minecraft:" + item,
			"bedrock_identifier": ident,
			"display_name": label,
			"predicate": [
				{"type": "range_dispatch", "property": "custom_model_data", "threshold": value},
				{"type": "range_dispatch", "property": "custom_model_data", "threshold": value + 1, "expected": False},
			],
			"bedrock_options": {"icon": ident.replace(":", ".")},
		})
	if item_tex:
		path = os.path.join(tdir, "item_texture.json")
		data = json.load(open(path)) if os.path.exists(path) else {"resource_pack_name": "pp_modernised", "texture_name": "atlas.items", "texture_data": {}}
		data.setdefault("texture_data", {}).update(item_tex)
		with open(path, "w") as f:
			json.dump(data, f, indent="\t")
		os.makedirs(os.path.join(out, "geyser_custom_mappings"), exist_ok=True)
		with open(os.path.join(out, "geyser_custom_mappings", "pp_modernised_dnt.json"), "w") as f:
			json.dump({"format_version": 2, "items": items}, f, indent="\t")
	report.append("mapped %d Dungeons and Taverns keys to Geyser custom items" % sum(1 for defs in items.values() for v in defs if "dnt_" in v["bedrock_identifier"]))

	# 5. Manifest.
	ver = [int(x) for x in version.split(".")]
	manifest = {
		"format_version": 2,
		"header": {
			"name": "PP Modernised",
			"description": "XSSheep's Pixel Perfection for Bedrock via Geyser, with Vibrant Visuals PBR",
			"uuid": str(uuid.uuid5(NS, "pp-modernised-bedrock-header")),
			"version": ver,
			"min_engine_version": [1, 21, 120],
		},
		"modules": [{"type": "resources", "uuid": str(uuid.uuid5(NS, "pp-modernised-bedrock-resources")), "version": ver}],
		"capabilities": ["pbr"],
		"metadata": {"license": "CC-BY-SA-4.0", "authors": ["XSSheep", "Nova_Wostra", "Diab Neiroukh"],
			"generated_with": {"PackConverter": ["3.5.1"], "pp-modernised-tools": [version]}},
	}
	with open(os.path.join(pack, "manifest.json"), "w") as f:
		json.dump(manifest, f, indent="\t")
	for name in ("LICENSE.md", "CREDITS.md"):
		if os.path.exists(os.path.join(java, name)):
			shutil.copy2(os.path.join(java, name), os.path.join(pack, name))
	with open(os.path.join(out, "bedrock_report.txt"), "w") as f:
		f.write("\n".join(report) + "\n")
	print("\n".join(report))


if __name__ == "__main__":
	main()
