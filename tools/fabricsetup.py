"""Fetch the Fabric loader libraries for a Minecraft version and write a Fabric classpath.

Usage: python3 -I fabricsetup.py MC_VERSION LOADER_VERSION CLIENT_DIR
Appends Fabric libraries to CLIENT_DIR/libraries and writes CLIENT_DIR/classpath_fabric.txt
(Fabric libraries first, then the vanilla classpath minus libraries Fabric replaces).
"""
import json
import os
import sys
import urllib.request


def maven_path(name):
	group, artifact, version = name.split(":")[:3]
	return "/".join(group.split(".") + [artifact, version, "%s-%s.jar" % (artifact, version)])


def main():
	mc, loader, client = sys.argv[1:4]
	url = "https://meta.fabricmc.net/v2/versions/loader/%s/%s/profile/json" % (mc, loader)
	profile = json.load(urllib.request.urlopen(url))
	paths = []
	names = set()
	for lib in profile["libraries"]:
		rel = maven_path(lib["name"])
		dest = os.path.join(client, "libraries", rel)
		if not os.path.exists(dest):
			os.makedirs(os.path.dirname(dest), exist_ok=True)
			base = lib.get("url", "https://maven.fabricmc.net/")
			with urllib.request.urlopen(base.rstrip("/") + "/" + rel) as resp, open(dest, "wb") as f:
				f.write(resp.read())
		paths.append(dest)
		names.add(":".join(lib["name"].split(":")[:2]))
	vanilla = open(os.path.join(client, "classpath.txt")).read().split(":")
	# Drop vanilla copies of libraries Fabric ships newer versions of (e.g. ASM).
	keep = []
	for p in vanilla:
		parts = p.split("/libraries/")[-1].split("/")
		ga = ".".join(parts[:-3]) + ":" + parts[-3] if len(parts) > 3 else ""
		if ga not in names:
			keep.append(p)
	with open(os.path.join(client, "classpath_fabric.txt"), "w") as f:
		f.write(":".join(paths + keep))
	print("main class", profile["mainClass"], "|", len(paths), "fabric libs")


if __name__ == "__main__":
	main()
