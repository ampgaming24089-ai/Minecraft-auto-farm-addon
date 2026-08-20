#!/usr/bin/env python3
"""Regenerate every Riftborne texture from source.

    python3 tools/gen_art.py

No arguments, no dependencies, no network. Output is byte-for-byte identical on
every run, so regenerating produces an empty diff unless a recipe actually
changed. Each recipe below is authored as "what is this material made of",
and the matching MER map is derived from the albedo rather than painted twice.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artlib import (  # noqa: E402
    TRANSPARENT,
    Canvas,
    Rng,
    bevel,
    fbm,
    hex_rgba,
    hsv,
    luma,
    make_mer,
    mix,
    radial,
    shade,
    speckle,
    veins,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKS = os.path.join(ROOT, "RP", "textures", "blocks")
ITEMS = os.path.join(ROOT, "RP", "textures", "items")
ENTITY = os.path.join(ROOT, "RP", "textures", "entity")

# The whole pack is built from six anchor colours so nothing drifts out of key.
PALETTE = {
    "endstone": hex_rgba("#DCE0A8"),
    "endstone_dark": hex_rgba("#A8AC78"),
    "void": hex_rgba("#2A1140"),
    "void_lit": hex_rgba("#C77BFF"),
    "lumen": hex_rgba("#1E8C7E"),
    "lumen_lit": hex_rgba("#5FE8D2"),
}


def out(canvas, folder, name):
    path = os.path.join(folder, name + ".png")
    canvas.save(path)
    return path


def emit(albedo, folder, name, **mer_kwargs):
    """Write an albedo texture plus its derived MER companion."""
    out(albedo, folder, name)
    if mer_kwargs.pop("mer", True):
        make_mer(albedo, **mer_kwargs).save(os.path.join(folder, name + "_mer.png"))


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------


def stone_base(seed, base, dark, contrast=0.30, size=16):
    """Shared end-stone substrate: soft blotches, not per-pixel static."""
    c = Canvas(size)

    def paint(x, y, _cur):
        n = fbm(x, y, size, seed, octaves=3, base_period=4)
        grain = fbm(x, y, size, seed + 1301, octaves=2, base_period=8)
        t = (n * 0.75 + grain * 0.25 - 0.5) * 2.0 * contrast
        return shade(mix(base, dark, max(0.0, min(1.0, n * 0.55))), t)

    c.each(paint)
    return c


def block_shattered_end_stone():
    """End stone that the void has been pulling apart for a few aeons."""
    c = stone_base(4021, PALETTE["endstone"], PALETTE["endstone_dark"], 0.34)
    veins(c, 9107, 3, mix(PALETTE["endstone_dark"], PALETTE["void"], 0.55), 22, wobble=1.1)
    veins(c, 9108, 2, mix(PALETTE["void"], (0, 0, 0, 255), 0.35), 14, wobble=1.3)
    speckle(c, 5501, 0.06, [shade(PALETTE["endstone_dark"], -0.25), shade(PALETTE["endstone"], 0.18)])
    emit(c, BLOCKS, "voidbound_shattered_end_stone", roughness=246, roughness_variation=14, seed=3)


def block_verdant_end_stone():
    """End stone colonised by void moss - the ground cover of the groves."""
    c = stone_base(6613, PALETTE["endstone"], PALETTE["endstone_dark"], 0.24)
    moss = mix(PALETTE["lumen"], PALETTE["void"], 0.35)
    moss_lit = mix(PALETTE["lumen_lit"], moss, 0.45)

    def overgrow(x, y, cur):
        n = fbm(x, y, 16, 8821, octaves=3, base_period=4)
        if n < 0.46:
            return None
        t = min(1.0, (n - 0.46) / 0.34)
        return mix(cur, mix(moss, moss_lit, t * 0.6), 0.35 + 0.6 * t)

    c.each(overgrow)
    speckle(c, 8822, 0.045, [moss_lit, shade(moss, -0.3)])
    emit(
        c,
        BLOCKS,
        "voidbound_verdant_end_stone",
        roughness=238,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=0.5,
        emissive_threshold=0.30,
    )


def block_echo_ore():
    """Echo shards embedded in end stone: clustered, not scattered confetti."""
    c = stone_base(1777, PALETTE["endstone"], PALETTE["endstone_dark"], 0.26)
    rng = Rng(3311)
    core = PALETTE["lumen_lit"]
    rim = mix(PALETTE["lumen"], PALETTE["void"], 0.4)
    for _ in range(4):
        cx, cy = rng.range(2, 14), rng.range(2, 14)
        r = rng.range(1.8, 3.1)
        for y in range(16):
            for x in range(16):
                # Wrap the distance so clusters bleed across the tile seam.
                dx = min(abs(x + 0.5 - cx), 16 - abs(x + 0.5 - cx))
                dy = min(abs(y + 0.5 - cy), 16 - abs(y + 0.5 - cy))
                d = math.hypot(dx, dy) / r
                if d > 1.0:
                    continue
                c.blend(x, y, mix(core, rim, min(1.0, d ** 0.7)))
    speckle(c, 3312, 0.03, [shade(core, 0.35)])
    emit(
        c,
        BLOCKS,
        "voidbound_echo_ore",
        roughness=200,
        emissive_from=core[:3],
        emissive_gain=1.15,
        emissive_threshold=0.12,
    )


def block_void_crystal():
    """A solid crystal block, read as large facets rather than noise."""
    c = Canvas(16)
    deep = PALETTE["void"]
    lit = PALETTE["void_lit"]

    def facets(x, y, _cur):
        # Two rotated sawtooth fields intersect into flat, angular planes.
        a = ((x * 0.62 + y * 0.31) % 4.0) / 4.0
        b = ((x * -0.28 + y * 0.71) % 5.0) / 5.0
        n = fbm(x, y, 16, 4477, octaves=2, base_period=4)
        t = 0.45 * a + 0.35 * b + 0.20 * n
        return mix(deep, lit, max(0.0, min(1.0, t * 1.15)))

    c.each(facets)
    veins(c, 4478, 4, shade(lit, 0.45), 16, wobble=0.35)
    emit(
        c,
        BLOCKS,
        "voidbound_void_crystal_block",
        metalness=0,
        roughness=54,
        emissive_from=lit[:3],
        emissive_gain=0.95,
        emissive_threshold=0.20,
    )


def block_void_glass():
    """Tinted, mostly-clear glass with a bright rift seam through it."""
    c = Canvas(16)
    deep = mix(PALETTE["void"], (0, 0, 0, 255), 0.35)
    tint = (deep[0], deep[1], deep[2], 104)
    c.fill(tint)
    frame = (PALETTE["void_lit"][0], PALETTE["void_lit"][1], PALETTE["void_lit"][2], 205)
    for i in range(16):
        c.set(i, 0, frame)
        c.set(i, 15, frame)
        c.set(0, i, frame)
        c.set(15, i, frame)
    for i in range(3, 13):
        c.blend(i, i, (255, 255, 255, 60))
    emit(
        c,
        BLOCKS,
        "voidbound_void_glass",
        roughness=18,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=0.5,
        emissive_threshold=0.35,
    )


def _stalk(c, x, top, bottom, color, rng, sway=0.0):
    px = x
    for y in range(bottom, top - 1, -1):
        px += rng.range(-sway, sway)
        c.blend(int(round(px)), y, color)
    return px


def block_voidbloom():
    """Cross-model flora: paired stalks, each opening into a violet blossom."""
    c = Canvas(16)
    rng = Rng(2204)
    stalk = mix(PALETTE["void"], PALETTE["endstone_dark"], 0.30)
    stalk_lit = mix(stalk, PALETTE["void_lit"], 0.30)
    petal = PALETTE["void_lit"]
    petal_deep = mix(PALETTE["void"], PALETTE["void_lit"], 0.45)

    def blossom(cx, cy, r):
        # Four petals around a bright pistil - a shape, not a gradient blob.
        for angle in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
            px = cx + math.cos(angle) * r * 0.72
            py = cy + math.sin(angle) * r * 0.72
            for y in range(c.h):
                for x in range(c.w):
                    d = math.hypot(x + 0.5 - px, y + 0.5 - py) / (r * 0.62)
                    if d <= 1.0:
                        c.blend(x, y, mix(petal, petal_deep, d ** 0.8))
        for y in range(c.h):
            for x in range(c.w):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / (r * 0.44)
                if d <= 1.0:
                    c.blend(x, y, mix((255, 246, 255, 255), petal, d))

    for base_x, top, r in ((4, 7, 3.0), (11, 10, 2.2)):
        px = base_x
        for y in range(15, top - 1, -1):
            px += rng.range(-0.28, 0.28)
            c.blend(int(round(px)), y, stalk)
            if y % 4 == 1:
                c.blend(int(round(px)) + rng.int(-1, 1), y, stalk_lit)
        blossom(px + 0.5, top - 0.5, r)

    # A couple of shed motes drifting off the blossoms.
    for mx, my in ((13, 4), (2, 3), (8, 12)):
        c.blend(mx, my, shade(petal, 0.45))
    emit(
        c,
        BLOCKS,
        "voidbound_voidbloom",
        roughness=170,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.3,
        emissive_threshold=0.10,
    )

def block_lumen_bulb():
    """Cross-model flora: teal lantern-fruit on a pale stem."""
    c = Canvas(16)
    rng = Rng(7702)
    stem = mix(PALETTE["lumen"], PALETTE["endstone_dark"], 0.4)
    tip = _stalk(c, 8, 7, 15, stem, rng, sway=0.25)
    radial(c, tip + 0.5, 5.5, 4.0, PALETTE["lumen_lit"], (20, 80, 76, 0), falloff=1.35)
    radial(c, tip - 0.6, 4.4, 1.6, (235, 255, 250, 255), (95, 232, 210, 0), falloff=1.2)
    for y in range(8, 13):
        c.blend(int(tip) - 2, y, mix(stem, PALETTE["lumen_lit"], 0.3))
        c.blend(int(tip) + 2, y + 1, mix(stem, PALETTE["lumen_lit"], 0.2))
    emit(
        c,
        BLOCKS,
        "voidbound_lumen_bulb",
        roughness=140,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.45,
        emissive_threshold=0.08,
    )


def block_rift_lantern():
    """A caged lantern: obsidian frame, violet rift burning behind the bars."""
    frame = mix(PALETTE["void"], (0, 0, 0, 255), 0.45)
    frame_lit = shade(frame, 0.22)
    core = PALETTE["void_lit"]

    side = Canvas(16)
    # Glowing interior first, then the ironwork on top of it.
    side.fill(mix(frame, core, 0.10))
    radial(side, 8.0, 8.5, 7.5, shade(core, 0.55), mix(frame, core, 0.18), falloff=1.25)
    # Heavy top and bottom caps.
    side.rect(0, 0, 15, 2, frame)
    side.rect(0, 13, 15, 15, frame)
    for x in range(16):
        side.blend(x, 0, frame_lit)
        side.blend(x, 15, shade(frame, -0.35))
        side.blend(x, 2, shade(frame, -0.3))
        side.blend(x, 13, frame_lit)
    # Two vertical bars and one waist band - sparse enough to see the rift.
    for x in (3, 12):
        for y in range(3, 13):
            side.set(x, y, frame if y % 3 else frame_lit)
    for x in range(16):
        side.set(x, 8, frame if x % 4 else frame_lit)
    # Corner rivets.
    for x, y in ((1, 3), (14, 3), (1, 12), (14, 12)):
        side.set(x, y, frame_lit)
    emit(
        side,
        BLOCKS,
        "voidbound_rift_lantern_side",
        metalness=0,
        roughness=120,
        emissive_from=core[:3],
        emissive_gain=1.25,
        emissive_threshold=0.14,
    )

    top = Canvas(16)
    top.fill(shade(frame, -0.10))
    top.rect(2, 2, 13, 13, frame)
    radial(top, 8.0, 8.0, 5.4, shade(core, 0.35), shade(frame, 0.05), falloff=1.7)
    for i in range(16):
        top.blend(i, 0, frame_lit)
        top.blend(0, i, frame_lit)
        top.blend(i, 15, shade(frame, -0.3))
        top.blend(15, i, shade(frame, -0.3))
    speckle(top, 991, 0.04, [frame_lit, shade(frame, -0.2)])
    emit(
        top,
        BLOCKS,
        "voidbound_rift_lantern_top",
        roughness=150,
        emissive_from=core[:3],
        emissive_gain=0.9,
        emissive_threshold=0.22,
    )

def _shard_silhouette(c, points, fill_inner, fill_outer):
    """Fill a convex polygon with a centre-out gradient, then bevel it."""
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    for y in range(c.h):
        for x in range(c.w):
            px, py = x + 0.5, y + 0.5
            inside = True
            for i in range(len(points)):
                ax, ay = points[i]
                bx, by = points[(i + 1) % len(points)]
                if (bx - ax) * (py - ay) - (by - ay) * (px - ax) < 0:
                    inside = False
                    break
            if not inside:
                continue
            d = min(1.0, math.hypot(px - cx, py - cy) / 6.0)
            c.set(x, y, mix(fill_inner, fill_outer, d))


def item_echo_shard():
    c = Canvas(16)
    _shard_silhouette(
        c,
        [(8, 1), (12, 7), (9.5, 14.5), (6, 14), (3.5, 7)],
        PALETTE["lumen_lit"],
        mix(PALETTE["lumen"], PALETTE["void"], 0.45),
    )
    veins(c, 6161, 2, shade(PALETTE["lumen_lit"], 0.5), 9, wobble=0.5)
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.5))
    emit(
        c,
        ITEMS,
        "voidbound_echo_shard",
        roughness=64,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.1,
        emissive_threshold=0.16,
    )


def item_void_crystal():
    c = Canvas(16)
    _shard_silhouette(
        c,
        [(8, 0.5), (13, 5), (11, 13), (5, 13.5), (3, 5)],
        shade(PALETTE["void_lit"], 0.25),
        PALETTE["void"],
    )
    for y in range(2, 13):
        c.blend(8, y, shade(PALETTE["void_lit"], 0.55))
    bevel(c, light=0.3, dark=0.3)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.6))
    emit(
        c,
        ITEMS,
        "voidbound_void_crystal",
        roughness=42,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.2,
        emissive_threshold=0.18,
    )


def item_rift_compass():
    """A ring of dark alloy around a floating violet needle."""
    c = Canvas(16)
    body = mix(PALETTE["void"], PALETTE["endstone_dark"], 0.30)
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            if 4.4 <= d <= 7.2:
                c.set(x, y, shade(body, 0.18 - 0.12 * ((d - 4.4) / 2.8)))
    radial(c, 8, 8, 4.6, mix(PALETTE["void"], (0, 0, 0, 255), 0.55), mix(PALETTE["void"], PALETTE["void_lit"], 0.25))
    for i in range(-3, 4):
        c.blend(8 + i, 8 - i, shade(PALETTE["void_lit"], 0.35 if i < 0 else -0.1))
    c.blend(8, 8, (255, 255, 255, 255))
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.65))
    emit(
        c,
        ITEMS,
        "voidbound_rift_compass",
        metalness=140,
        roughness=96,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=0.9,
        emissive_threshold=0.30,
    )


def item_lumen_berry():
    c = Canvas(16)
    radial(c, 7.5, 8.5, 5.2, PALETTE["lumen_lit"], mix(PALETTE["lumen"], PALETTE["void"], 0.5), falloff=1.25)
    radial(c, 6.0, 6.5, 2.0, (240, 255, 252, 255), (95, 232, 210, 0), falloff=1.1)
    for y in range(2, 5):
        c.blend(10, y, mix(PALETTE["lumen"], PALETTE["void"], 0.3))
    c.blend(11, 4, mix(PALETTE["lumen"], PALETTE["void"], 0.3))
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(
        c,
        ITEMS,
        "voidbound_lumen_berry",
        roughness=110,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.0,
        emissive_threshold=0.20,
    )


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------


def paint_box(c, u, v, w, h, d, painter):
    """Fill the six faces of a Bedrock box UV footprint.

    Bedrock lays a box out as: top and bottom on the first `d` rows, then
    east / north / west / south across the next `h` rows. `painter(face, fx,
    fy, fw, fh)` returns the colour for one pixel of one face.
    """
    faces = [
        ("top", u + d, v, w, d),
        ("bottom", u + d + w, v, w, d),
        ("east", u, v + d, d, h),
        ("north", u + d, v + d, w, h),
        ("west", u + d + w, v + d, d, h),
        ("south", u + d + w + d, v + d, w, h),
    ]
    for name, ox, oy, fw, fh in faces:
        for fy in range(fh):
            for fx in range(fw):
                color = painter(name, fx, fy, fw, fh)
                if color is not None:
                    c.set(ox + fx, oy + fy, color)


def entity_lumen_wisp():
    """32x32 sheet for the wisp: a glowing core plus three orbiting shards."""
    c = Canvas(32, 32)
    core_in = shade(PALETTE["lumen_lit"], 0.55)
    core_out = mix(PALETTE["lumen"], PALETTE["void"], 0.30)

    def core(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.0)
        n = fbm(fx * 2, fy * 2, 12, 1234, octaves=2, base_period=4)
        return mix(core_in, core_out, min(1.0, d * 0.85 + n * 0.2))

    paint_box(c, 0, 0, 6, 6, 6, core)

    def shard(_face, fx, fy, fw, fh):
        t = (fx + fy) / float(max(1, fw + fh - 2))
        return mix(shade(PALETTE["lumen_lit"], 0.3), mix(PALETTE["lumen"], PALETTE["void"], 0.5), t)

    for u, v in ((0, 14), (12, 14), (0, 20)):
        paint_box(c, u, v, 2, 2, 2, shard)

    emit(
        c,
        ENTITY,
        "voidbound_lumen_wisp",
        roughness=90,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.35,
        emissive_threshold=0.10,
    )


def entity_rift_stalker():
    """64x32 sheet: obsidian carapace with violet rift light in the seams."""
    c = Canvas(64, 32)
    hide = mix(PALETTE["void"], (0, 0, 0, 255), 0.12)
    hide_lit = mix(PALETTE["void"], PALETTE["void_lit"], 0.55)

    def carapace(face, fx, fy, fw, fh):
        n = fbm(fx * 1.5, fy * 1.5, 16, 5150, octaves=3, base_period=4)
        base = mix(hide, shade(hide, 0.42), n)
        # A bright ridge runs down the spine and along each flank seam.
        if face == "top" and abs(fx - (fw - 1) / 2.0) < 0.9:
            return mix(base, PALETTE["void_lit"], 0.55)
        if face in ("east", "west") and fy in (1, fh - 2):
            return mix(base, hide_lit, 0.6)
        return base

    paint_box(c, 0, 0, 8, 6, 12, carapace)

    def skull(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 12, 6160, octaves=2, base_period=4)
        base = mix(hide, shade(hide, 0.38), n)
        if face == "north" and fy in (1, 2) and fx in (1, fw - 2):
            return shade(PALETTE["void_lit"], 0.5)  # eyes
        return base

    paint_box(c, 0, 20, 6, 5, 5, skull)

    def crest(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(PALETTE["void_lit"], hide, min(1.0, t * 1.3))

    paint_box(c, 24, 20, 2, 4, 6, crest)

    def limb(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(shade(hide, 0.1), mix(hide, PALETTE["void_lit"], 0.25), t)

    for u, v in ((44, 0), (44, 10), (52, 0), (52, 10)):
        paint_box(c, u, v, 2, 6, 2, limb)

    emit(
        c,
        ENTITY,
        "voidbound_rift_stalker",
        roughness=150,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.1,
        emissive_threshold=0.22,
    )


def entity_void_moth():
    """64x32 sheet: a dusty violet body under four translucent-looking wings."""
    c = Canvas(64, 32)
    fur = mix(PALETTE["void"], PALETTE["endstone_dark"], 0.22)
    fur_hi = mix(fur, PALETTE["void_lit"], 0.35)
    wing = mix(PALETTE["void_lit"], PALETTE["void"], 0.45)
    wing_edge = shade(PALETTE["void_lit"], 0.35)

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 12, 4310, octaves=3, base_period=4)
        base = mix(fur, fur_hi, n * 0.55)
        # Banding along the abdomen.
        if face in ("east", "west", "top") and fy % 2 == 0:
            return shade(base, -0.12)
        return base

    paint_box(c, 0, 0, 4, 4, 6, body)

    def head(face, fx, fy, fw, fh):
        base = mix(fur_hi, fur, 0.3)
        if face == "north" and fy == 1 and fx in (1, fw - 2):
            return shade(PALETTE["lumen_lit"], 0.4)  # eyes
        return base

    paint_box(c, 22, 0, 4, 3, 2, head)

    def make_wing(scale):
        def paint(face, fx, fy, fw, fh):
            # Veins run outward from the wing root; the trailing edge glows.
            t = fx / float(max(1, fw - 1))
            n = fbm(fx * 3, fy * 3, 16, 4311, octaves=2, base_period=4)
            base = mix(wing, mix(wing, PALETTE["void"], 0.55), t * scale)
            if fx % 3 == 0:
                base = mix(base, wing_edge, 0.45)
            if face == "top" or face == "bottom":
                return mix(base, wing_edge, 0.15 + n * 0.2)
            return base
        return paint

    paint_box(c, 0, 12, 7, 1, 5, make_wing(0.9))
    paint_box(c, 0, 19, 7, 1, 5, make_wing(0.9))
    paint_box(c, 26, 12, 5, 1, 4, make_wing(1.1))
    paint_box(c, 26, 18, 5, 1, 4, make_wing(1.1))

    def antenna(_face, fx, fy, fw, fh):
        return mix(fur_hi, PALETTE["lumen_lit"], 1.0 - fy / float(max(1, fh - 1)))

    paint_box(c, 46, 0, 1, 3, 1, antenna)

    emit(
        c,
        ENTITY,
        "voidbound_void_moth",
        roughness=190,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=0.85,
        emissive_threshold=0.28,
    )


def entity_echo_sentinel():
    """64x64 sheet: quarried end stone bound around a burning echo core."""
    c = Canvas(64, 64)
    stone = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.42)
    stone_hi = mix(stone, PALETTE["endstone"], 0.35)
    seam = PALETTE["lumen_lit"]

    def masonry(seed, seam_faces=()):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.4, fy * 1.4, 16, seed, octaves=3, base_period=4)
            base = mix(stone, stone_hi, n)
            # Brick courses, offset every other row.
            if fy % 4 == 0:
                base = shade(base, -0.22)
            elif (fx + (fy // 4) * 2) % 5 == 0:
                base = shade(base, -0.16)
            if face in seam_faces and abs(fx - (fw - 1) / 2.0) < 0.6:
                return mix(base, seam, 0.5)
            return base
        return paint

    paint_box(c, 0, 0, 10, 14, 6, masonry(7710, ("north",)))
    paint_box(c, 0, 22, 8, 8, 8, masonry(7711))
    paint_box(c, 34, 0, 4, 14, 4, masonry(7712))
    paint_box(c, 34, 20, 4, 14, 4, masonry(7713))
    paint_box(c, 0, 40, 4, 12, 4, masonry(7714))
    paint_box(c, 18, 40, 4, 12, 4, masonry(7715))

    def core(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.2)
        return mix(shade(seam, 0.6), mix(seam, PALETTE["void"], 0.6), d)

    paint_box(c, 36, 40, 4, 4, 1, core)

    # Eyes on the head's north face.
    for x, y in ((10, 33), (13, 33), (10, 34), (13, 34)):
        c.set(x, y, shade(seam, 0.55))

    emit(
        c,
        ENTITY,
        "voidbound_echo_sentinel",
        roughness=232,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.2,
        emissive_threshold=0.22,
    )


# --------------------------------------------------------------------------
# Armor
# --------------------------------------------------------------------------

ARMOR = os.path.join(ROOT, "RP", "textures", "models", "armor")

# Vanilla's humanoid.armor UV layout on a 64x32 sheet. Layer 1 carries the
# helmet, chestplate and boots; layer 2 carries the leggings. Copied from the
# vanilla netherite attachables so the plates land on the right body parts.
ARMOR_LAYER_1 = [
    ("helmet", 0, 0, 8, 8, 8),
    ("body", 16, 16, 8, 12, 4),
    ("arm", 40, 16, 4, 12, 4),
    ("leg", 0, 16, 4, 12, 4),
]
ARMOR_LAYER_2 = [
    ("body", 16, 16, 8, 12, 4),
    ("leg", 0, 16, 4, 12, 4),
]


def _plate_painter(part, layer, seed):
    """Paint one armour piece.

    Minecraft armour reads as armour because of its edges: a pauldron cap, a
    belt line, a knee band, a boot cuff. A flat wash of one colour over the
    whole body - which is what the first pass did - renders as body paint. So
    each part gets its own banding, laid out in the box's local face
    coordinates, with gold as the only trim colour and the rift glow kept to
    thin accents.
    """
    plate = hex_rgba("#1E0E2E")
    plate_mid = hex_rgba("#3A2452")
    plate_hi = hex_rgba("#6B4A8C")
    gold = hex_rgba("#C9A85C")
    gold_dim = mix(gold, plate, 0.45)
    glow = PALETTE["void_lit"]

    def grain(fx, fy, base, strength=0.22):
        n = fbm(fx * 1.7, fy * 1.7, 16, seed, octaves=3, base_period=4)
        return shade(base, (n - 0.5) * strength)

    def paint(face, fx, fy, fw, fh):
        top = fy == 0
        bottom = fy == fh - 1

        if part == "helmet":
            base = plate_mid if face in ("north", "east", "west", "south") else plate_hi
            if face == "top":
                base = plate_hi
            if face == "bottom":
                return grain(fx, fy, plate, 0.12)
            if face == "north" and fy == 3 and 1 < fx < fw - 2:
                return glow                      # visor slit
            if face == "north" and fy == 2:
                return mix(plate_hi, gold, 0.35)  # brow ridge
            if fy == fh - 2 and face != "top":
                return gold_dim                   # rim above the neck
            return grain(fx, fy, base)

        if part == "body" and layer == 1:
            # Chestplate: pauldron caps, a V-neck, a belt at the hem.
            if face == "top":
                return grain(fx, fy, plate_hi, 0.14)
            if face == "bottom":
                return grain(fx, fy, plate, 0.12)
            if fy <= 1:
                if face == "north" and fw > 4 and 2 < fx < fw - 3:
                    return grain(fx, fy, plate, 0.14)   # neck opening
                return mix(plate_hi, gold, 0.22 if fy == 1 else 0.0)
            if fy == fh - 2:
                return gold                              # belt
            if bottom:
                return grain(fx, fy, plate, 0.12)
            if face == "north" and fy in (4, 5) and abs(fx - (fw - 1) / 2.0) < 0.6:
                return glow                              # chest core
            return grain(fx, fy, plate_mid if fy < fh - 4 else plate)

        if part == "body" and layer == 2:
            # Leggings waist: heavy belt over a plain skirt.
            if face in ("top", "bottom"):
                return grain(fx, fy, plate, 0.12)
            if fy <= 1:
                return gold if fy == 0 else gold_dim
            if fy == 2:
                return plate_hi
            if face in ("north", "south") and fx % 3 == 0:
                return grain(fx, fy, plate, 0.14)        # panel seams
            return grain(fx, fy, plate_mid)

        if part == "arm":
            # Pauldron, plain upper arm, bracer.
            if face == "top":
                return grain(fx, fy, plate_hi, 0.14)
            if face == "bottom":
                return grain(fx, fy, plate, 0.12)
            if fy <= 2:
                return gold_dim if fy == 2 else grain(fx, fy, plate_hi)
            if fy in (9, 10):
                return gold if fy == 10 else grain(fx, fy, plate_hi)
            if bottom:
                return grain(fx, fy, plate, 0.12)
            return grain(fx, fy, plate_mid)

        if part == "leg" and layer == 1:
            # Boot: the upper part of this box is hidden by the greaves, so
            # only the cuff down is detailed.
            if face == "top":
                return grain(fx, fy, plate, 0.12)
            if fy < 6:
                return grain(fx, fy, plate_mid, 0.14)
            if fy == 6:
                return gold                              # cuff
            if face == "bottom" or bottom:
                return grain(fx, fy, plate_hi, 0.12)     # sole
            if fy == fh - 2 and face == "north":
                return mix(plate_hi, glow, 0.25)         # toe cap
            return grain(fx, fy, plate)

        # part == "leg" and layer == 2 - greaves.
        if face in ("top", "bottom"):
            return grain(fx, fy, plate, 0.12)
        if fy in (5, 6):
            return gold if fy == 5 else plate_hi         # knee band
        if top:
            return grain(fx, fy, plate_hi, 0.14)
        return grain(fx, fy, plate_mid)

    return paint


def armor_layers():
    os.makedirs(ARMOR, exist_ok=True)
    for name, parts, seed, layer in (
        ("voidbound_armor_1", ARMOR_LAYER_1, 8801, 1),
        ("voidbound_armor_2", ARMOR_LAYER_2, 8802, 2),
    ):
        sheet = Canvas(64, 32)
        for part, u, v, w, h, d in parts:
            paint_box(sheet, u, v, w, h, d, _plate_painter(part, layer, seed))
        emit(
            sheet,
            ARMOR,
            name,
            metalness=48,
            roughness=118,
            emissive_from=PALETTE["void_lit"][:3],
            emissive_gain=1.15,
            emissive_threshold=0.22,
        )


def _armor_icon(name, draw):
    """Shared finishing pass for the four armour icons."""
    c = Canvas(16)
    plate = mix(PALETTE["void"], (0, 0, 0, 255), 0.28)
    draw(c, plate, PALETTE["void_lit"], PALETTE["lumen_lit"])
    bevel(c, light=0.26, dark=0.28)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.65))
    emit(
        c,
        ITEMS,
        name,
        metalness=64,
        roughness=104,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.1,
        emissive_threshold=0.26,
    )


def item_void_helmet():
    def draw(c, plate, lit, echo):
        c.rect(3, 3, 12, 10, plate)
        c.rect(2, 5, 13, 11, plate)
        c.rect(5, 8, 10, 11, TRANSPARENT)   # face opening
        for x in range(5, 11):
            c.set(x, 7, lit)                # visor band
        c.set(7, 2, lit)
        c.set(8, 2, lit)
        c.set(3, 11, echo)
        c.set(12, 11, echo)
    _armor_icon("voidbound_void_helmet", draw)


def item_void_chestplate():
    def draw(c, plate, lit, echo):
        c.rect(2, 3, 13, 5, plate)          # shoulders
        c.rect(4, 3, 11, 13, plate)         # torso
        c.rect(2, 4, 3, 9, plate)           # left pauldron
        c.rect(12, 4, 13, 9, plate)         # right pauldron
        for y in range(5, 13):
            c.set(7, y, lit)
            c.set(8, y, lit)
        c.set(3, 6, echo)
        c.set(12, 6, echo)
    _armor_icon("voidbound_void_chestplate", draw)


def item_void_leggings():
    def draw(c, plate, lit, echo):
        c.rect(3, 2, 12, 5, plate)          # belt
        c.rect(3, 5, 6, 14, plate)          # left leg
        c.rect(9, 5, 12, 14, plate)         # right leg
        for x in range(4, 12):
            c.set(x, 3, lit)
        c.set(4, 9, echo)
        c.set(11, 9, echo)
    _armor_icon("voidbound_void_leggings", draw)


def item_void_boots():
    def draw(c, plate, lit, echo):
        c.rect(2, 6, 6, 12, plate)
        c.rect(9, 6, 13, 12, plate)
        c.rect(1, 11, 6, 13, plate)         # left toe
        c.rect(9, 11, 14, 13, plate)        # right toe
        for x in range(2, 7):
            c.set(x, 7, lit)
        for x in range(9, 14):
            c.set(x, 7, lit)
        c.set(2, 12, echo)
        c.set(13, 12, echo)
    _armor_icon("voidbound_void_boots", draw)


def entity_chorus_hopper():
    """32x32: a plump chorus-fed grazer, pale purple with darker dapples."""
    c = Canvas(32, 32)
    hide = hex_rgba("#8A5FA8")
    hide_dark = mix(hide, PALETTE["void"], 0.5)
    belly = mix(hide, hex_rgba("#E8D8F2"), 0.55)

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 2.2, fy * 2.2, 16, 4501, octaves=3, base_period=4)
        base = mix(hide, hide_dark, n * 0.7)
        if face == "bottom":
            return belly
        if n > 0.68:
            return hide_dark            # dapples
        return base

    paint_box(c, 0, 0, 6, 5, 8, body)

    def head(face, fx, fy, fw, fh):
        base = mix(hide, belly, 0.25)
        if face == "north" and fy == 1 and fx in (0, fw - 1):
            return PALETTE["void_lit"]  # eyes
        if face == "north" and fy == 3:
            return hide_dark            # mouth line
        return base

    paint_box(c, 0, 14, 4, 4, 3, head)

    def leg(_face, fx, fy, fw, fh):
        return mix(hide_dark, hide, fy / float(max(1, fh - 1)))

    paint_box(c, 16, 14, 2, 2, 2, leg)
    paint_box(c, 16, 19, 2, 2, 2, leg)

    def frond(_face, fx, fy, fw, fh):
        return mix(PALETTE["void_lit"], hide_dark, fy / float(max(1, fh - 1)))

    paint_box(c, 0, 22, 1, 3, 1, frond)
    paint_box(c, 6, 22, 1, 3, 1, frond)

    emit(c, ENTITY, "voidbound_chorus_hopper", roughness=210,
         emissive_from=PALETTE["void_lit"][:3], emissive_gain=0.7, emissive_threshold=0.34)


def entity_shard_wraith():
    """64x32: a hollow shroud with nothing inside it but light."""
    c = Canvas(64, 32)
    cloth = mix(PALETTE["void"], (0, 0, 0, 255), 0.30)
    cloth_hi = mix(cloth, hex_rgba("#7B4FA8"), 0.55)
    inner = hex_rgba("#D9A8FF")

    def hood(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 16, 7801, octaves=3, base_period=4)
        base = mix(cloth, cloth_hi, n * 0.8)
        if face == "north":
            # A dark void under the hood, with two points of light in it.
            if 0 < fx < fw - 1 and fy > 1:
                if fy == 3 and fx in (1, fw - 2):
                    return inner
                return mix(cloth, (0, 0, 0, 255), 0.7)
        if face == "top":
            return shade(base, 0.16)
        return base

    paint_box(c, 0, 0, 6, 6, 6, hood)

    def shroud(face, fx, fy, fw, fh):
        n = fbm(fx * 1.6, fy * 1.6, 16, 7802, octaves=3, base_period=4)
        base = mix(cloth, cloth_hi, n * 0.6)
        t = fy / float(max(1, fh - 1))
        # The hem frays into light.
        if t > 0.7 and (fx + fy) % 2 == 0:
            return mix(base, inner, (t - 0.7) / 0.3 * 0.7)
        if face in ("east", "west") and fx % 3 == 0:
            return shade(base, -0.2)
        return base

    paint_box(c, 0, 13, 8, 9, 8, shroud)

    def tatter(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(cloth_hi, mix(cloth, inner, 0.4), t)

    paint_box(c, 34, 0, 1, 5, 3, tatter)
    paint_box(c, 44, 0, 1, 5, 3, tatter)

    emit(c, ENTITY, "voidbound_shard_wraith", roughness=176,
         emissive_from=inner[:3], emissive_gain=1.25, emissive_threshold=0.18)


def entity_crystal_crawler():
    """64x32: a low six-legged thing armoured in echo crystal."""
    c = Canvas(64, 32)
    chitin = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.55)
    chitin_hi = mix(chitin, PALETTE["endstone"], 0.4)
    crystal = PALETTE["lumen_lit"]

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 1.5, fy * 1.5, 16, 3901, octaves=3, base_period=4)
        base = mix(chitin, chitin_hi, n)
        if face == "top" and fy % 3 == 1:
            return shade(base, -0.2)     # segment plates
        if face in ("east", "west") and fy == fh - 1:
            return mix(base, crystal, 0.35)
        return base

    paint_box(c, 0, 0, 8, 4, 12, body)

    def head(face, fx, fy, fw, fh):
        base = mix(chitin_hi, chitin, 0.3)
        if face == "north" and fy == 1 and fx in (1, fw - 2):
            return shade(crystal, 0.5)   # eyes
        return base

    paint_box(c, 0, 18, 6, 3, 3, head)

    def spine(_face, fx, fy, fw, fh):
        t = 1.0 - fy / float(max(1, fh - 1))
        return mix(chitin, crystal, min(1.0, t * 1.15))

    paint_box(c, 20, 18, 4, 4, 1, spine)
    paint_box(c, 32, 18, 2, 3, 1, spine)

    def leg(_face, fx, fy, fw, fh):
        return mix(chitin_hi, chitin, fy / float(max(1, fh - 1)))

    for u, v in ((42, 0), (42, 6), (42, 12), (48, 0), (48, 6), (48, 12)):
        paint_box(c, u, v, 1, 4, 1, leg)

    emit(c, ENTITY, "voidbound_crystal_crawler", roughness=224,
         emissive_from=crystal[:3], emissive_gain=1.0, emissive_threshold=0.26)


# --------------------------------------------------------------------------
# The Rift Sovereign and its particles
# --------------------------------------------------------------------------

PARTICLE = os.path.join(ROOT, "RP", "textures", "particle")


def particle_atlas():
    """A 64x64 sheet of four 16x16 particle cells.

    Cell layout, referenced by uv in the particle JSON:
      (0,0)   soft glow      (16,0)  four-point spark
      (0,16)  crystal shard  (16,16) smoke puff
    """
    c = Canvas(64, 64)
    white = (255, 255, 255, 255)

    # Soft radial glow - tinted at runtime, so authored white.
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8) / 7.5
            if d <= 1.0:
                a = int(255 * (1.0 - d) ** 2.0)
                c.set(x, y, (255, 255, 255, a))

    # Spark: a bright core with four tapering arms.
    for i in range(8):
        a = int(255 * (1.0 - i / 8.0) ** 1.4)
        c.set(16 + 8 + i, 8, (255, 255, 255, a))
        c.set(16 + 8 - i, 8, (255, 255, 255, a))
        c.set(16 + 8, 8 + i, (255, 255, 255, a))
        c.set(16 + 8, 8 - i, (255, 255, 255, a))
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
        c.set(16 + 8 + dx, 8 + dy, white)

    # Crystal shard: a small faceted diamond.
    for y in range(16):
        for x in range(16):
            if abs(x - 8) + abs(y - 8) * 0.7 <= 5:
                edge = (abs(x - 8) + abs(y - 8) * 0.7) / 5.0
                c.set(x, 16 + y, (255, 255, 255, int(255 * (1.0 - edge * 0.45))))

    # Smoke puff: soft noise blob.
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8) / 8.0
            n = fbm(x * 2, y * 2, 16, 6060, octaves=3, base_period=4)
            a = max(0.0, (1.0 - d) * (0.45 + n * 0.55))
            if a > 0.03:
                c.set(16 + x, 16 + y, (255, 255, 255, int(min(255, a * 210))))

    os.makedirs(PARTICLE, exist_ok=True)
    out(c, PARTICLE, "voidbound_particles")


# Boss UV layout on a 128x128 sheet, kept here so the geometry and the painter
# cannot drift apart.
SOVEREIGN_PARTS = [
    ("core", 0, 0, 10, 10, 10),
    ("shell_upper", 0, 22, 16, 6, 16),
    ("shell_lower", 0, 46, 16, 6, 16),
    ("spike_a", 66, 0, 2, 8, 2),
    ("spike_b", 66, 12, 2, 8, 2),
    ("spike_c", 66, 24, 2, 8, 2),
    ("spike_d", 66, 36, 2, 8, 2),
    ("mantle", 66, 48, 12, 14, 2),
    ("shard_a", 96, 0, 3, 3, 3),
    ("shard_b", 96, 10, 3, 3, 3),
    ("shard_c", 96, 20, 3, 3, 3),
    ("shard_d", 96, 30, 3, 3, 3),
    ("eye", 76, 66, 6, 2, 1),
]


def entity_rift_sovereign():
    """128x128 sheet: black basalt regalia around a magenta rift core."""
    c = Canvas(128, 128)
    regalia = mix(PALETTE["void"], (0, 0, 0, 255), 0.52)
    regalia_hi = mix(regalia, hex_rgba("#E56BD8"), 0.30)
    gold = hex_rgba("#C9A85C")
    core_hot = hex_rgba("#FFE4FA")
    core_mid = hex_rgba("#E75BE0")
    core_deep = hex_rgba("#5A0F7A")

    def paint_core(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.1)
        n = fbm(fx * 2.4, fy * 2.4, 16, 9001, octaves=3, base_period=4)
        t = min(1.0, d * 0.8 + n * 0.28)
        return mix(core_hot, mix(core_mid, core_deep, t), min(1.0, t * 1.25))

    def paint_shell(seed, banded):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.3, fy * 1.3, 16, seed, octaves=3, base_period=4)
            base = mix(regalia, shade(regalia, 0.30), n)
            if face == "top":
                base = shade(base, 0.14)
            elif face == "bottom":
                base = shade(base, -0.24)
            # Inlaid gold banding around the rim of each shell.
            if banded and face in ("north", "south", "east", "west"):
                if fy == 1 or fy == fh - 2:
                    return mix(base, gold, 0.65)
                if fx % 4 == 0:
                    return mix(base, regalia_hi, 0.5)
            return base
        return paint

    def paint_spike(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(mix(core_mid, gold, 0.35), regalia, min(1.0, t * 1.2))

    def paint_mantle(face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        n = fbm(fx * 2, fy * 2, 16, 9100, octaves=2, base_period=4)
        base = mix(regalia, shade(regalia, 0.22), n * 0.6)
        # The hem burns out into rift light.
        if t > 0.62:
            return mix(base, core_mid, (t - 0.62) / 0.38 * 0.9)
        if face in ("north", "south") and fx % 3 == 0:
            return mix(base, regalia_hi, 0.35)
        return base

    def paint_shard(_face, fx, fy, fw, fh):
        t = (fx + fy) / float(max(1, fw + fh - 2))
        return mix(shade(core_mid, 0.4), core_deep, t)

    def paint_eye(_face, fx, fy, fw, fh):
        return mix(core_hot, core_mid, fx / float(max(1, fw - 1)))

    painters = {
        "core": paint_core,
        "shell_upper": paint_shell(9010, True),
        "shell_lower": paint_shell(9011, True),
        "mantle": paint_mantle,
        "eye": paint_eye,
    }
    for part, u, v, w, h, d in SOVEREIGN_PARTS:
        if part.startswith("spike"):
            painter = paint_spike
        elif part.startswith("shard"):
            painter = paint_shard
        else:
            painter = painters[part]
        paint_box(c, u, v, w, h, d, painter)

    emit(
        c,
        ENTITY,
        "voidbound_rift_sovereign",
        metalness=72,
        roughness=96,
        emissive_from=core_mid[:3],
        emissive_gain=1.45,
        emissive_threshold=0.12,
    )


# --------------------------------------------------------------------------
# The End sky
# --------------------------------------------------------------------------

ENVIRONMENT = os.path.join(ROOT, "RP", "textures", "environment")


def end_sky():
    """Replace the End's skybox tile: textures/environment/end_sky.png.

    Vibrant Visuals will not let a pack supply a cubemap for the End - Mojang
    restricts that to the Overworld - but the skybox is an ordinary vanilla
    texture, so overriding it changes the End's sky whether or not Vibrant
    Visuals is switched on.

    The hard constraint is tiling. The game repeats this 128px tile many times
    across every face of the skybox, so anything with large features or strong
    contrast turns into visible wallpaper. Vanilla's own End sky is nearly
    black for exactly this reason. So: a very dark base, dust variation held
    under about 8% brightness, and stars doing all the visible work - points
    small and sparse enough that the eye reads a starfield rather than a
    repeat.
    """
    size = 128
    c = Canvas(size, size)

    base = hex_rgba("#0A0414")
    dust = hex_rgba("#241043")

    for y in range(size):
        for x in range(size):
            # Two low-frequency octaves only, at low amplitude. Enough to stop
            # the sky reading as flat black, not enough to tile visibly.
            haze = fbm(x, y, size, 2201, octaves=2, base_period=2, gain=0.5)
            c.set(x, y, mix(base, dust, max(0.0, (haze - 0.42)) * 0.55))

    rng = Rng(31337)

    # Faint background field: many dim points, no halo.
    for _ in range(620):
        sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
        v = rng.range(0.10, 0.34)
        c.set(sx, sy, mix(c.get(sx, sy), hex_rgba("#CBB8E8"), v))

    # Mid field: visible but still small.
    for _ in range(150):
        sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
        tint = mix(hex_rgba("#FFFFFF"), hex_rgba("#E0A8F0"), rng.range(0.0, 0.5))
        c.set(sx, sy, mix(c.get(sx, sy), tint, rng.range(0.5, 0.8)))

    # A handful of bright stars with a one-pixel halo, no cross flares - flares
    # repeat conspicuously once the tile is laid out dozens of times.
    for _ in range(26):
        sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
        tint = mix(hex_rgba("#FFFFFF"), hex_rgba("#F0C8FF"), rng.range(0.0, 0.4))
        c.set(sx, sy, tint)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = (sx + dx) % size, (sy + dy) % size
            c.set(nx, ny, mix(c.get(nx, ny), tint, 0.22))

    os.makedirs(ENVIRONMENT, exist_ok=True)
    out(c, ENVIRONMENT, "end_sky")


# --------------------------------------------------------------------------
# Pack icons
# --------------------------------------------------------------------------


def pack_icon(path, accent):
    """128x128 emblem: a torn rift over the void, ringed by an End horizon."""
    size = 128
    c = Canvas(size, size)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - 64, y - 64) / 78.0
            n = fbm(x * 0.25, y * 0.25, size, 909, octaves=4, base_period=8)
            base = mix(hex_rgba("#150C2E"), hex_rgba("#05030C"), min(1.0, d * 1.15))
            c.set(x, y, shade(base, (n - 0.5) * 0.22))
    # Horizon glow.
    radial(c, 64, 92, 74, (accent[0], accent[1], accent[2], 90), (0, 0, 0, 0), falloff=1.6)
    # The rift: a vertical tear with ragged edges and a white-hot centre.
    rng = Rng(4242)
    half = []
    width = 0.0
    for y in range(18, 110):
        t = (y - 18) / 92.0
        width = 13.0 * math.sin(math.pi * t) ** 1.35 + rng.range(-0.7, 0.7)
        half.append((y, max(0.6, width)))
    for y, w in half:
        for x in range(int(64 - w), int(64 + w) + 1):
            e = abs(x - 64) / w
            color = mix((255, 255, 255, 255), accent, min(1.0, e ** 0.65))
            c.blend(x, y, mix(color, (accent[0], accent[1], accent[2], 0), max(0.0, (e - 0.75) / 0.25)))
    for y, w in half:
        for side in (-1, 1):
            gx = 64 + side * (w + rng.range(0.5, 3.0))
            c.blend(int(gx), y, (accent[0], accent[1], accent[2], 120))
    # Floating shards to sell the scale.
    for _ in range(26):
        sx, sy = rng.range(8, 120), rng.range(8, 120)
        if abs(sx - 64) < 20:
            continue
        s = rng.int(1, 3)
        col = mix(accent, hex_rgba("#DCE0A8"), rng.range(0.0, 0.6))
        for oy in range(s):
            for ox in range(s):
                c.blend(int(sx) + ox, int(sy) + oy, (col[0], col[1], col[2], 210))
    c.save(path)


# --------------------------------------------------------------------------


def main():
    for folder in (BLOCKS, ITEMS, ENTITY, ARMOR, ENVIRONMENT, PARTICLE):
        os.makedirs(folder, exist_ok=True)

    recipes = [
        block_shattered_end_stone,
        block_verdant_end_stone,
        block_echo_ore,
        block_void_crystal,
        block_void_glass,
        block_voidbloom,
        block_lumen_bulb,
        block_rift_lantern,
        item_echo_shard,
        item_void_crystal,
        item_rift_compass,
        item_lumen_berry,
        entity_lumen_wisp,
        entity_rift_stalker,
        entity_void_moth,
        entity_echo_sentinel,
        entity_chorus_hopper,
        entity_shard_wraith,
        entity_crystal_crawler,
        entity_rift_sovereign,
        particle_atlas,
        armor_layers,
        item_void_helmet,
        item_void_chestplate,
        item_void_leggings,
        item_void_boots,
        end_sky,
    ]
    for recipe in recipes:
        recipe()
        print("  generated", recipe.__name__)

    pack_icon(os.path.join(ROOT, "BP", "pack_icon.png"), PALETTE["void_lit"])
    pack_icon(os.path.join(ROOT, "RP", "pack_icon.png"), PALETTE["lumen_lit"])
    print("  generated pack icons")

    total = sum(
        len([f for f in os.listdir(d) if f.endswith(".png")]) for d in (BLOCKS, ITEMS, ENTITY, ARMOR, ENVIRONMENT, PARTICLE)
    )
    print(f"{total} texture files written")


if __name__ == "__main__":
    main()
