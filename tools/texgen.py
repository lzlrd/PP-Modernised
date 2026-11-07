"""Texture derivation helpers for PP Modernised.

Three ways to make a texture the pack lacks:
- geo: Mojang built the 26.3 texture by cutting up another texture (bed faces, shulker box particle,
  baby collars). Learn that cut-up from the two vanilla files, then apply it to the pack's own copy
  of the source. The result is made entirely of pack art.
- shift: the texture is a recolour of another (lightning rod on, ominous vault). Learn the colour
  change from the vanilla pair by luminance rank and apply it to the pack's source.
- palette: no pack source exists. Re-colour the vanilla texture with the palette of related pack
  textures by luminance rank. The shapes are still Mojang's, so these are listed as vanilla-derived.
"""
import colorsys
import os

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image


def load(path):
	arr = np.asarray(Image.open(path).convert("RGBA"), dtype=np.int16).copy()
	arr[arr[..., 3] == 0] = 0
	return arr


def save(arr, path):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	out = np.clip(arr, 0, 255).astype(np.uint8)
	Image.fromarray(out, "RGBA").save(path, optimize=True)


def orientations(arr):
	"""Yield (index, oriented array) for the 8 rotations/flips."""
	for flip in (False, True):
		base = arr[:, ::-1] if flip else arr
		for k in range(4):
			yield (flip, k), np.rot90(base, k)


def orient(arr, key):
	flip, k = key
	base = arr[:, ::-1] if flip else arr
	return np.rot90(base, k)


def correspond(src, tgt, max_patches=24, min_count=3):
	"""Map every opaque target pixel to a source pixel via rigid patches.

	Returns (assign, coverage): assign[y, x] = (orientation index, sy, sx) in oriented-source coords
	or None. Coverage is the share of opaque target pixels matched exactly.
	"""
	h, w = tgt.shape[:2]
	opaque = tgt[..., 3] > 0
	remaining = opaque.copy()
	assign = np.full((h, w, 3), -1, dtype=np.int32)
	keys = []
	padded = []
	for key, s in orientations(src):
		keys.append(key)
		p = np.full((s.shape[0] + 2 * (h - 1), s.shape[1] + 2 * (w - 1), 4), -1, dtype=np.int16)
		p[h - 1:h - 1 + s.shape[0], w - 1:w - 1 + s.shape[1]] = s
		padded.append(p)
	matched = 0
	total = int(opaque.sum())
	if total == 0:
		return assign, 1.0, keys
	for _ in range(max_patches):
		best = (0, None, None, None)
		for oi, p in enumerate(padded):
			win = sliding_window_view(p, (h, w, 4))[:, :, 0]
			eq = np.all(win == tgt[None, None], axis=-1) & remaining[None, None]
			counts = eq.sum(axis=(2, 3))
			idx = np.unravel_index(np.argmax(counts), counts.shape)
			if counts[idx] > best[0]:
				best = (int(counts[idx]), oi, idx, eq[idx])
		count, oi, (oy, ox), mask = best if best[1] is not None else (0, None, (0, 0), None)
		if count < min_count:
			break
		ys, xs = np.nonzero(mask)
		assign[ys, xs, 0] = oi
		assign[ys, xs, 1] = ys + oy - (h - 1)
		assign[ys, xs, 2] = xs + ox - (w - 1)
		remaining &= ~mask
		matched += count
		if not remaining.any():
			break
	coverage = matched / total
	# Unmatched opaque pixels borrow the patch of their nearest matched neighbour.
	done = assign[..., 0] >= 0
	if done.any() and remaining.any():
		dy, dx = np.nonzero(done)
		for y, x in zip(*np.nonzero(remaining)):
			i = np.argmin((dy - y) ** 2 + (dx - x) ** 2)
			ny, nx = dy[i], dx[i]
			assign[y, x] = (assign[ny, nx, 0], assign[ny, nx, 1] + (y - ny), assign[ny, nx, 2] + (x - nx))
	assign[~opaque] = -1
	return assign, coverage, keys


