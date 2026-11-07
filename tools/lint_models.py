"""Lint a pack's block/item models against vanilla: undefined face texture variables,
texture paths that exist in neither the pack nor vanilla, and face UVs outside 0..16.

Usage: python3 -I lint_models.py VANILLA_ASSETS PACK_ASSETS
"""
import json
import os
import sys


def tree(root, sub, ext):
	out = {}
	for ns in os.listdir(root) if os.path.isdir(root) else []:
		base = os.path.join(root, ns, sub)
		for directory, _, names in os.walk(base):
			for name in names:
				if name.endswith(ext):
					rel = os.path.relpath(os.path.join(directory, name), base)[: -len(ext)]
					out[ns + ":" + rel] = os.path.join(directory, name)
	return out


def norm(ref):
	return ref if ":" in ref else "minecraft:" + ref


def main():
	vanilla, pack = sys.argv[1:3]
	models = tree(vanilla, "models", ".json")
	pack_models = tree(pack, "models", ".json")
	models.update(pack_models)
	textures = set(tree(vanilla, "textures", ".png")) | set(tree(pack, "textures", ".png"))
	cache = {}

	def load(name):
		path = models.get(name)
		if not path:
			return None
		try:
			return json.load(open(path, encoding="utf-8-sig"))
		except Exception as exc:
			print("BADJSON", name, exc)
			return None

	def resolve(name, depth=0):
		if name in cache:
			return cache[name]
		data = load(name) or {}
		tex, elements = {}, None
		if data.get("parent") and depth < 30:
			ptex, pel = resolve(norm(data["parent"]), depth + 1)
			tex.update(ptex)
			elements = pel
		tex.update(data.get("textures", {}))
		if "elements" in data:
			elements = data["elements"]
		cache[name] = (tex, elements)
		return cache[name]

	def lookup(tex, ref):
		seen = set()
		while isinstance(ref, str) and ref.startswith("#"):
			if ref in seen:
				return None
			seen.add(ref)
			ref = tex.get(ref[1:])
		if isinstance(ref, dict):
			ref = ref.get("sprite")
		return ref

	for name in sorted(pack_models):
		tex, elements = resolve(name)
		problems = []
		for key, value in tex.items():
			target = lookup(tex, value)
			if isinstance(target, str) and norm(target) not in textures and target != "missingno":
				problems.append("missing texture file " + target + " (#" + key + ")")
		for el in elements or []:
			for face, spec in (el.get("faces") or {}).items():
				ref = spec.get("texture", "")
				if lookup(tex, ref) is None:
					problems.append("face " + face + " uses undefined " + ref)
				uv = spec.get("uv")
				if uv and (min(uv) < 0 or max(uv) > 16):
					problems.append("face " + face + " uv out of range " + str(uv))
		if problems:
			print(name + ": " + "; ".join(sorted(set(problems))))


if __name__ == "__main__":
	main()
