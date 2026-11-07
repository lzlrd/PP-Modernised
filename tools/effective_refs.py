"""Work out which block/item textures the game actually uses with a pack applied over vanilla.

Resolves the effective blockstates, item model definitions and models (pack overrides vanilla
by path), follows model parents and texture variables, and reports referenced textures that
neither the pack nor any of its own files provide (so they fall back to vanilla art).

Usage: python3 -I effective_refs.py VANILLA_ASSETS_ROOT PACK_ASSETS_ROOT OUT_DIR
Both roots are .../assets directories (containing namespaces).
"""
import json
import os
import sys


def load_tree(root, sub, ext=".json"):
	"""Return {namespace:path -> absolute file} for root/<ns>/<sub>/**."""
	out = {}
	if not os.path.isdir(root):
		return out
	for ns in os.listdir(root):
		base = os.path.join(root, ns, sub)
		for directory, _, names in os.walk(base):
			for name in names:
				if name.endswith(ext):
					rel = os.path.relpath(os.path.join(directory, name), base)[: -len(ext)]
					out[ns + ":" + rel.replace(os.sep, "/")] = os.path.join(directory, name)
	return out


def norm(ref):
	return ref if ":" in ref else "minecraft:" + ref


def read_json(path):
	try:
		with open(path, encoding="utf-8-sig") as f:
			return json.load(f)
	except Exception as exc:
		print("bad json", path, exc)
		return {}


def walk_models(node, found):
	"""Collect model references from blockstate or item definition JSON."""
	if isinstance(node, dict):
		for key, value in node.items():
			if key == "model" and isinstance(value, str):
				found.add(norm(value))
			elif key == "base" and isinstance(value, str) and node.get("type") in ("minecraft:special", "special"):
				found.add(norm(value))
			else:
				walk_models(value, found)
	elif isinstance(node, list):
		for item in node:
			walk_models(item, found)


def main():
	vanilla_root, pack_root, out_dir = sys.argv[1:4]
	models = load_tree(vanilla_root, "models")
	models.update(load_tree(pack_root, "models"))
	states = load_tree(vanilla_root, "blockstates")
	states.update(load_tree(pack_root, "blockstates"))
	items = load_tree(vanilla_root, "items")
	items.update(load_tree(pack_root, "items"))
	pack_models = load_tree(pack_root, "models")
	pack_tex = load_tree(pack_root, "textures", ".png")

	roots = set()
	for path in list(states.values()) + list(items.values()):
		walk_models(read_json(path), roots)

	cache = {}

	def resolve(name, depth=0):
		if name in cache:
			return cache[name]
		path = models.get(name)
		data = read_json(path) if path else {}
		textures = {}
		parent = data.get("parent")
		if parent and depth < 30:
			textures.update(resolve(norm(parent), depth + 1)[0])
		textures.update(data.get("textures", {}))
		cache[name] = (textures, path is not None)
		return cache[name]

	used = {}
	missing_models = set()
	for name in sorted(roots):
		textures, exists = resolve(name)
		if not exists and not name.startswith("minecraft:builtin"):
			missing_models.add(name)
		for key, value in textures.items():
			seen = set()
			while isinstance(value, str) and value.startswith("#") and value not in seen:
				seen.add(value)
				value = textures.get(value[1:], value)
			if isinstance(value, dict):
				value = value.get("sprite", "")
			if isinstance(value, str) and value and not value.startswith("#"):
				used.setdefault(norm(value), set()).add(name)

	fallback = sorted(t for t in used if t not in pack_tex)
	unused_pack = sorted(t for t in pack_tex if t.split(":", 1)[1].startswith(("block/", "item/")) and t not in used)
	os.makedirs(out_dir, exist_ok=True)
	with open(os.path.join(out_dir, "model_textures_fallback.txt"), "w") as f:
		for t in fallback:
			f.write(t + "\t" + ",".join(sorted(used[t])[:3]) + "\n")
	with open(os.path.join(out_dir, "pack_textures_unused.txt"), "w") as f:
		f.write("\n".join(unused_pack))
	with open(os.path.join(out_dir, "missing_models.txt"), "w") as f:
		f.write("\n".join(sorted(missing_models)))
	print("referenced textures:", len(used), "| falling back to vanilla:", len(fallback),
		"| pack block/item textures unused:", len(unused_pack), "| unresolved models:", len(missing_models),
		"| pack models:", len(pack_models))


if __name__ == "__main__":
	main()
