"""Generate the 26.3 textures PP Modernised lacks, from the pack's own art where possible.

Usage: python3 -I gen_missing.py VANILLA_TEXTURES PACK_TEXTURES REPORT_FILE
Writes PNGs (and vanilla animation .mcmeta where the target is animated) into PACK_TEXTURES and a
tab-separated report: target, method, source/refs, quality note.
"""
import json
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texgen as tg  # noqa: E402

COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray",
	"cyan", "purple", "blue", "brown", "green", "red", "black"]


def recipes(V, P):
	"""(target, method, args) for everything worth generating."""
	r = []
	for c in COLOURS:
		r.append(("block/%s_shulker_box.png" % c, "geo", ["entity/shulker/shulker_%s.png" % c]))
	r.append(("block/shulker_box.png", "geo", ["entity/shulker/shulker.png"]))
	r.append(("block/bamboo_fence_gate_particle.png", "geo", ["block/bamboo_fence_gate.png"]))
	r.append(("block/shelf_mushroom_particle.png", "geo", ["block/shelf_mushroom_stage1.png", "block/shelf_mushroom_stage0.png"]))
	r.append(("block/wildflowers_stem.png", "geo", ["block/pink_petals_stem.png"]))
	r.append(("block/conduit.png", "geo", ["entity/conduit/base.png", "entity/conduit/cage.png"]))
	r.append(("block/redstone_dust_overlay.png", "copy_vanilla_if_blank", []))
	r.append(("block/open_eyeblossom_emissive.png", "hue_mask", ["block/open_eyeblossom.png"]))
	r.append(("block/tripwire.png", "palette", ["item/string.png", "block/tripwire_hook.png"]))
	r.append(("block/end_portal_glow.png", "end_portal_glow", ["block/end_portal_frame_eye.png", "environment/end_sky.png"]))
	r.append(("item/leather_chestplate_overlay.png", "geo_or_palette", ["item/leather_chestplate.png"],
		["item/leather_helmet_overlay.png", "item/leather_leggings_overlay.png", "item/leather_boots_overlay.png"]))
	for i in range(16):
		r.append(("item/light_%02d.png" % i, "palette", ["block/glowstone.png", "block/redstone_lamp_on.png"]))
	# Entities.
	r.append(("entity/equipment/humanoid_baby/turtle_scute.png", "geo", ["entity/equipment/humanoid/turtle_scute.png"]))
	r.append(("entity/wolf/wolf_collar_baby.png", "geo_or_palette", ["entity/wolf/wolf_collar.png"], ["entity/wolf/wolf_collar.png"]))
	r.append(("entity/shield/flow.png", "geo", ["entity/banner/flow.png"]))
	r.append(("entity/shield/guster.png", "geo_or_palette", ["entity/banner/guster.png"], ["entity/banner/guster.png"]))
	r.append(("entity/projectiles/wind_charge.png", "palette", ["entity/breeze/breeze.png"]))
	r.append(("colormap/dry_foliage.png", "dry_foliage", ["colormap/foliage.png"]))
	r.append(("environment/celestial/end_flash.png", "palette", ["environment/end_sky.png"]))
	# Trim palettes: 8-step ramps sampled from the pack's own material textures.
	trim_refs = {
		"amethyst": ["item/amethyst_shard.png", "block/amethyst_block.png"],
		"copper": ["item/copper_ingot.png", "block/copper_block.png"],
		"copper_darker": ["item/copper_ingot.png", "block/copper_block.png"],
		"diamond": ["item/diamond.png", "block/diamond_block.png"],
		"diamond_darker": ["item/diamond.png", "block/diamond_block.png"],
		"emerald": ["item/emerald.png", "block/emerald_block.png"],
		"gold": ["item/gold_ingot.png", "block/gold_block.png"],
		"gold_darker": ["item/gold_ingot.png", "block/gold_block.png"],
		"iron": ["item/iron_ingot.png", "block/iron_block.png"],
		"iron_darker": ["item/iron_ingot.png", "block/iron_block.png"],
		"lapis": ["item/lapis_lazuli.png", "block/lapis_block.png"],
		"netherite": ["item/netherite_ingot.png", "block/netherite_block.png"],
		"netherite_darker": ["item/netherite_ingot.png", "block/netherite_block.png"],
		"quartz": ["item/quartz.png", "block/quartz_block_side.png"],
		"redstone": ["item/redstone.png", "block/redstone_block.png"],
		"resin": ["item/resin_brick.png", "block/resin_block.png"],
	}
	for name, refs in trim_refs.items():
		r.append(("palettes/trim/%s.png" % name, "trim_palette", refs))
	# Particles: vanilla shapes in the palette of the matching pack texture.
	groups = [
		("cherry_", 12, ["block/cherry_leaves.png"]),
		("pale_oak_", 12, ["block/pale_oak_leaves.png"]),
		("leaf_", 12, ["block/oak_leaves.png"]),
		("soul_", 11, ["block/soul_fire_0.png"]),
		("sculk_soul_", 11, ["block/sculk.png"]),
		("sculk_charge_", 7, ["block/sculk.png"]),
		("sculk_charge_pop_", 4, ["block/sculk.png"]),
	]
	for prefix, count, refs in groups:
		for i in range(count):
			r.append(("particle/%s%d.png" % (prefix, i), "palette", refs))
	for colour in ("orange", "red", "yellow"):
		for i in range(1, 5):
			r.append(("particle/%s_poplar_%d.png" % (colour, i), "palette", ["block/%s_poplar_leaves.png" % colour]))
	for prefix in ("geyser_base_", "geyser_plume_", "geyser_poof_", "noxious_gas_"):
		for i in range(1, 9):
			r.append(("particle/%s%02d.png" % (prefix, i), "palette", ["block/sulfur.png", "block/potent_sulfur.png"]))
	r.append(("particle/sulfur_cube_goo.png", "palette", ["block/sulfur.png"]))
	for i in range(5):
		r.append(("particle/trial_spawner_detection_%d.png" % i, "palette", ["block/trial_spawner_side_active.png"]))
		r.append(("particle/trial_spawner_detection_ominous_%d.png" % i, "palette", ["block/trial_spawner_side_active_ominous.png"]))
	r.append(("particle/vault_connection.png", "palette", ["block/vault_front_on.png"]))
	r.append(("particle/infested.png", "palette", ["entity/silverfish/silverfish.png", "entity/silverfish.png", "entity/endermite.png"]))
	r.append(("particle/glow.png", "palette", ["item/glow_ink_sac.png"]))
	r.append(("particle/goldheart_0.png", "palette", ["item/gold_ingot.png"]))
	r.append(("particle/goldheart_1.png", "palette", ["item/gold_ingot.png"]))
	r.append(("particle/goldheart_2.png", "palette", ["item/gold_ingot.png"]))
	# GUI: widgets and icons in the palette of the pack's own widgets.
	button = ["gui/sprites/widget/button.png"]
	button_hi = ["gui/sprites/widget/button_highlighted.png"]
	button_off = ["gui/sprites/widget/button_disabled.png"]
	for base, refs in (("widget/realms_button", None), ("dialog/warning_button", None),
			("social_interactions/report_button", None), ("friends/button", None)):
		r.append(("gui/sprites/%s.png" % base, "palette", button))
		r.append(("gui/sprites/%s_highlighted.png" % base, "palette", button_hi))
		r.append(("gui/sprites/%s_disabled.png" % base, "palette", button_off))
	r.append(("gui/sprites/widget/scroller.png", "palette", ["gui/sprites/widget/slider_handle.png"]))
	r.append(("gui/sprites/widget/scroller_background.png", "palette", ["gui/sprites/widget/slider.png"]))
	r.append(("gui/sprites/widget/preedit.png", "palette", ["gui/sprites/widget/text_field.png"]))
	for name in ("accept", "accept_highlighted", "reject", "reject_highlighted", "cancel", "remove",
			"send_request", "friends", "loading", "list_separator_top", "background", "background_dark", "toast_background"):
		r.append(("gui/sprites/friends/%s.png" % name, "palette", button if "background" not in name else ["gui/sprites/toast/advancement.png"]))
	r.append(("gui/sprites/popup/background.png", "palette", ["gui/sprites/toast/advancement.png"]))
	for name in ("accessibility", "chat_modified", "checkmark", "info", "language", "link", "link_highlighted",
			"music_notes", "new_realm", "unseen_notification", "video_link", "video_link_highlighted"):
		r.append(("gui/sprites/icon/%s.png" % name, "palette", ["gui/sprites/icon/search.png", "gui/sprites/icon/invite.png"]))
	for name in ("bug", "player_reporting", "social_interactions"):
		r.append(("gui/sprites/pause_menu/%s.png" % name, "palette", ["gui/sprites/icon/search.png", "gui/sprites/icon/invite.png"]))
	r.append(("gui/sprites/hud/air_empty.png", "palette", ["gui/sprites/hud/air.png"]))
	for name in ("locator_bar_arrow_down", "locator_bar_arrow_up", "locator_bar_background"):
		r.append(("gui/sprites/hud/%s.png" % name, "palette", ["gui/sprites/hud/experience_bar_background.png"]))
	for name in ("bowtie", "default_0", "default_1", "default_2", "default_3"):
		r.append(("gui/sprites/hud/locator_bar_dot/%s.png" % name, "palette", ["gui/sprites/hud/experience_bar_progress.png"]))
	r.append(("gui/sprites/gamemode_switcher/selection.png", "palette", ["gui/sprites/widget/slot_frame.png"]))
	r.append(("gui/sprites/gamemode_switcher/slot.png", "palette", ["gui/sprites/widget/slot_frame.png"]))
	r.append(("gui/container/gamemode_switcher.png", "palette", ["gui/container/inventory.png"]))
	r.append(("gui/sprites/container/bundle/slot_background.png", "palette", ["gui/container/inventory.png"]))
	r.append(("gui/sprites/container/loom/error.png", "palette", ["gui/container/loom.png"]))
	for name in ("nautilus_armor", "nautilus_armor_inventory", "spear"):
		r.append(("gui/sprites/container/slot/%s.png" % name, "palette", ["gui/sprites/container/slot/horse_armor.png", "gui/sprites/container/slot/sword.png"]))
	for name in ("menu_background", "menu_list_background", "inworld_menu_background", "inworld_menu_list_background",
			"tab_header_background", "header_separator", "footer_separator", "inworld_header_separator", "inworld_footer_separator"):
		r.append(("gui/%s.png" % name, "palette", ["gui/options_background.png"]))
	r.append(("gui/hanging_signs/pale_oak.png", "geo_or_palette", ["block/stripped_pale_oak_log.png"], ["block/stripped_pale_oak_log.png"]))
	return r


