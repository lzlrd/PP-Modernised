"""Fix the load errors the 26.3 client reports for Pixel Perfection Legacy 26.3-97.2.

Usage: python3 -I fix_ppl.py PACK_ROOT VANILLA_ASSETS ASSET_INDEX_JSON LOG_FILE
"""
import json
import os
import re
import sys

from PIL import Image

VALID_PATH = re.compile(r"^[a-z0-9_.\-/]+$")
CUBE_PARENTS = {"block/cube", "block/cube_all", "block/cube_bottom_top", "block/cube_column", "block/cube_top",
	"minecraft:block/cube", "minecraft:block/cube_all", "minecraft:block/cube_bottom_top",
	"minecraft:block/cube_column", "minecraft:block/cube_top"}


def load(path):
	with open(path, encoding="utf-8-sig") as f:
		return json.load(f)


def save(path, data):
	with open(path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent="\t")
		f.write("\n")


def norm(ref):
	return ref if ":" in ref else "minecraft:" + ref


def main():
	pack, vanilla, index_file, log_file = sys.argv[1:5]
	assets = os.path.join(pack, "assets")
	log = []

	textures = set()
	for root in (assets, vanilla):
		for ns in os.listdir(root):
			base = os.path.join(root, ns, "textures")
			for directory, _, names in os.walk(base):
				for name in names:
					if name.endswith(".png"):
						textures.add(ns + ":" + os.path.relpath(os.path.join(directory, name), base)[:-4])

	# 1. Resource locations must be lowercase without spaces; the game ignores anything else.
	for directory, _, names in os.walk(assets):
		for name in names:
			rel = os.path.relpath(os.path.join(directory, name), assets).replace(os.sep, "/")
			if not VALID_PATH.match(rel) or name.lower() == "thumbs.db":
				os.remove(os.path.join(directory, name))
				log.append("removed invalid resource path " + rel)

	# 2. Models: drop "#missing" faces (zero-area Blockbench leftovers), repair particle paths,
	#    stop cube parents leaking unresolved variables, clamp out-of-range UVs.
	for ns in os.listdir(assets):
		base = os.path.join(assets, ns, "models")
		for directory, _, names in os.walk(base):
			for name in names:
				if not name.endswith(".json"):
					continue
				path = os.path.join(directory, name)
				rel = ns + ":" + os.path.relpath(path, base)[:-5]
				try:
					data = load(path)
				except Exception as exc:
					log.append("unreadable model " + rel + ": " + str(exc))
					continue
				changed = []
				elements = data.get("elements")
				if isinstance(elements, list):
					kept = []
					for el in elements:
						faces = el.get("faces") or {}
						for face in [f for f, s in faces.items() if s.get("texture") == "#missing"]:
							del faces[face]
							changed.append("dropped #missing face")
						for spec in faces.values():
							uv = spec.get("uv")
							if uv and (min(uv) < 0 or max(uv) > 16):
								spec["uv"] = [min(16, max(0, v)) for v in uv]
								changed.append("clamped uv")
						if faces:
							kept.append(el)
					if len(kept) != len(elements):
						changed.append("dropped empty elements")
					data["elements"] = kept
					if data.get("parent") in CUBE_PARENTS:
						data["parent"] = "block/block"
						changed.append("parent cube -> block/block")
				tex = data.get("textures") or {}
				particle = tex.get("particle")
				if isinstance(particle, str) and not particle.startswith("#") and norm(particle) not in textures:
					candidates = [v for k, v in tex.items() if k != "particle" and isinstance(v, str)
						and not v.startswith("#") and norm(v) in textures]
					if candidates:
						tex["particle"] = candidates[0]
						changed.append("particle " + particle + " -> " + candidates[0])
				if changed:
					save(path, data)
					log.append("model " + rel + ": " + ", ".join(sorted(set(changed))))

	# 3. Animations: frame indices past the end of the strip make the game reject them.
	for directory, _, names in os.walk(assets):
		for name in names:
			if not name.endswith(".png.mcmeta"):
				continue
			meta_path = os.path.join(directory, name)
			png = meta_path[: -len(".mcmeta")]
			rel = os.path.relpath(meta_path, assets)
			if not os.path.exists(png):
				os.remove(meta_path)
				log.append("removed orphan animation metadata " + rel)
				continue
			try:
				meta = load(meta_path)
			except Exception as exc:
				log.append("unreadable mcmeta " + rel + ": " + str(exc))
				continue
			anim = meta.get("animation")
			if not isinstance(anim, dict) or "frames" not in anim:
				continue
			w, h = Image.open(png).size
			fw = anim.get("width", min(w, h))
			fh = anim.get("height", fw)
			count = (w // fw) * (h // fh)
			frames = anim["frames"]
			valid = [f for f in frames if (f["index"] if isinstance(f, dict) else f) < count]
			if len(valid) != len(frames):
				anim["frames"] = valid
				save(meta_path, meta)
				log.append("animation " + rel + ": dropped " + str(len(frames) - len(valid)) + " frames past " + str(count))

	# 4. sounds.json entries pointing at sound files that exist nowhere.
	sounds_path = os.path.join(assets, "minecraft", "sounds.json")
	if os.path.exists(sounds_path):
		index = json.load(open(index_file))["objects"]
		available = {k[len("minecraft/sounds/"):-4] for k in index if k.startswith("minecraft/sounds/") and k.endswith(".ogg")}
		sdir = os.path.join(assets, "minecraft", "sounds")
		for directory, _, names in os.walk(sdir):
			for name in names:
				if name.endswith(".ogg"):
					available.add(os.path.relpath(os.path.join(directory, name), sdir)[:-4])
		sounds = load(sounds_path)
		for event, spec in list(sounds.items()):
			entries = spec.get("sounds", [])
			keep = []
			for entry in entries:
				name = entry if isinstance(entry, str) else entry.get("name")
				is_event = isinstance(entry, dict) and entry.get("type") == "event"
				clean = name.split(":", 1)[-1] if name else name
				if is_event or clean in available:
					keep.append(entry)
				else:
					log.append("sounds.json " + event + ": dropped missing file " + str(name))
			if len(keep) != len(entries):
				if keep:
					spec["sounds"] = keep
				else:
					del sounds[event]
					log.append("sounds.json: removed empty event " + event)
		save(sounds_path, sounds)

	with open(log_file, "a") as f:
		f.write("\n".join(log) + "\n")
	print(len(log), "fixes")


if __name__ == "__main__":
	main()
