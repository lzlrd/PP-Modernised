"""Download a Minecraft Java client (runtime, libraries, asset index) for headless testing.

Usage: python3 -I mcsetup.py VERSION_JSON RUNTIME_MANIFEST_URL DEST
Writes DEST/runtime, DEST/libraries, DEST/assets/indexes, DEST/client.jar and DEST/classpath.txt.
Sound asset objects are skipped; the game runs silently without them.
"""
import concurrent.futures
import hashlib
import json
import os
import stat
import sys
import urllib.request


def fetch(url, dest, sha1=None, executable=False):
	if os.path.exists(dest) and sha1:
		with open(dest, "rb") as f:
			if hashlib.sha1(f.read()).hexdigest() == sha1:
				return
	os.makedirs(os.path.dirname(dest), exist_ok=True)
	with urllib.request.urlopen(url) as resp:
		data = resp.read()
	if sha1 and hashlib.sha1(data).hexdigest() != sha1:
		raise RuntimeError("sha1 mismatch for " + url)
	with open(dest, "wb") as f:
		f.write(data)
	if executable:
		os.chmod(dest, os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def rules_allow(rules):
	if not rules:
		return True
	allowed = False
	for rule in rules:
		os_rule = rule.get("os")
		if rule.get("features"):
			continue
		matches = os_rule is None or os_rule.get("name") == "linux"
		if matches:
			allowed = rule["action"] == "allow"
	return allowed


def main():
	version_json, runtime_url, dest = sys.argv[1:4]
	version = json.load(open(version_json))
	jobs = []

	runtime = json.load(urllib.request.urlopen(runtime_url))
	for path, info in runtime["files"].items():
		target = os.path.join(dest, "runtime", path)
		if info["type"] == "directory":
			os.makedirs(target, exist_ok=True)
		elif info["type"] == "file":
			raw = info["downloads"]["raw"]
			jobs.append((raw["url"], target, raw["sha1"], info.get("executable", False)))
		elif info["type"] == "link":
			os.makedirs(os.path.dirname(target), exist_ok=True)
			if not os.path.lexists(target):
				os.symlink(info["target"], target)

	classpath = []
	for lib in version["libraries"]:
		if not rules_allow(lib.get("rules")):
			continue
		art = lib.get("downloads", {}).get("artifact")
		if art:
			target = os.path.join(dest, "libraries", art["path"])
			jobs.append((art["url"], target, art["sha1"], False))
			classpath.append(target)

	client = version["downloads"]["client"]
	jobs.append((client["url"], os.path.join(dest, "client.jar"), client["sha1"], False))
	classpath.append(os.path.join(dest, "client.jar"))

	index = version["assetIndex"]
	index_path = os.path.join(dest, "assets", "indexes", index["id"] + ".json")
	fetch(index["url"], index_path, index["sha1"])
	objects = json.load(open(index_path))["objects"]
	for name, obj in objects.items():
		if not name.startswith(("minecraft/sounds/", "minecraft/music/")):
			h = obj["hash"]
			jobs.append(("https://resources.download.minecraft.net/" + h[:2] + "/" + h,
				os.path.join(dest, "assets", "objects", h[:2], h), h, False))

	with concurrent.futures.ThreadPoolExecutor(8) as pool:
		for future in [pool.submit(fetch, *job) for job in jobs]:
			future.result()
	with open(os.path.join(dest, "classpath.txt"), "w") as f:
		f.write(":".join(classpath))
	print("downloaded", len(jobs), "files; main class", version["mainClass"])


if __name__ == "__main__":
	main()
