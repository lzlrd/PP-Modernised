"""Write a showcase datapack for in-game screenshots of PP Modernised.

Usage: python3 -I showcase.py BLOCKS_REPORT_JSON DATAPACK_DIR
Creates functions ppm:build (place everything), ppm:grid (every block in a grid) and
ppm:view_<name> (teleport the player to a camera position). Floor is the default flat world
(grass top at y=-61, player feet at y=-60).
"""
import json
import os
import sys

Y = -60
COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray",
	"cyan", "purple", "blue", "brown", "green", "red", "black"]
WOODS = ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "pale_oak", "poplar"]
FLOWERS = ["dandelion", "golden_dandelion", "poppy", "blue_orchid", "allium", "azure_bluet", "red_tulip", "orange_tulip",
	"white_tulip", "pink_tulip", "oxeye_daisy", "cornflower", "lily_of_the_valley", "wither_rose", "torchflower",
	"open_eyeblossom", "closed_eyeblossom"]
SAPLINGS = ["oak_sapling", "spruce_sapling", "birch_sapling", "jungle_sapling", "acacia_sapling", "dark_oak_sapling",
	"cherry_sapling", "pale_oak_sapling", "poplar_sapling", "dead_bush", "brown_mushroom", "red_mushroom",
	"crimson_fungus", "warped_fungus", "crimson_roots", "warped_roots"]