def first_existing(root, paths):
	for p in paths:
		if os.path.exists(os.path.join(root, p)):
			return p
	return None


def main():
	V, P, report = sys.argv[1:4]
	rows = []
	for item in recipes(V, P):
		target, method, args = item[0], item[1], item[2]
		extra = item[3] if len(item) > 3 else []
		vpath = os.path.join(V, target)
		out = os.path.join(P, target)
		if os.path.exists(out):
			continue
		if not os.path.exists(vpath) and method != "end_portal_glow":
			rows.append((target, "skip", "", "no vanilla texture at this path"))
			continue
		vt = tg.load(vpath) if os.path.exists(vpath) else None
		result, how, note = None, method, ""
		if method in ("geo", "geo_or_palette"):
			for src in args:
				vs_path, ps_path = os.path.join(V, src), os.path.join(P, src)
				if not (os.path.exists(vs_path) and os.path.exists(ps_path)):
					continue
				vs = tg.load(vs_path)
				if vt.shape[0] * vt.shape[1] > 64 * 64 or vs.shape[0] * vs.shape[1] > 128 * 128:
					continue
				assign, cov, keys = tg.correspond(vs, vt)
				if cov >= 0.7:
					result = tg.apply_geo(tg.load(ps_path), vs.shape, assign, keys)
					how, note = "geo", "%s (%.0f%% exact)" % (src, cov * 100)
					break
			if result is None and method == "geo_or_palette":
				refs = [tg.load(os.path.join(P, p)) for p in extra if os.path.exists(os.path.join(P, p))]
				if refs:
					result, how, note = tg.palette(vt, refs), "palette", ",".join(extra)
		elif method == "palette":
			refs = [tg.load(os.path.join(P, p)) for p in args if os.path.exists(os.path.join(P, p))]
			if refs:
				result, note = tg.palette(vt, refs), ",".join(p for p in args if os.path.exists(os.path.join(P, p)))
		elif method == "trim_palette":
			refs = [tg.load(os.path.join(P, p)) for p in args if os.path.exists(os.path.join(P, p))]
			if refs:
				pal = tg.ref_palette(refs)
				# Match the vanilla ramp's luminance at each step from the pack palette.
				lum_v = tg.luminance(vt[..., :3].astype(np.float64))
				lum_p = tg.luminance(pal.astype(np.float64))
				result = vt.copy()
				for (y, x), lv in np.ndenumerate(lum_v):
					result[y, x, :3] = pal[np.argmin(np.abs(lum_p - lv))]
				note = ",".join(args)
		elif method == "hue_mask":
			src = os.path.join(P, args[0])
			if os.path.exists(src):
				pack = tg.load(src)
				em = vt[vt[..., 3] > 0][:, :3].astype(np.float64)
				ref_hsv = tg.to_hsv(em)
				hsv = tg.to_hsv(pack[..., :3].astype(np.float64))
				hue_ok = np.zeros(pack.shape[:2], bool)
				for h in np.unique(np.round(ref_hsv[:, 0], 2)):
					hue_ok |= np.abs(((hsv[..., 0] - h + 0.5) % 1.0) - 0.5) < 0.04
				mask = hue_ok & (hsv[..., 2] >= np.percentile(ref_hsv[:, 2], 10) * 0.9) & (pack[..., 3] > 0)
				result = np.where(mask[..., None], pack, 0)
				note = args[0] + " (%d px glow)" % int(mask.sum())
		elif method == "copy_vanilla_if_blank":
			if vt[..., 3].max() == 0:
				result, note = vt, "fully transparent in vanilla too"
		elif method == "dry_foliage":
			vf = tg.load(os.path.join(V, args[0])).astype(np.float64)
			pf = tg.load(os.path.join(P, args[0])).astype(np.float64)
			ratio = (vt[..., :3] + 1.0) / (vf[..., :3] + 1.0)
			result = vt.copy()
			result[..., :3] = np.clip(pf[..., :3] * ratio, 0, 255)
			note = "pack foliage x (vanilla dry/foliage)"
		elif method == "end_portal_glow":
			eye = tg.load(os.path.join(P, args[0]))
			pal = tg.ref_palette([eye])
			glow = pal[len(pal) * 3 // 4:] if len(pal) else np.array([[80, 220, 200]])
			col = glow.mean(axis=0)
			frames = []
			for f in range(4):
				fr = np.zeros((16, 16, 4), np.int16)
				for y in range(16):
					a = int(max(0, 1 - y / 16.0) ** (1.5 + 0.5 * f) * (200 - 30 * f))
					fr[y, :, :3] = col
					fr[y, :, 3] = a
				frames.append(fr)
			result = np.concatenate(frames, axis=0)
			with open(out + ".mcmeta", "w") as f:
				json.dump({"animation": {"frametime": 12, "interpolate": True, "frames": [0, 1, 2, 3, 2, 1]}}, f, indent="\t")
			note = "4-frame fade in the end portal frame eye's colour"
		if result is None:
			rows.append((target, "skip", ",".join(args), "no usable pack source"))
			continue
		tg.save(result, out)
		vmeta = vpath + ".mcmeta"
		if os.path.exists(vmeta) and not os.path.exists(out + ".mcmeta"):
			shutil.copy2(vmeta, out + ".mcmeta")
		rows.append((target, how, note, "vanilla-derived shapes" if how == "palette" else ""))
	with open(report, "w") as f:
		f.write("target\tmethod\tsource\tnote\n")
		for row in rows:
			f.write("\t".join(row) + "\n")
	from collections import Counter
	print(Counter(r[1] for r in rows))


if __name__ == "__main__":
	main()
