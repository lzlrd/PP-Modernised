"""Generate LabPBR 1.3 normal (_n) and specular (_s) maps for PP Modernised.

Heights come from each texture's luminance, scaled per material. They feed the normal map,
parallax occlusion (POM) through the _n alpha, and a cavity AO term. Specular values come from a
material table keyed on the texture name, with per-pixel detection for metal, gem and flame
pixels. Existing PPL _s maps only carry emission, so their alpha is kept and the other channels
are filled in.

Writes a JSON material report so the same data can drive Bedrock Vibrant Visuals texture sets.

Usage: python3 -I gen_pbr.py PACK_ASSETS REPORT_JSON
"""
import colorsys
import json
import os
import re
import sys

import numpy as np
from PIL import Image

# name regex -> (smoothness 0-255, F0 0-229 or metal id, porosity 0-64 or SSS 65-255, POM depth 0-1)
MATERIALS = [
	(r"(^|/)(water|lava)_(still|flow)$", None),  # Shaders draw fluids themselves.
	(r"glass|^block/ice$|packed_ice|blue_ice|frosted_ice", (235, 10, 0, 0.0)),
	(r"slime|honey_block", (215, 10, 230, 0.1)),
	(r"leaves|leaf_litter|vine|grass$|short_grass|tall_grass|fern|seagrass|kelp|lily_pad|azalea|moss|sapling|"
		r"flower|tulip|orchid|allium|bluet|daisy|cornflower|lily_of_the_valley|rose|dandelion|poppy|petals|"
		r"wildflowers|bush|roots|sprouts|dripleaf|spore_blossom|cactus|bamboo|sugar_cane|wheat|carrots|potatoes|"
		r"beetroots|crop|stem|eyeblossom|torchflower|pitcher|hanging_roots|cave_vines|weeping|twisting|mangrove_propagule|"
		r"chorus_flower|glow_lichen|sculk_vein|shrub|straw", (110, 10, 180, 0.35)),
	(r"snow|powder_snow", (90, 10, 150, 0.3)),
	(r"wool|carpet|cushion", (20, 10, 60, 0.4)),
	(r"concrete_powder|^block/(sand|red_sand|suspicious_sand)|gravel|clay$|mud$|soul_sand|soul_soil", (25, 10, 50, 0.45)),
	(r"dirt|farmland|podzol|mycelium|grass_block|rooted_dirt|coarse", (25, 10, 45, 0.5)),
	(r"glazed_terracotta", (210, 10, 5, 0.12)),
	(r"concrete", (115, 10, 8, 0.12)),
	(r"terracotta", (55, 10, 20, 0.3)),
	(r"netherite_block|netherite", (175, 255, 0, 0.3)),
	(r"gold_block|^block/raw_gold_block", (195, 231, 0, 0.3)),
	(r"iron_block|iron_bars|iron_door|iron_trapdoor|anvil|cauldron|hopper|chain|heavy_core|^block/iron", (165, 230, 0, 0.3)),
	(r"oxidized_.*copper|oxidized_cut", (70, 10, 10, 0.35)),
	(r"copper|lightning_rod", (150, 234, 0, 0.3)),
	(r"diamond_block|emerald_block|amethyst|budding|quartz_bricks|^block/quartz", (205, 40, 0, 0.2)),
	(r"_ore$|_ore\d*$|ancient_debris", (70, 10, 15, 0.75)),
	(r"obsidian", (200, 12, 0, 0.35)),
	(r"polished|smooth_|chiseled|cut_", (140, 10, 8, 0.3)),
	(r"cobble|mossy_cobblestone|cobbled", (30, 10, 25, 1.0)),
	(r"brick|tiles|tuff_bricks|prismarine_bricks|nether_bricks|end_stone_bricks|mud_bricks|resin_bricks", (45, 10, 22, 0.9)),
	(r"stripped_", (90, 10, 28, 0.5)),
	(r"_log|_stem|_wood|_hyphae|bamboo_block", (55, 10, 30, 0.8)),
	(r"planks|bookshelf|barrel|crafting_table|cartography|fletching|smithing|loom|lectern|composter|_door|_trapdoor|"
		r"scaffolding|beehive|chest|_sign|shelf", (75, 10, 25, 0.5)),
	(r"deepslate|blackstone|basalt|tuff|calcite|dripstone|sulfur", (50, 10, 15, 0.7)),
	(r"stone|andesite|diorite|granite|netherrack|end_stone|purpur|prismarine|sandstone|magma|bedrock", (45, 10, 18, 0.7)),
	(r"sea_lantern|froglight|shroomlight|glowstone|redstone_lamp", (160, 10, 0, 0.25)),
	(r"sculk", (120, 10, 120, 0.4)),
]
DEFAULT = (60, 10, 10, 0.5)