def apply_geo(pack_src, vanilla_src_shape, assign, keys):
	"""Build the target from the pack's source using a learned correspondence."""
	vh, vw = vanilla_src_shape[:2]
	if pack_src.shape[:2] != (vh, vw):
		img = Image.fromarray(np.clip(pack_src, 0, 255).astype(np.uint8), "RGBA").resize((vw, vh), Image.NEAREST)
		pack_src = np.asarray(img, dtype=np.int16)
	oriented = [orient(pack_src, k) for k in keys]
	h, w = assign.shape[:2]
	out = np.zeros((h, w, 4), dtype=np.int16)
	for y in range(h):
		for x in range(w):
			oi, sy, sx = assign[y, x]
			if oi < 0:
				continue
			s = oriented[oi]
			if 0 <= sy < s.shape[0] and 0 <= sx < s.shape[1]:
				out[y, x] = s[sy, sx]
	return out


def luminance(arr):
	return 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]


def ref_palette(refs):
	"""Opaque reference colours sorted by luminance."""
	cols = []
	for r in refs:
		cols.append(r[r[..., 3] > 0][:, :3])
	cols = np.concatenate(cols) if cols else np.zeros((0, 3))
	if len(cols) == 0:
		return cols
	return cols[np.argsort(luminance(cols), kind="stable")]


def palette(tgt, refs):
	"""Recolour tgt with the reference palette, matching luminance ranks."""
	pal = ref_palette(refs)
	out = tgt.copy()
	op = tgt[..., 3] > 0
	if len(pal) == 0 or not op.any():
		return out
	lum = luminance(tgt[op].astype(np.float64))
	order = np.argsort(np.argsort(lum, kind="stable"), kind="stable")
	# Pixels with equal luminance share a rank so flat areas stay flat.
	uniq, inv = np.unique(np.round(lum, 1), return_inverse=True)
	ranks = np.array([order[inv == i].mean() for i in range(len(uniq))])[inv]
	frac = ranks / max(1, len(lum) - 1)
	idx = np.clip(np.round(frac * (len(pal) - 1)).astype(int), 0, len(pal) - 1)
	out[op, :3] = pal[idx]
	return out


def to_hsv(rgb):
	return np.array([colorsys.rgb_to_hsv(*(c / 255.0)) for c in rgb.reshape(-1, 3)]).reshape(rgb.shape)


def to_rgb(hsv):
	return np.array([colorsys.hsv_to_rgb(*c) for c in hsv.reshape(-1, 3)]).reshape(hsv.shape) * 255.0


def shift(v_src, v_tgt, pack_src):
	"""Apply the vanilla src->tgt colour change to pack_src, matched by luminance rank.

	Only pixels whose vanilla colour actually changes are shifted; alpha follows the pack source.
	"""
	if v_src.shape != v_tgt.shape:
		raise ValueError("shift needs same-size vanilla pair")
	both = (v_src[..., 3] > 0) & (v_tgt[..., 3] > 0)
	s = v_src[both][:, :3].astype(np.float64)
	t = v_tgt[both][:, :3].astype(np.float64)
	hs, ht = to_hsv(s), to_hsv(t)
	delta = ht - hs
	delta[:, 0] = (delta[:, 0] + 0.5) % 1.0 - 0.5
	changed = np.abs(s - t).max(axis=1) > 8
	src_lum = luminance(s)
	out = pack_src.copy()
	op = pack_src[..., 3] > 0
	if not op.any() or not changed.any():
		return out
	p = pack_src[op][:, :3].astype(np.float64)
	plum = luminance(p)
	# Match each pack pixel to the vanilla pixel of the same luminance percentile.
	vorder = np.argsort(src_lum, kind="stable")
	prank = np.argsort(np.argsort(plum, kind="stable"), kind="stable") / max(1, len(plum) - 1)
	vidx = vorder[np.clip(np.round(prank * (len(vorder) - 1)).astype(int), 0, len(vorder) - 1)]
	hsv = to_hsv(p)
	d = delta[vidx] * changed[vidx][:, None]
	if changed[vidx].any():
		# Hue is set to the vanilla target hue rather than shifted, so recolours land on the same colour.
		hsv[:, 0] = np.where(changed[vidx], ht[vidx, 0], hsv[:, 0])
		hsv[:, 1] = np.clip(hsv[:, 1] + d[:, 1], 0, 1)
		hsv[:, 2] = np.clip(hsv[:, 2] + d[:, 2], 0, 1)
	out[op, :3] = to_rgb(hsv)
	return out