def main():
	report, out = sys.argv[1:3]
	blocks = json.load(open(report))
	fdir = os.path.join(out, "data", "ppm", "function")
	os.makedirs(fdir, exist_ok=True)
	with open(os.path.join(out, "pack.mcmeta"), "w") as f:
		json.dump({"pack": {"description": "PP Modernised showcase", "min_format": [121, 0], "max_format": [121, 0]}}, f)
	b = []
	add = b.append
	add("gamerule advance_time false")
	add("gamerule advance_weather false")
	add("time set 6000")
	add("weather clear")
	add("fill -2 %d -2 46 %d 30 air" % (Y, Y + 12))
	add("fill -2 %d -2 46 %d 30 grass_block" % (Y - 1, Y - 1))
	# Back wall with ladders, item frame row and hanging chains/lanterns.
	add("fill 0 %d 0 44 %d 0 stone_bricks" % (Y, Y + 6))
	for i in range(3):
		add("setblock %d %d 1 ladder[facing=south]" % (1, Y + i))
		add("setblock %d %d 1 ladder[facing=south]" % (2, Y + i))
	add("fill 4 %d 1 20 %d 1 stone_bricks" % (Y + 5, Y + 5))
	for i, chain in enumerate(["iron_chain", "copper_chain", "exposed_copper_chain", "weathered_copper_chain", "oxidized_copper_chain"]):
		add("setblock %d %d 2 %s" % (4 + 2 * i, Y + 4, chain))
		add("setblock %d %d 2 %s" % (4 + 2 * i, Y + 3, chain))
		add("fill %d %d 1 %d %d 1 stone_bricks" % (4 + 2 * i, Y + 4, 4 + 2 * i, Y + 5))
	for i, lantern in enumerate(["lantern[hanging=true]", "soul_lantern[hanging=true]", "copper_lantern[hanging=true]"]):
		add("setblock %d %d 2 %s" % (15 + 2 * i, Y + 4, lantern))
		add("fill %d %d 1 %d %d 1 stone_bricks" % (15 + 2 * i, Y + 4, 15 + 2 * i, Y + 5))
	add("setblock 15 %d 2 stone_bricks" % (Y + 5))
	# Logs (fixed blockstates), spawners, vaults, portal frame.
	x = 1
	for wood in WOODS + ["crimson", "warped"]:
		name = wood + ("_stem" if wood in ("crimson", "warped") else "_log")
		add("setblock %d %d 4 %s" % (x, Y, name))
		add("setblock %d %d 4 %s[axis=x]" % (x, Y + 1, name))
		x += 2
	specials = ["spawner", "trial_spawner", "trial_spawner[ominous=true,trial_spawner_state=active]", "vault",
		"vault[ominous=true,vault_state=active]", "conduit[waterlogged=false]", "end_portal_frame[eye=true]",
		"jack_o_lantern", "bookshelf", "pitcher_crop[age=3]", "sniffer_egg", "sniffer_egg[hatch=1]", "sniffer_egg[hatch=2]",
		"iron_bars", "copper_bars", "cactus_flower", "potted_red_mushroom", "melon_stem[age=2]", "pumpkin_stem[age=4]", "end_portal"]
	x = 1
	for s in specials:
		add("setblock %d %d 7 %s" % (x, Y, s))
		x += 2
	# Shulker boxes.
	x = 1
	for c in [""] + [c + "_" for c in COLOURS]:
		add("setblock %d %d 10 %sshulker_box[facing=up]" % (x, Y, c))
		x += 2
	# Flowers, saplings and their potted versions.
	x = 1
	for p in FLOWERS + SAPLINGS:
		add("setblock %d %d 13 %s" % (x, Y, p))
		add("setblock %d %d 15 potted_%s" % (x, Y, p))
		x += 2
	# Rails: a flat run and a ramp for each rail type, plus a lily pad pond.
	for i, rail in enumerate(["rail", "powered_rail[powered=true]", "detector_rail", "activator_rail"]):
		z = 18 + i * 2
		add("fill 1 %d %d 6 %d %d %s" % (Y, z, Y, z, rail.split("[")[0] + ("[shape=east_west" + (",powered=true]" if "powered=true" in rail else "]"))))
		add("setblock 7 %d %d stone_bricks" % (Y, z))
		add("setblock 7 %d %d %s" % (Y + 1, z, rail.split("[")[0] + "[shape=east_west" + (",powered=true]" if "powered=true" in rail else "]")))
		add("setblock 6 %d %d %s" % (Y, z, rail.split("[")[0] + "[shape=ascending_east" + (",powered=true]" if "powered=true" in rail else "]")))
	add("fill 12 %d 18 20 %d 24 water" % (Y - 1, Y - 1))
	for (px, pz) in [(13, 19), (15, 20), (17, 19), (14, 22), (18, 23), (16, 22)]:
		add("setblock %d %d %d lily_pad" % (px, Y, pz))
	# Material wall for shader (LabPBR) checks, facing south at z=32.
	mats = ["bricks", "stone_bricks", "cobblestone", "deepslate_tiles", "oak_planks", "spruce_log", "iron_block", "gold_block",
		"copper_block", "diamond_ore", "gold_ore", "deepslate_diamond_ore", "glowstone", "sea_lantern", "redstone_lamp[lit=true]",
		"quartz_block", "polished_andesite", "mossy_cobblestone", "netherite_block", "amethyst_block", "smooth_stone", "terracotta"]
	add("fill 0 %d 31 45 %d 40 air" % (Y, Y + 8))
	add("fill 0 %d 31 45 %d 40 grass_block" % (Y - 1, Y - 1))
	for i, m in enumerate(mats):
		add("fill %d %d 32 %d %d 32 %s" % (i * 2, Y, i * 2 + 1, Y + 2, m))
	for i in range(0, 44, 4):
		add("setblock %d %d 35 lantern" % (i, Y))
		add("setblock %d %d 33 torch" % (i + 2, Y))
	with open(os.path.join(fdir, "build.mcfunction"), "w") as f:
		f.write("\n".join(b) + "\n")
	# Every block, default state, on a stone floor. Fluids and portals excluded.
	skip = {"air", "cave_air", "void_air", "water", "lava", "bubble_column", "nether_portal", "end_gateway", "fire", "soul_fire",
		"structure_void", "moving_piston", "piston_head", "light"}
	names = sorted(k.split(":")[1] for k in blocks if k.split(":")[1] not in skip)
	cols = 32
	g = ["fill 60 %d 0 %d %d %d smooth_stone" % (Y - 1, 60 + cols * 2, Y - 1, 2 * ((len(names) + cols - 1) // cols)),
		"fill 60 %d 0 %d %d %d air" % (Y, 60 + cols * 2, Y + 3, 2 * ((len(names) + cols - 1) // cols))]
	for i, n in enumerate(names):
		g.append("setblock %d %d %d %s" % (60 + (i % cols) * 2, Y, (i // cols) * 2, n))
	with open(os.path.join(fdir, "grid.mcfunction"), "w") as f:
		f.write("\n".join(g) + "\n")
	views = {
		"wall": (10, Y + 2, 9, 180, 15),
		"specials": (20, Y + 3, 3, 0, 40),
		"shulkers": (17, Y + 4, 6, 0, 50),
		"flowers": (12, Y + 2, 10, 0, 25),
		"flowers_close": (6, Y + 1, 11.5, 0, 25),
		"rails": (6, Y + 3, 27, 160, 35),
		"pond": (16, Y + 4, 27, 180, 50),
		"logs": (12, Y + 2, 7.5, 180, 20),
		"pbr_left": (5, Y + 2, 37, 160, 12),
		"pbr_mid": (19, Y + 2, 37, 180, 12),
		"pbr_right": (35, Y + 2, 37, 200, 12),
	}
	rows = 2 * ((len(names) + cols - 1) // cols)
	for gy in range(0, rows, 16):
		for gx in range(0, cols * 2, 22):
			views["grid_%d_%d" % (gx, gy)] = (60 + gx + 11, Y + 9, gy - 2, 0, 55)
	for name, (vx, vy, vz, yaw, pitch) in views.items():
		with open(os.path.join(fdir, "view_%s.mcfunction" % name), "w") as f:
			f.write("tp @a %s %s %s %s %s\n" % (vx, vy, vz, yaw, pitch))
	with open(os.path.join(out, "views.txt"), "w") as f:
		f.write("\n".join(views) + "\n")
	print(len(b), "build commands;", len(names), "grid blocks;", len(views), "views")


if __name__ == "__main__":
	main()