FULL_GLOW = re.compile(r"glowstone|sea_lantern|shroomlight|froglight|redstone_lamp_on|^block/lava|magma|beacon|end_rod|"
	r"respawn_anchor_top|crying_obsidian|lit_|_on$|nether_portal|conduit|amethyst_cluster")
FLAME = re.compile(r"torch|lantern|campfire|fire|furnace_front_on|smoker_front_on|blast_furnace_front_on|candle.*lit|"
	r"jack_o_lantern|vault_front_on|vault_front_ejecting|trial_spawner_side_active|trial_spawner_top_active|creaking_heart.*awake|"
	r"cave_vines.*lit|glow_berries|firefly|copper_bulb_lit|sculk_catalyst_top_bloom|sculk_catalyst_side_bloom")
METALLIC_ITEM = re.compile(r"(iron|gold|golden|copper|netherite|chain|chainmail)")
GEM_ITEM = re.compile(r"diamond|emerald|amethyst|quartz|prismarine_crystals|echo_shard")


def material(key):
	for pattern, values in MATERIALS:
		if re.search(pattern, key):
			return values
	return DEFAULT


def hsv(arr):
	rgb = arr[..., :3].reshape(-1, 3) / 255.0
	out = np.array([colorsys.rgb_to_hsv(*c) for c in rgb])
	return out.reshape(arr.shape[:2] + (3,))


def frames_of(img):
	h, w = img.shape[:2]
	if h > w and h % w == 0:
		return [img[i * w:(i + 1) * w] for i in range(h // w)]
	return [img]


def heights(rgba, tiling):
	"""Normalised height 0..1 from luminance, per frame."""
	lum = (0.2126 * rgba[..., 0] + 0.7152 * rgba[..., 1] + 0.0722 * rgba[..., 2]) / 255.0
	opaque = rgba[..., 3] > 16
	if opaque.sum() < 2:
		return np.ones(lum.shape)
	lo, hi = np.percentile(lum[opaque], 3), np.percentile(lum[opaque], 97)
	h = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
	h[~opaque] = 1.0
	return h


def groove_heights(rgba):
	"""Bricks and tiles: the smaller of two colour clusters is mortar, so it sits low."""
	opaque = rgba[..., 3] > 16
	cols = rgba[..., :3][opaque]
	if len(cols) < 8:
		return None
	lum = cols @ np.array([0.2126, 0.7152, 0.0722])
	centres = np.array([cols[lum <= np.median(lum)].mean(axis=0), cols[lum > np.median(lum)].mean(axis=0)])
	for _ in range(8):
		d = ((cols[:, None, :] - centres[None]) ** 2).sum(-1)
		lab = d.argmin(1)
		for k in (0, 1):
			if (lab == k).any():
				centres[k] = cols[lab == k].mean(axis=0)
	counts = np.bincount(lab, minlength=2)
	mortar = int(np.argmin(counts))
	if counts[mortar] < 0.08 * len(cols) or counts[mortar] > 0.45 * len(cols):
		return None
	full = np.zeros(rgba.shape[:2], int) - 1
	full[opaque] = lab
	h = heights(rgba, True)
	h = 0.55 + 0.45 * h
	h[full == mortar] = 0.0
	return h


def normals(h, depth, tiling):
	mode = "wrap" if tiling else "edge"
	p = np.pad(h, 1, mode=mode)
	dx = (p[1:-1, 2:] - p[1:-1, :-2]) * 0.5
	dy = (p[2:, 1:-1] - p[:-2, 1:-1]) * 0.5
	k = 2.2 * depth
	nx, ny = -dx * k, -dy * k
	nz = np.ones_like(h)
	n = np.sqrt(nx * nx + ny * ny + nz * nz)
	nx, ny = nx / n, ny / n
	blur = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] + h) / 5.0
	ao = 1.0 - np.clip((blur - h) * 2.5 * depth, 0, 0.45)
	return nx, ny, ao


def process(path, key, kind, existing_s, report):
	img = np.asarray(Image.open(path).convert("RGBA")).astype(np.float64)
	if kind == "block":
		mat = material(key)
	elif kind == "item":
		mat = (150, 230, 0, 0.35) if METALLIC_ITEM.search(key) else (190, 40, 0, 0.3) if GEM_ITEM.search(key) else (70, 10, 5, 0.35)
	else:
		mat = (165, 230, 0, 0.3) if "equipment" in key and METALLIC_ITEM.search(key) else (45, 10, 0, 0.3)
	if mat is None:
		return False
	smooth, f0, poro, depth = mat
	tiling = kind == "block"
	n_frames, s_frames = [], []
	for fr in frames_of(img):
		alpha = fr[..., 3]
		opaque = alpha > 16
		h = groove_heights(fr) if kind == "block" and re.search(r"brick|tiles", key) else None
		if h is None:
			h = heights(fr, tiling)
		nx, ny, ao = normals(h, depth, tiling)
		n_img = np.zeros(fr.shape)
		n_img[..., 0] = (nx * 0.5 + 0.5) * 255
		n_img[..., 1] = (ny * 0.5 + 0.5) * 255
		n_img[..., 2] = ao * 255
		n_img[..., 3] = np.clip(255 - depth * 180 * (1 - h), 1, 255)
		n_img[~opaque] = (128, 128, 255, 255)
		s_img = np.zeros(fr.shape)
		hv = hsv(fr)
		sat, val, hue = hv[..., 1], hv[..., 2], hv[..., 0]
		s_img[..., 0] = smooth
		s_img[..., 1] = f0
		s_img[..., 2] = poro
		emit = np.zeros(h.shape)
		# Metal blocks: only plausibly metallic pixels get the metal id; the rest stay dielectric.
		if f0 >= 230:
			if f0 == 231:
				metal = (val > 0.35) & ((sat < 0.25) | ((hue > 0.07) & (hue < 0.18)))
			elif f0 == 234:
				metal = (val > 0.3) & (((hue < 0.1) | (hue > 0.95)) & (sat > 0.25) | (sat < 0.2))
			else:
				metal = (val > 0.25) & (sat < 0.35)
			s_img[..., 1] = np.where(metal, f0, 10)
			s_img[..., 0] = np.where(metal, smooth, 60)
		# Ore flecks: gold and copper shine as metal; gems are glossy dielectrics.
		if re.search(r"_ore\d*$", key):
			fleck = (sat > 0.35) & (val > 0.45)
			if "gold" in key:
				s_img[..., 1] = np.where(fleck, 231, s_img[..., 1])
			elif "copper" in key:
				s_img[..., 1] = np.where(fleck, 234, s_img[..., 1])
			elif re.search("diamond|emerald|lapis|redstone|quartz|amethyst", key):
				s_img[..., 1] = np.where(fleck, 40, s_img[..., 1])
			s_img[..., 0] = np.where(fleck, 200, s_img[..., 0])
			n_img[..., 3] = np.where(fleck, 255, n_img[..., 3])
		# Emission.
		if kind == "block" and FULL_GLOW.search(key):
			emit = np.clip((val - 0.35) / 0.65, 0, 1) * 254
		elif FLAME.search(key):
			warm = ((hue < 0.17) | (hue > 0.95)) & (sat > 0.3) & (val > 0.6)
			soul = (hue > 0.42) & (hue < 0.6) & (sat > 0.3) & (val > 0.55) & ("soul" in key)
			emit = np.where(warm | soul, np.clip(val, 0, 1) * 230, 0)
		s_img[..., 3] = np.where(emit > 0, np.clip(emit, 1, 254), 0)
		s_img[~opaque] = (0, 0, 0, 0)
		n_frames.append(n_img)
		s_frames.append(s_img)
	n_all = np.concatenate(n_frames, axis=0)
	s_all = np.concatenate(s_frames, axis=0)
	if existing_s is not None:
		old = np.asarray(Image.open(existing_s).convert("RGBA")).astype(np.float64)
		if old.shape == s_all.shape:
			s_all[..., 3] = np.maximum(old[..., 3], s_all[..., 3])
	base = path[:-4]
	Image.fromarray(np.clip(n_all, 0, 255).astype(np.uint8), "RGBA").save(base + "_n.png", optimize=True)
	Image.fromarray(np.clip(s_all, 0, 255).astype(np.uint8), "RGBA").save(base + "_s.png", optimize=True)
	meta = path + ".mcmeta"
	if os.path.exists(meta):
		for suffix in ("_n.png.mcmeta", "_s.png.mcmeta"):
			with open(meta, encoding="utf-8-sig") as src, open(base + suffix, "w") as dst:
				dst.write(src.read())
	report[key] = {"smoothness": smooth, "f0": f0, "porosity_sss": poro, "depth": depth,
		"emissive": bool((s_all[..., 3] > 0).any())}
	return True


def main():
	assets, report_path = sys.argv[1:3]
	report = {}
	count = 0
	for ns in sorted(os.listdir(assets)):
		troot = os.path.join(assets, ns, "textures")
		for kind in ("block", "item", "entity"):
			base = os.path.join(troot, kind)
			for directory, _, names in os.walk(base):
				for name in sorted(names):
					if not name.endswith(".png") or re.search(r"_(n|s|e|e_s|n_s)\.png$", name):
						continue
					path = os.path.join(directory, name)
					key = ns + ":" + os.path.relpath(path, troot)[:-4] if ns != "minecraft" else os.path.relpath(path, troot)[:-4]
					existing = path[:-4] + "_s.png"
					try:
						if process(path, key, kind, existing if os.path.exists(existing) else None, report):
							count += 1
					except Exception as exc:
						print("failed", key, exc)
	with open(report_path, "w") as f:
		json.dump(report, f, indent=1, sort_keys=True)
	print(count, "textures got LabPBR maps")


if __name__ == "__main__":
	main()
