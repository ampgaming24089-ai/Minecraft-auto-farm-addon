#!/usr/bin/env python3
"""Regenerate every End Everlasting texture from source.

    python3 tools/gen_art.py

No arguments, no dependencies, no network. Output is byte-for-byte identical on
every run, so regenerating produces an empty diff unless a recipe actually
changed. Each recipe below is authored as "what is this material made of",
and the matching MER map is derived from the albedo rather than painted twice.
"""

import inspect
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artlib import (  # noqa: E402
    TRANSPARENT,
    Canvas,
    canvas_from_png,
    recolour,
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


def _mobkit_owned():
    """Entity textures produced by the mob pipeline, not by this file.

    Two generators writing the same PNG is a bug with no symptom until you
    look at a render: whichever ran last wins, silently. It happened - a
    retired `entity_echo_warden` recipe in here kept overwriting the one
    tools/mobs/echo_warden_paint.py had just produced, and the boss was
    wearing a flat texture painted for a body it no longer had.

    So ownership is asserted rather than remembered. Every tools/mobs/*_paint.py
    claims `voidbound_<name>`, and emit() refuses to write over the claim.
    """
    owned = set()
    mobs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobs")
    if not os.path.isdir(mobs):
        return owned
    for entry in os.listdir(mobs):
        if entry.endswith("_paint.py"):
            owned.add("voidbound_" + entry[: -len("_paint.py")])
    return owned


MOBKIT_OWNED = _mobkit_owned()


def emit(albedo, folder, name, **mer_kwargs):
    """Write an albedo texture, its MER companion, and the set that binds them.

    The texture set is the part that is easy to forget and impossible to see
    missing: a `_mer.png` with no `.texture_set.json` beside it is a file the
    game never opens. Everything still renders - just flat, with no metalness,
    no roughness and, most visibly, no glow at all. Writing all three here
    means that cannot drift apart again.
    """
    if folder == ENTITY and name in MOBKIT_OWNED:
        # The owner itself is of course allowed to write it; what is being
        # caught is any *other* caller doing so.
        caller = inspect.currentframe().f_back.f_globals.get("__file__", "")
        expected = "%s_paint.py" % name[len("voidbound_"):]
        if os.path.basename(caller) != expected:
            raise SystemExit(
                "%s tried to write %s, which tools/mobs/%s owns.\n"
                "  Two generators writing one texture means the last to run\n"
                "  wins and nothing says so. Delete the other recipe."
                % (os.path.basename(caller) or "something", name, expected))
    out(albedo, folder, name)
    if not mer_kwargs.pop("mer", True):
        return
    make_mer(albedo, **mer_kwargs).save(os.path.join(folder, name + "_mer.png"))
    with open(os.path.join(folder, name + ".texture_set.json"), "w") as handle:
        json.dump({
            "format_version": "1.16.100",
            "minecraft:texture_set": {
                "color": name,
                "metalness_emissive_roughness": name + "_mer",
            },
        }, handle, indent=2)
        handle.write("\n")


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


def item_raw_haunch():
    """Pale meat with a violet cast - it came off something from the End."""
    c = Canvas(16)
    meat = hex_rgba("#B9668F")
    meat_dark = mix(meat, PALETTE["void"], 0.45)
    fat = hex_rgba("#E8C4D8")
    bone = hex_rgba("#EDE6DC")
    for y in range(4, 14):
        for x in range(2, 13):
            d = math.hypot((x - 7.5) / 5.5, (y - 9) / 4.5)
            if d > 1.0:
                continue
            n = fbm(x * 2, y * 2, 16, 5150, octaves=3, base_period=4)
            c.set(x, y, mix(meat, meat_dark, min(1.0, d * 0.8 + n * 0.3)))
    for x in range(4, 11):
        c.blend(x, 6, mix(fat, meat, 0.3))
    for y in range(2, 6):
        c.set(9, y, bone)
        c.set(10, y, mix(bone, meat_dark, 0.3))
    c.set(9, 1, bone)
    c.set(10, 1, bone)
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(c, ITEMS, "voidbound_raw_haunch", roughness=200)


def item_cooked_haunch():
    """The same cut, seared."""
    c = Canvas(16)
    meat = hex_rgba("#8A4A32")
    meat_dark = mix(meat, (0, 0, 0, 255), 0.4)
    crust = hex_rgba("#C98A4C")
    bone = hex_rgba("#EDE6DC")
    for y in range(4, 14):
        for x in range(2, 13):
            d = math.hypot((x - 7.5) / 5.5, (y - 9) / 4.5)
            if d > 1.0:
                continue
            n = fbm(x * 2, y * 2, 16, 5151, octaves=3, base_period=4)
            base = mix(meat, meat_dark, min(1.0, d * 0.75 + n * 0.35))
            c.set(x, y, mix(base, crust, max(0.0, 0.55 - d) * 0.9))
    for y in range(2, 6):
        c.set(9, y, bone)
        c.set(10, y, mix(bone, meat_dark, 0.3))
    c.set(9, 1, bone)
    c.set(10, 1, bone)
    bevel(c)
    c.outline(mix(hex_rgba("#2A1408"), (0, 0, 0, 255), 0.3))
    emit(c, ITEMS, "voidbound_cooked_haunch", roughness=190)


def item_echo_bread():
    """A dense loaf pressed from lumen berries - the travel ration."""
    c = Canvas(16)
    crust = hex_rgba("#8C7A4E")
    crust_hi = hex_rgba("#C4B075")
    berry = PALETTE["lumen_lit"]
    for y in range(5, 13):
        for x in range(2, 14):
            d = math.hypot((x - 8) / 6.2, (y - 9) / 4.0)
            if d > 1.0:
                continue
            n = fbm(x * 2.2, y * 2.2, 16, 6262, octaves=3, base_period=4)
            c.set(x, y, mix(crust_hi, crust, min(1.0, d * 0.7 + n * 0.4)))
    # Berries showing through the crust.
    for bx, by in ((5, 8), (9, 7), (11, 10), (7, 11)):
        c.blend(bx, by, berry)
        c.blend(bx + 1, by, mix(berry, crust, 0.45))
    for x in range(4, 12, 3):
        c.blend(x, 6, mix(crust, (0, 0, 0, 255), 0.25))
    bevel(c)
    c.outline(mix(hex_rgba("#3A2E16"), (0, 0, 0, 255), 0.3))
    emit(c, ITEMS, "voidbound_echo_bread", roughness=214,
         emissive_from=berry[:3], emissive_gain=0.8, emissive_threshold=0.3)


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


# --------------------------------------------------------------------------
# Tools and armour: recoloured vanilla art
# --------------------------------------------------------------------------

VANILLA_REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vanilla_refs")

# The brief was "a reskin of the classic sword, tools and armour", and the eye
# knows those silhouettes far too well for a hand-drawn approximation to pass -
# an earlier pass tried and every shape read as almost-but-not-quite. So the
# real vanilla textures are recoloured instead: the shape, shading and outline
# are Mojang's, only the metal's hue changes.
#
# Diamond is the donor. Its metal sits at hue 180 and its wooden handles at
# hue 30, which separates cleanly, so a hue window over the metal leaves the
# sticks untouched.
METAL_HUES = (150.0 / 360.0, 210.0 / 360.0)
TOOL_METAL = hex_rgba("#9B5FD6")
ARMOR_METAL = hex_rgba("#7A4CB8")


def _require_ref(filename):
    path = os.path.join(VANILLA_REFS, filename)
    if not os.path.exists(path):
        raise SystemExit(
            "missing %s\n  run: python3 tools/fetch_vanilla_refs.py" % os.path.relpath(path, ROOT)
        )
    return path


def tool_set():
    """Five tools, recoloured from vanilla diamond so the shapes are exact."""
    for vanilla, name in (
        ("diamond_sword.png", "void_sword"),
        ("diamond_pickaxe.png", "void_pickaxe"),
        ("diamond_axe.png", "void_axe"),
        ("diamond_shovel.png", "void_shovel"),
        ("diamond_hoe.png", "void_hoe"),
    ):
        c = canvas_from_png(_require_ref(vanilla))
        recolour(c, TOOL_METAL, hue_window=METAL_HUES, value_scale=0.94)
        emit(
            c, ITEMS, "voidbound_%s" % name,
            metalness=96, roughness=84,
            emissive_from=TOOL_METAL[:3], emissive_gain=0.55, emissive_threshold=0.55,
        )


def armor_layers():
    """Both armour layers, recoloured from vanilla diamond."""
    os.makedirs(ARMOR, exist_ok=True)
    for vanilla, name in (
        ("diamond_1.png", "voidbound_armor_1"),
        ("diamond_2.png", "voidbound_armor_2"),
    ):
        c = canvas_from_png(_require_ref(vanilla))
        # No hue window here: armour layers are all metal.
        recolour(c, ARMOR_METAL, value_scale=0.92)
        emit(
            c, ARMOR, name,
            metalness=72, roughness=104,
            emissive_from=ARMOR_METAL[:3], emissive_gain=0.5, emissive_threshold=0.62,
        )


# --------------------------------------------------------------------------
# Armor
# --------------------------------------------------------------------------

ARMOR = os.path.join(ROOT, "RP", "textures", "models", "armor")

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


def item_gameplay_set():
    """The three utility items, plus the decorative block variants."""
    # Rift Charm: a bound loop of crystal on a cord.
    charm = Canvas(16)
    cord = mix(PALETTE["void"], hex_rgba("#8A7BA8"), 0.4)
    ring = PALETTE["void_lit"]
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 9)
            if 3.4 <= d <= 5.4:
                charm.set(x, y, mix(ring, PALETTE["void"], (d - 3.4) / 2.0 * 0.8))
    for i in range(4):
        charm.set(8, 2 + i, cord)
        charm.set(9, 2 + i, shade(cord, -0.25))
    charm.set(7, 1, cord); charm.set(8, 1, cord); charm.set(9, 1, cord)
    radial(charm, 8, 9, 3.0, mix(ring, (255, 255, 255, 255), 0.5), (0, 0, 0, 0), falloff=1.6)
    bevel(charm)
    charm.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.65))
    emit(charm, ITEMS, "voidbound_rift_charm", metalness=120, roughness=70,
         emissive_from=ring[:3], emissive_gain=1.25, emissive_threshold=0.22)

    # Echo Horn: a curled shell horn with a lit mouth.
    horn = Canvas(16)
    shell = hex_rgba("#C6BE94")
    shell_lo = mix(shell, PALETTE["void"], 0.45)
    mouth = PALETTE["lumen_lit"]
    for i in range(11):
        t = i / 10.0
        cx = 3 + i * 0.95
        cy = 12 - i * 0.75
        width = 1.0 + t * 2.6
        for dy in range(-int(width), int(width) + 1):
            for dx in range(-int(width), int(width) + 1):
                if dx * dx + dy * dy <= width * width:
                    horn.set(int(cx) + dx, int(cy) + dy, mix(shell_lo, shell, 1.0 - t * 0.5))
    radial(horn, 12.5, 4.5, 3.2, mouth, mix(shell, mouth, 0.2), falloff=1.5)
    speckle(horn, 9601, 0.06, [shade(shell, 0.25), shade(shell_lo, -0.2)])
    bevel(horn)
    horn.outline(mix(hex_rgba("#3A3418"), (0, 0, 0, 255), 0.35))
    emit(horn, ITEMS, "voidbound_echo_horn", roughness=170,
         emissive_from=mouth[:3], emissive_gain=1.1, emissive_threshold=0.28)

    # Ender Fruit Pie.
    pie = Canvas(16)
    crust = hex_rgba("#C4A96A")
    crust_lo = mix(crust, hex_rgba("#6B5730"), 0.5)
    filling = hex_rgba("#3FE0C4")
    pie.rect(2, 6, 13, 13, crust)
    for x in range(2, 14):
        pie.set(x, 6, mix(crust, (255, 255, 255, 255), 0.25))
        pie.set(x, 13, crust_lo)
    pie.rect(3, 7, 12, 10, filling)
    for x in range(3, 13, 2):
        pie.set(x, 8, mix(filling, (255, 255, 255, 255), 0.4))
    for x in range(2, 14, 3):
        pie.set(x, 11, crust_lo)
    bevel(pie)
    pie.outline(mix(hex_rgba("#3A2E16"), (0, 0, 0, 255), 0.35))
    emit(pie, ITEMS, "voidbound_ender_fruit_pie", roughness=204,
         emissive_from=filling[:3], emissive_gain=0.8, emissive_threshold=0.3)


def block_decor_set():
    """Chiselled bricks, a pillar and tiles - the finishing blocks."""
    brick = mix(PALETTE["endstone_dark"], hex_rgba("#CFC8A4"), 0.5)
    brick_lo = mix(brick, PALETTE["void"], 0.4)
    mortar = mix(brick_lo, (0, 0, 0, 255), 0.35)
    lit = PALETTE["void_lit"]

    chiselled = Canvas(16)

    def chisel(x, y, _cur):
        n = fbm(x * 1.8, y * 1.8, 16, 9610, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if x in (0, 15) or y in (0, 15):
            return mortar
        # An inset panel with a rift glyph cut into it.
        if 2 <= x <= 13 and 2 <= y <= 13:
            if x in (2, 13) or y in (2, 13):
                return shade(base, -0.28)
            on_glyph = abs(x - 8) + abs(y - 8) in (2, 5) or (x == 8 and 4 <= y <= 12)
            if on_glyph:
                return mix(base, lit, 0.55)
        return base

    chiselled.each(chisel)
    emit(chiselled, BLOCKS, "voidbound_chiseled_ender_bricks", roughness=236,
         emissive_from=lit[:3], emissive_gain=0.7, emissive_threshold=0.36)

    pillar = Canvas(16)

    def pillar_face(x, y, _cur):
        n = fbm(x * 2.6, y * 0.9, 16, 9620, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if x in (0, 1, 14, 15):
            return shade(base, -0.26)             # fluted edges
        if y in (0, 15):
            return mortar                          # collar
        if x in (5, 10):
            return shade(base, -0.16)
        return base

    pillar.each(pillar_face)
    emit(pillar, BLOCKS, "voidbound_ender_pillar", roughness=238)

    pillar_top = Canvas(16)

    def pillar_cap(x, y, _cur):
        d = max(abs(x - 7.5), abs(y - 7.5))
        n = fbm(x * 2, y * 2, 16, 9621, octaves=2, base_period=4)
        base = mix(brick_lo, brick, n)
        if d > 6.2:
            return mortar
        if d > 4.4:
            return shade(base, -0.2)
        return mix(base, lit, 0.18)

    pillar_top.each(pillar_cap)
    emit(pillar_top, BLOCKS, "voidbound_ender_pillar_top", roughness=234,
         emissive_from=lit[:3], emissive_gain=0.55, emissive_threshold=0.42)

    tiles = Canvas(16)

    def tile_face(x, y, _cur):
        n = fbm(x * 2.2, y * 2.2, 16, 9630, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if x % 8 == 0 or y % 8 == 0:
            return mortar
        if (x // 8 + y // 8) % 2 == 0:
            return shade(base, 0.12)
        return shade(base, -0.10)

    tiles.each(tile_face)
    speckle(tiles, 9631, 0.05, [shade(brick, 0.22), shade(brick_lo, -0.2)])
    emit(tiles, BLOCKS, "voidbound_ender_tiles", roughness=240)


# --------------------------------------------------------------------------
# The End forest
# --------------------------------------------------------------------------


def block_ender_log():
    """Pale, chalky bark with dark rift seams running the grain."""
    bark = hex_rgba("#6E5F86")
    bark_lo = mix(bark, PALETTE["void"], 0.55)
    bark_hi = mix(bark, hex_rgba("#CFC4E2"), 0.45)
    seam = mix(PALETTE["void_lit"], PALETTE["void"], 0.35)

    side = Canvas(16)

    def grain(x, y, _cur):
        # Vertical grain: noise stretched hard on x so it reads as fibre.
        n = fbm(x * 3.4, y * 0.7, 16, 7300, octaves=3, base_period=4)
        base = mix(bark_lo, bark, n)
        if n > 0.62:
            base = mix(base, bark_hi, (n - 0.62) / 0.38 * 0.8)
        return base

    side.each(grain)
    veins(side, 7301, 2, seam, 18, wobble=0.25, width=1)
    emit(side, BLOCKS, "voidbound_ender_log", roughness=236,
         emissive_from=seam[:3], emissive_gain=0.55, emissive_threshold=0.42)

    top = Canvas(16)

    def rings(x, y, _cur):
        d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
        n = fbm(x * 2, y * 2, 16, 7302, octaves=2, base_period=4)
        ring = (math.sin(d * 2.1 + n * 1.4) + 1) * 0.5
        return mix(bark_lo, bark_hi, ring * 0.75)

    top.each(rings)
    radial(top, 8, 8, 2.2, seam, mix(bark, seam, 0.2), falloff=1.4)
    emit(top, BLOCKS, "voidbound_ender_log_top", roughness=232,
         emissive_from=seam[:3], emissive_gain=0.6, emissive_threshold=0.4)


def block_ender_leaves():
    """Airy violet canopy - alpha-tested, so it needs real holes."""
    c = Canvas(16)
    leaf = hex_rgba("#7B3FA8")
    leaf_lo = mix(leaf, PALETTE["void"], 0.5)
    leaf_hi = mix(leaf, hex_rgba("#D8A8F0"), 0.5)

    def canopy(x, y, _cur):
        n = fbm(x * 2.6, y * 2.6, 16, 7310, octaves=3, base_period=4)
        clump = fbm(x * 1.2, y * 1.2, 16, 7311, octaves=2, base_period=4)
        if clump < 0.36:
            return TRANSPARENT          # gaps you can see sky through
        base = mix(leaf_lo, leaf, n)
        if n > 0.66:
            return mix(base, leaf_hi, (n - 0.66) / 0.34)
        return base

    c.each(canopy)
    speckle(c, 7312, 0.05, [leaf_hi, shade(leaf_lo, -0.25)])
    emit(c, BLOCKS, "voidbound_ender_leaves", roughness=222,
         emissive_from=leaf_hi[:3], emissive_gain=0.45, emissive_threshold=0.5)


def block_ender_bush():
    """Low bush carrying ripe fruit - the ground-level source."""
    c = Canvas(16)
    stem = mix(PALETTE["void"], hex_rgba("#7B6A92"), 0.55)
    leaf = hex_rgba("#6E3A96")
    leaf_hi = mix(leaf, hex_rgba("#C89AE8"), 0.5)
    fruit = hex_rgba("#3FE0C4")

    rng = Rng(7320)
    for base_x in (4, 8, 11):
        px = base_x
        for y in range(15, 8, -1):
            px += rng.range(-0.3, 0.3)
            c.blend(int(round(px)), y, stem)
    for cx, cy, r in ((5, 8, 3.2), (9, 6, 3.6), (11, 9, 2.8)):
        for y in range(16):
            for x in range(16):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
                if d <= 1.0 and rng.next() > d * 0.55:
                    c.blend(x, y, mix(leaf_hi, leaf, min(1.0, d * 1.1)))
    for fx, fy in ((5, 9), (10, 6), (12, 10)):
        c.blend(fx, fy, fruit)
        c.blend(fx + 1, fy, mix(fruit, leaf, 0.4))
        c.blend(fx, fy + 1, mix(fruit, leaf, 0.55))
    emit(c, BLOCKS, "voidbound_ender_bush", roughness=200,
         emissive_from=fruit[:3], emissive_gain=1.15, emissive_threshold=0.2)


def item_ender_fruit():
    """A dense teal fruit with a pale rind seam."""
    c = Canvas(16)
    flesh = hex_rgba("#3FE0C4")
    flesh_deep = mix(flesh, PALETTE["void"], 0.55)
    rind = hex_rgba("#DFF7F0")
    radial(c, 7.6, 9.0, 5.6, flesh, flesh_deep, falloff=1.2)
    radial(c, 5.8, 7.0, 2.2, rind, (63, 224, 196, 0), falloff=1.1)
    for y in range(5, 14):
        c.blend(11, y, mix(rind, flesh_deep, 0.45))
    for y in range(2, 6):
        c.set(9, y, mix(PALETTE["void"], hex_rgba("#7B6A92"), 0.5))
    c.set(10, 2, mix(flesh, rind, 0.4))
    c.set(8, 2, mix(flesh, rind, 0.4))
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(c, ITEMS, "voidbound_ender_fruit", roughness=140,
         emissive_from=flesh[:3], emissive_gain=1.2, emissive_threshold=0.18)


def item_sovereign_crown():
    """The Sovereign's crown - the reason to fight it twice."""
    c = Canvas(16)
    gold = hex_rgba("#E8C766")
    gold_lo = hex_rgba("#8A6E28")
    gem = hex_rgba("#E75BE0")
    for x in range(2, 14):
        c.set(x, 10, gold)
        c.set(x, 11, gold_lo)
    # Five points, tallest in the centre.
    for x, height in ((2, 6), (5, 4), (8, 2), (11, 4), (13, 6)):
        for y in range(height, 10):
            c.set(x, y, gold if y > height else mix(gold, rind_white(), 0.35))
            c.set(x + 1, y, gold_lo)
    for gx, gy in ((3, 8), (8, 5), (12, 8)):
        c.set(gx, gy, gem)
        c.blend(gx + 1, gy, mix(gem, gold, 0.5))
    c.set(8, 4, shade(gem, 0.5))
    bevel(c, light=0.3, dark=0.28)
    c.outline(mix(hex_rgba("#3A2A08"), (0, 0, 0, 255), 0.35))
    emit(c, ITEMS, "voidbound_sovereign_crown", metalness=190, roughness=52,
         emissive_from=gem[:3], emissive_gain=1.2, emissive_threshold=0.3)


def rind_white():
    return hex_rgba("#FFF4CC")


def block_building_set():
    """Four worked blocks, so the End's materials can actually be built with."""
    # Planks: milled ender log, grain running one way.
    planks = Canvas(16)
    plank = hex_rgba("#7E6D96")
    plank_lo = mix(plank, PALETTE["void"], 0.45)
    plank_hi = mix(plank, hex_rgba("#D2C6E4"), 0.4)

    def plank_face(x, y, _cur):
        row = y // 4
        n = fbm(x * 3.0, y * 0.8, 16, 9400 + row * 31, octaves=3, base_period=4)
        base = mix(plank_lo, plank, n)
        if n > 0.66:
            base = mix(base, plank_hi, (n - 0.66) / 0.34 * 0.7)
        if y % 4 == 0:
            return shade(base, -0.30)              # board seam
        # Stagger the butt joints like vanilla planks do.
        if (x + row * 5) % 8 == 0:
            return shade(base, -0.20)
        return base

    planks.each(plank_face)
    emit(planks, BLOCKS, "voidbound_ender_planks", roughness=238)

    # Ender bricks: coursed masonry from shattered end stone.
    bricks = Canvas(16)
    brick = mix(PALETTE["endstone_dark"], hex_rgba("#CFC8A4"), 0.5)
    brick_lo = mix(brick, PALETTE["void"], 0.4)
    mortar = mix(brick_lo, (0, 0, 0, 255), 0.35)

    def brick_face(x, y, _cur):
        row = y // 4
        n = fbm(x * 1.8, y * 1.8, 16, 9410, octaves=3, base_period=4)
        if y % 4 == 0:
            return mortar
        if (x + row * 4) % 8 == 0:
            return mortar
        return mix(brick_lo, brick, n)

    bricks.each(brick_face)
    speckle(bricks, 9411, 0.05, [shade(brick, 0.2), shade(brick_lo, -0.2)])
    emit(bricks, BLOCKS, "voidbound_ender_bricks", roughness=242)

    # Crystal bricks: cut void crystal, still lit from within.
    crystal = Canvas(16)
    deep = PALETTE["void"]
    lit = PALETTE["void_lit"]

    def crystal_face(x, y, _cur):
        row = y // 8
        n = fbm(x * 2.2, y * 2.2, 16, 9420, octaves=3, base_period=4)
        base = mix(deep, lit, min(1.0, n * 0.95))
        if y % 8 == 0 or (x + row * 4) % 8 == 0:
            return mix(shade(deep, -0.25), lit, 0.15)
        return base

    crystal.each(crystal_face)
    emit(crystal, BLOCKS, "voidbound_void_crystal_bricks", roughness=64,
         emissive_from=lit[:3], emissive_gain=0.95, emissive_threshold=0.24)

    # Echo lamp: a full-brightness lamp, the End's answer to glowstone.
    lamp = Canvas(16)
    frame = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.5)
    glow = PALETTE["lumen_lit"]
    lamp.fill(frame)
    for cx, cy in ((4, 4), (11, 4), (4, 11), (11, 11), (8, 8)):
        radial(lamp, cx + 0.5, cy + 0.5, 3.4, shade(glow, 0.45), frame, falloff=1.5)
    speckle(lamp, 9430, 0.06, [shade(glow, 0.6), shade(frame, -0.2)])
    emit(lamp, BLOCKS, "voidbound_echo_lamp", roughness=110,
         emissive_from=glow[:3], emissive_gain=1.5, emissive_threshold=0.1)


def entity_endstone_golem():
    """64x64: quarried end stone bound with crystal - a guardian, not a threat."""
    c = Canvas(64, 64)
    rock = mix(PALETTE["endstone"], PALETTE["endstone_dark"], 0.4)
    rock_lo = mix(rock, PALETTE["void"], 0.32)
    rock_hi = mix(rock, hex_rgba("#F2EFD0"), 0.4)
    binding = PALETTE["lumen_lit"]

    def stone(seed, bound=False):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.5, fy * 1.5, 16, seed, octaves=3, base_period=4)
            base = mix(rock_lo, rock, n)
            if n > 0.7:
                base = mix(base, rock_hi, (n - 0.7) / 0.3 * 0.85)
            # Cracks, filled with crystal where the stone was rebound.
            crack = fbm(fx * 3.2, fy * 3.2, 16, seed + 71, octaves=2, base_period=4)
            if crack > 0.76:
                return mix(base, binding, 0.75) if bound else shade(base, -0.35)
            if face == "bottom":
                return shade(base, -0.2)
            return base
        return paint

    paint_box(c, 0, 0, 10, 12, 8, stone(9520, bound=True))

    def head(face, fx, fy, fw, fh):
        base = stone(9521)(face, fx, fy, fw, fh)
        if face == "north" and fy in (2, 3) and fx in (1, fw - 2):
            return shade(binding, 0.45)          # eyes
        return base

    paint_box(c, 0, 22, 7, 6, 7, head)
    paint_box(c, 38, 0, 4, 12, 4, stone(9522, bound=True))
    paint_box(c, 38, 20, 4, 12, 4, stone(9523, bound=True))
    paint_box(c, 0, 37, 4, 8, 4, stone(9524))
    paint_box(c, 18, 37, 4, 8, 4, stone(9525))

    emit(c, ENTITY, "voidbound_endstone_golem", roughness=246,
         emissive_from=binding[:3], emissive_gain=0.95, emissive_threshold=0.3)


def entity_void_titan():
    """64x64: the golem's build in blackened, rift-bound stone."""
    c = Canvas(64, 64)
    rock = mix(PALETTE["void"], (0, 0, 0, 255), 0.32)
    rock_hi = mix(rock, hex_rgba("#9A88C0"), 0.5)
    core = hex_rgba("#FF4FD0")

    def stone(seed, bound=False):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.4, fy * 1.4, 16, seed, octaves=3, base_period=4)
            base = mix(rock, rock_hi, n * 0.8)
            crack = fbm(fx * 3.0, fy * 3.0, 16, seed + 97, octaves=2, base_period=4)
            if crack > 0.70:
                # Where a golem shows crystal, the Titan shows raw rift.
                return mix(base, core, 0.85) if bound else shade(base, -0.4)
            if face == "bottom":
                return shade(base, -0.24)
            return base
        return paint

    paint_box(c, 0, 0, 10, 12, 8, stone(9730, bound=True))

    def head(face, fx, fy, fw, fh):
        base = stone(9731, bound=True)(face, fx, fy, fw, fh)
        if face == "north" and fy in (1, 2, 3) and fx in (1, fw - 2):
            return shade(core, 0.55)
        return base

    paint_box(c, 0, 22, 7, 6, 7, head)
    paint_box(c, 38, 0, 4, 12, 4, stone(9732, bound=True))
    paint_box(c, 38, 20, 4, 12, 4, stone(9733, bound=True))
    paint_box(c, 0, 37, 4, 8, 4, stone(9734))
    paint_box(c, 18, 37, 4, 8, 4, stone(9735))

    emit(c, ENTITY, "voidbound_void_titan", roughness=214,
         emissive_from=core[:3], emissive_gain=1.4, emissive_threshold=0.18)


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

    The End sky is a cube, and the game tiles this one texture across all six
    faces. That creates two failure modes, and this pack hit both:

    - High-contrast, large features turn into visible wallpaper.
    - *Any* low-frequency variation makes each face average to a slightly
      different brightness, and the cube's edges become visible as seams.

    So there is no noise here at all. The base is a perfectly flat colour,
    which means every face averages identically and the corners disappear, and
    every bit of visible interest comes from stars. Movement comes from
    particles in front of the sky (see world/ambience.js), because Bedrock
    gives a pack no way to animate a skybox.

    Density is the whole game, and the first version got it badly wrong: 2358
    stars in a 128px tile is fourteen percent of every pixel, and at the
    distance a skybox is actually viewed that stops reading as stars and starts
    reading as film grain. A real night sky is mostly empty. So this is sparse
    - about three percent coverage - and it buys back the lost interest with
    *contrast* instead of count: a few genuinely bright stars with halos, over
    a scattering of faint ones, rather than a uniform wash of dim ones.
    """
    size = 128
    c = Canvas(size, size)
    # A saturated deep violet rather than near-black. The previous base lost
    # to any lit terrain in the same frame, which read as an empty sky rather
    # than a deep one. It still has to be perfectly flat: any low-frequency
    # variation makes the six cube faces average differently and the corners
    # appear as seams.
    c.fill(hex_rgba("#241145"))

    rng = Rng(31337)
    tints = [
        hex_rgba("#FFFFFF"), hex_rgba("#F4E8FF"), hex_rgba("#D6C2FF"),
        hex_rgba("#A9D8FF"), hex_rgba("#FFC2E8"), hex_rgba("#FFE7C2"),
    ]

    # Three tiers, faintest first so brighter stars land on top. The faint tier
    # is the one that turns into grain, so it is the one kept smallest.
    for count, low, high in ((300, 0.10, 0.24), (110, 0.30, 0.52), (34, 0.60, 0.86)):
        for _ in range(count):
            sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
            c.set(sx, sy, mix(c.get(sx, sy), rng.pick(tints), rng.range(low, high)))

    # The handful that carry the sky. Full brightness with a soft halo, few
    # enough that the halo never reads as a repeating shape across the tile.
    for _ in range(14):
        sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
        tint = rng.pick(tints)
        c.set(sx, sy, tint)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = (sx + dx) % size, (sy + dy) % size
            c.set(nx, ny, mix(c.get(nx, ny), tint, 0.34))
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = (sx + dx) % size, (sy + dy) % size
            c.set(nx, ny, mix(c.get(nx, ny), tint, 0.12))

    os.makedirs(ENVIRONMENT, exist_ok=True)
    out(c, ENVIRONMENT, "end_sky")


def moon_phases():
    """textures/environment/moon_phases.png - eight phases in a 4x2 grid.

    Bedrock lays the moon out exactly the way Java does, so this is one of the
    few sky textures that genuinely transfers. It is generated rather than
    borrowed: an End moon should not be a photograph of ours, and shipping
    someone else's art inside a redistributed add-on is a licensing problem
    rather than a technical one.

    The phase is not drawn as a crescent shape - it is drawn as a *terminator*,
    a moving line with the lit side falling off into shadow, because a hard
    crescent reads as a sticker and a soft one reads as a sphere.
    """
    cell = 64
    c = Canvas(cell * 4, cell * 2)

    body_lit = hex_rgba("#E8D8F4")
    body_mid = hex_rgba("#9C7ABE")
    body_dark = hex_rgba("#3A2456")
    halo = hex_rgba("#C08AF0")

    for phase in range(8):
        ox = (phase % 4) * cell
        oy = (phase // 4) * cell
        # Minecraft's order is full, waning gibbous, last quarter, waning
        # crescent, new, waxing crescent, first quarter, waxing gibbous. The
        # first attempt swept a cosine across and produced a sequence that
        # went nearly-dark, half, nearly-full, dark - which is not a lunar
        # month, it is a flicker. Each phase names its own terminator instead.
        WANING = {1: -0.5, 2: 0.0, 3: 0.5}
        WAXING = {5: -0.5, 6: 0.0, 7: 0.5}

        for y in range(cell):
            for x in range(cell):
                nx = (x + 0.5) / cell * 2 - 1
                ny = (y + 0.5) / cell * 2 - 1
                d = math.hypot(nx, ny)
                if d > 1.0:
                    # A soft violet halo just outside the disc.
                    if d < 1.18:
                        a = int(120 * (1.0 - (d - 1.0) / 0.18) ** 2)
                        c.set(ox + x, oy + y, (halo[0], halo[1], halo[2], a))
                    continue

                # Sphere shading: the limb darkens toward the edge.
                z = math.sqrt(max(0.0, 1.0 - d * d))
                lift = 0.35 + 0.65 * z

                # Craters, as circular depressions at fixed spots.
                crater = 0.0
                for cx, cy, cr in ((-0.32, -0.18, 0.30), (0.28, 0.34, 0.24),
                                   (0.10, -0.46, 0.18), (-0.50, 0.36, 0.20),
                                   (0.46, -0.28, 0.15), (-0.08, 0.10, 0.26)):
                    cd = math.hypot(nx - cx, ny - cy) / cr
                    if cd < 1.0:
                        crater = max(crater, (1.0 - cd) ** 0.6)
                grain = fbm(x * 0.9, y * 0.9, cell, 5150, octaves=4, base_period=8)

                tone = mix(body_mid, body_lit, lift * (0.55 + grain * 0.45))
                tone = mix(tone, body_dark, crater * 0.55)

                # The terminator is an ellipse, not a straight line: it is the
                # edge of a sphere seen at an angle, so it narrows toward the
                # poles. Softened over a band so it reads as a curve rather
                # than a cut.
                limb = math.sqrt(max(0.0, 1.0 - ny * ny))
                if phase == 0:
                    shadow = 0.0
                elif phase == 4:
                    shadow = 1.0
                elif phase in WANING:
                    shadow = max(0.0, min(1.0, (WANING[phase] * limb - nx) * 3.0 + 0.5))
                else:
                    shadow = max(0.0, min(1.0, (nx - WAXING[phase] * limb) * 3.0 + 0.5))
                tone = mix(tone, (10, 6, 20, 255), shadow * 0.94)
                c.set(ox + x, oy + y, tone)

    os.makedirs(ENVIRONMENT, exist_ok=True)
    out(c, ENVIRONMENT, "moon_phases")


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


def item_material_set():
    """The four new crafting materials, drawn as four different kinds of object.

    A shard, a plate, an ingot and a core need to be told apart at 16px in a
    hotbar, so each gets its own silhouette rather than its own hue.
    """
    # Astral Shard - a pale blue splinter, the whale's drop.
    c = Canvas(16)
    _shard_silhouette(
        c,
        [(9, 1), (13, 6), (10, 15), (6, 14), (4, 6)],
        hex_rgba("#BFEFFF"),
        hex_rgba("#3D6FA8"),
    )
    veins(c, 8821, 2, hex_rgba("#EAF9FF"), 8, wobble=0.6)
    bevel(c, light=0.34, dark=0.26)
    c.outline(hex_rgba("#122238"))
    emit(c, ITEMS, "voidbound_astral_shard", roughness=58,
         emissive_from=(191, 239, 255), emissive_gain=1.15, emissive_threshold=0.30)

    # Void Chitin - a curved carapace plate with a ridged spine.
    c = Canvas(16)
    plate = hex_rgba("#4A3C62")
    plate_lo = hex_rgba("#241C34")
    sheen = hex_rgba("#68E2CC")
    for y in range(16):
        for x in range(16):
            # An ellipse squashed on Y reads as a shell rather than a stone.
            d = math.hypot((x + 0.5 - 8) / 6.4, (y + 0.5 - 8.5) / 5.2)
            if d > 1.0:
                continue
            c.set(x, y, mix(plate, plate_lo, d * 0.85))
    for i, x in enumerate(range(3, 14, 2)):
        for y in range(4, 13):
            if math.hypot((x + 0.5 - 8) / 6.4, (y + 0.5 - 8.5) / 5.2) > 0.95:
                continue
            c.blend(x, y, (sheen[0], sheen[1], sheen[2], 60 + 14 * (i % 3)))
    for y in range(4, 13):
        c.blend(8, y, shade(sheen, 0.1))
    bevel(c, light=0.28, dark=0.3)
    c.outline(hex_rgba("#120C1E"))
    emit(c, ITEMS, "voidbound_void_chitin", roughness=118,
         emissive_from=sheen[:3], emissive_gain=0.7, emissive_threshold=0.42)

    # Voidsteel Ingot - vanilla ingot footprint, violet alloy.
    c = Canvas(16)
    metal = hex_rgba("#8E6FC8")
    metal_lo = hex_rgba("#3E2C63")
    for y in range(5, 12):
        # Trapezoid: narrow at the top, wide at the base - the ingot read.
        inset = 5 - (y - 5) // 2
        for x in range(inset, 16 - inset):
            t = (y - 5) / 6.0
            c.set(x, y, mix(shade(metal, 0.22), metal_lo, t))
    for x in range(4, 12):
        c.blend(x, 6, shade(metal, 0.45))
    for x in range(2, 14):
        c.blend(x, 11, shade(metal_lo, -0.25))
    bevel(c, light=0.36, dark=0.3)
    c.outline(hex_rgba("#1B1230"))
    emit(c, ITEMS, "voidbound_voidsteel_ingot", metalness=225, roughness=44,
         emissive_from=(142, 111, 200), emissive_gain=0.5, emissive_threshold=0.55)

    # Titan Core - a caged sphere, unmistakably a boss drop.
    c = Canvas(16)
    cage = hex_rgba("#6B5A48")
    core_hot = hex_rgba("#FFD9A0")
    core_mid = hex_rgba("#E8703A")
    radial(c, 8, 8, 5.6, core_hot, mix(core_mid, hex_rgba("#3A1408"), 0.45))
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            if d > 7.0:
                continue
            # Two meridians and one equator: a cage, not a ball of paint.
            if abs(x - 7.5) < 0.9 or abs(y - 7.5) < 0.9 or d > 6.1:
                c.set(x, y, shade(cage, 0.2 - 0.35 * (d / 7.0)))
    c.blend(6, 6, (255, 255, 255, 190))
    bevel(c, light=0.3, dark=0.3)
    c.outline(hex_rgba("#1A1108"))
    emit(c, ITEMS, "voidbound_titan_core", metalness=120, roughness=70,
         emissive_from=core_hot[:3], emissive_gain=1.6, emissive_threshold=0.24)


def block_waystone():
    """A carved travel marker: a rune-cut face, a worn cap, a glowing core.

    Because it is a full block, the *face* has to do all the work of saying
    "this is a device". So the sides get a deep inset frame with a vertical
    rune down the middle and a bright node at its heart, and the top gets a
    socket rather than more brickwork.
    """
    stone = mix(PALETTE["endstone_dark"], hex_rgba("#C9C2A0"), 0.42)
    stone_lo = mix(stone, PALETTE["void"], 0.48)
    seam = mix(stone_lo, (0, 0, 0, 255), 0.42)
    rune = hex_rgba("#7CE8FF")
    core = hex_rgba("#D6FBFF")

    side = Canvas(16)

    def face(x, y, _cur):
        n = fbm(x * 1.7, y * 1.7, 16, 4413, octaves=3, base_period=5)
        base = mix(stone_lo, stone, n)
        if x in (0, 15) or y in (0, 15):
            return seam
        # Inset panel.
        if 2 <= x <= 13 and 1 <= y <= 14:
            if x in (2, 13) or y in (1, 14):
                return shade(base, -0.32)
            # Rune: a spine with three crossbars and a diamond node.
            spine = x == 8 and 3 <= y <= 12
            bars = y in (5, 8, 11) and 5 <= x <= 11
            node = abs(x - 8) + abs(y - 8) <= 1
            if node:
                return core
            if spine or bars:
                return mix(base, rune, 0.72)
        return base

    side.each(face)
    emit(side, BLOCKS, "voidbound_waystone_side", roughness=214,
         emissive_from=rune[:3], emissive_gain=1.5, emissive_threshold=0.30)

    top = Canvas(16)

    def cap(x, y, _cur):
        n = fbm(x * 2.1, y * 2.1, 16, 4414, octaves=3, base_period=5)
        base = mix(stone_lo, stone, n)
        if x in (0, 15) or y in (0, 15):
            return seam
        d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
        if d <= 2.2:
            return mix(core, rune, min(1.0, d / 2.2))   # the socket, lit
        if d <= 3.4:
            return shade(base, -0.34)                    # its rim, in shadow
        # Four spokes running out to the edges, so the cap reads as machined.
        if (abs(x - 7.5) < 0.9 or abs(y - 7.5) < 0.9) and d <= 6.6:
            return mix(base, rune, 0.30)
        return base

    top.each(cap)
    emit(top, BLOCKS, "voidbound_waystone_top", roughness=210,
         emissive_from=rune[:3], emissive_gain=1.5, emissive_threshold=0.30)


def block_flora_and_stone():
    """A sapling, a chitin block, polished end stone and cracked bricks."""
    # Ender sapling: the thicket in miniature, so it reads as the same plant.
    sap = Canvas(16)
    stem = mix(PALETTE["void"], hex_rgba("#8A78A4"), 0.6)
    leaf = hex_rgba("#7B3FA8")
    leaf_hi = mix(leaf, hex_rgba("#D6A8F0"), 0.55)
    bud = hex_rgba("#3FE0C4")

    rng = Rng(5150)
    for y in range(15, 7, -1):
        sap.set(8, y, stem if y % 3 else shade(stem, 0.18))
    for dx, dy in ((-1, 11), (1, 12), (-1, 13)):
        sap.blend(8 + dx, dy, shade(stem, -0.2))
    for cx, cy, r in ((8, 6, 4.2), (5.5, 8.5, 2.6), (10.5, 8.5, 2.6)):
        for y in range(16):
            for x in range(16):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
                if d <= 1.0 and rng.next() > d * 0.5:
                    sap.blend(x, y, mix(leaf_hi, leaf, min(1.0, d * 1.15)))
    for bx, by in ((6, 6), (10, 5), (8, 9)):
        sap.blend(bx, by, bud)
    emit(sap, BLOCKS, "voidbound_ender_sapling", roughness=204,
         emissive_from=bud[:3], emissive_gain=1.0, emissive_threshold=0.24)

    # Void chitin block: overlapping plates, the beetle's drop stacked up.
    chitin = Canvas(16)
    plate = hex_rgba("#4A3C62")
    plate_lo = mix(plate, PALETTE["void"], 0.55)
    sheen = hex_rgba("#68E2CC")

    def chitin_face(x, y, _cur):
        row = y // 4
        # Offset rows so the plates interlock rather than tile as a grid.
        col = (x + row * 2) // 4
        n = fbm(x * 2.4, y * 2.4, 16, 7710 + row * 17 + col * 3, octaves=3, base_period=4)
        base = mix(plate_lo, plate, n)
        local_y = y % 4
        if local_y == 0:
            return shade(base, -0.36)                    # plate lip
        if local_y == 1:
            return mix(base, sheen, 0.20)                # the light catching it
        if (x + row * 2) % 4 == 0:
            return shade(base, -0.24)
        return base

    chitin.each(chitin_face)
    emit(chitin, BLOCKS, "voidbound_void_chitin_block", roughness=128,
         emissive_from=sheen[:3], emissive_gain=0.6, emissive_threshold=0.46)

    # Polished end stone: the same substrate, worked flat.
    polished = stone_base(3311, PALETTE["endstone"], PALETTE["endstone_dark"], contrast=0.12)

    def polish(x, y, cur):
        # A shallow chamfer reads as "cut and smoothed" at this size.
        if x == 0 or y == 0:
            return shade(cur, 0.16)
        if x == 15 or y == 15:
            return shade(cur, -0.16)
        return cur

    polished.each(polish)
    emit(polished, BLOCKS, "voidbound_polished_end_stone", roughness=170)

    # Cracked ender bricks: the coursed masonry, broken open.
    brick = mix(PALETTE["endstone_dark"], hex_rgba("#CFC8A4"), 0.5)
    brick_lo = mix(brick, PALETTE["void"], 0.4)
    mortar = mix(brick_lo, (0, 0, 0, 255), 0.35)
    cracked = Canvas(16)

    def cracked_face(x, y, _cur):
        row = y // 4
        n = fbm(x * 2.2, y * 2.2, 16, 9440 + row * 13, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if y % 4 == 0:
            return mortar
        if (x + row * 6) % 8 == 0:
            return mortar
        return shade(base, -0.06)

    cracked.each(cracked_face)
    # Fracture lines drawn after the masonry, so they cut across the courses.
    veins(cracked, 4477, 5, shade(mortar, -0.3), 13, wobble=1.5)
    veins(cracked, 4478, 3, shade(brick_lo, -0.35), 8, wobble=1.9)
    emit(cracked, BLOCKS, "voidbound_cracked_ender_bricks", roughness=244)


def block_end_detail():
    """Four pieces of natural clutter: vines, clusters, moss and shrooms.

    The End reads as empty largely because every surface is the same flat
    yellow and every island edge just stops. These are the small things that
    make somewhere look inhabited by its own geology - growth on the ground,
    growth hanging off the underside, and a second stone colour so the terrain
    is not one tone from horizon to horizon.
    """
    # Ender vines: strands hanging from an overhang, thinning as they fall.
    vines = Canvas(16)
    cord = mix(PALETTE["void"], hex_rgba("#8E5FB8"), 0.62)
    cord_hi = mix(cord, hex_rgba("#E0B8F5"), 0.45)
    bead = hex_rgba("#5FE8D2")
    rng = Rng(6270)
    for start_x in (2, 5, 8, 11, 14):
        px = float(start_x)
        # Each strand ends at its own depth, so the fringe is ragged.
        depth = rng.int(8, 16)
        for y in range(depth):
            px += rng.range(-0.35, 0.35)
            x = int(round(px)) % 16
            thin = y > depth - 4
            vines.blend(x, y, mix(cord_hi, cord, min(1.0, y / 9.0)))
            if not thin:
                vines.blend((x + 1) % 16, y, shade(cord, -0.22))
            if rng.chance(0.12):
                vines.blend(x, y, bead)
    emit(vines, BLOCKS, "voidbound_ender_vines", roughness=206,
         emissive_from=bead[:3], emissive_gain=1.1, emissive_threshold=0.3)

    # Echo crystal cluster: a splay of shards from a common root.
    cluster = Canvas(16)
    shard = hex_rgba("#6FE6D8")
    shard_lo = mix(shard, PALETTE["void"], 0.6)
    for base_x, tip_x, tip_y, width in (
        (7, 4, 3, 1.6), (8, 8, 1, 2.0), (9, 12, 5, 1.4), (6, 5, 8, 1.1), (10, 11, 9, 1.0)
    ):
        steps = 15 - tip_y
        for i in range(steps + 1):
            t = i / max(1, steps)
            x = base_x + (tip_x - base_x) * t
            y = 15 - (15 - tip_y) * t
            half = max(0.5, width * (1.0 - t * 0.85))
            for ox in range(int(-half), int(half) + 1):
                px = int(round(x)) + ox
                if 0 <= px < 16:
                    cluster.blend(px, int(round(y)),
                                  mix(shard, shard_lo, min(1.0, t * 0.5 + abs(ox) * 0.3)))
        cluster.blend(int(round(tip_x)), tip_y, (235, 255, 252, 255))
    emit(cluster, BLOCKS, "voidbound_echo_cluster", roughness=48,
         emissive_from=shard[:3], emissive_gain=1.5, emissive_threshold=0.22)

    # Mossy end stone: the substrate again, with growth taking the low ground.
    moss = stone_base(2814, PALETTE["endstone"], PALETTE["endstone_dark"], contrast=0.26)
    growth = hex_rgba("#5E8F6A")
    growth_lo = mix(growth, PALETTE["void"], 0.45)

    def creep(x, y, cur):
        # Moss follows one noise field and ignores the stone's own, so the two
        # patterns cross instead of tracing each other.
        n = fbm(x * 1.5, y * 1.5, 16, 2815, octaves=3, base_period=6)
        if n < 0.52:
            return cur
        t = min(1.0, (n - 0.52) / 0.36)
        return mix(cur, mix(growth_lo, growth, t), 0.35 + t * 0.55)

    moss.each(creep)
    speckle(moss, 2816, 0.05, [mix(growth, hex_rgba("#B8E8C4"), 0.5), shade(growth_lo, -0.2)])
    emit(moss, BLOCKS, "voidbound_mossy_end_stone", roughness=232)

    # Pale shroom: a stubby cap on a short stalk, lit from underneath.
    shroom = Canvas(16)
    stalk = hex_rgba("#D8CFE8")
    cap = hex_rgba("#F0E4FF")
    gill = hex_rgba("#9C5FD6")
    for y in range(9, 15):
        shroom.set(7, y, stalk)
        shroom.set(8, y, shade(stalk, -0.2))
    for y in range(4, 10):
        spread = 6 - abs(y - 7)
        for x in range(8 - spread, 9 + spread):
            if not 0 <= x < 16:
                continue
            top = y < 8
            shroom.blend(x, y, cap if top else mix(gill, cap, 0.35))
    for x in range(3, 13, 2):
        shroom.blend(x, 9, gill)
    shroom.blend(6, 5, (255, 255, 255, 255))
    emit(shroom, BLOCKS, "voidbound_pale_shroom", roughness=176,
         emissive_from=cap[:3], emissive_gain=1.2, emissive_threshold=0.42)


def block_biome_set():
    """Surfaces and accents for the six painted biomes.

    Each biome has to be recognisable from the air in one glance, which means
    the *surface* block carries the identity and everything else agrees with
    it. So these are built as one family: the same end-stone substrate under
    every one, retinted and re-textured, so a border between two of them reads
    as the same world changing rather than as two packs meeting.
    """
    # --- Glowspore Basin: hot magenta fungal ground ------------------------
    spore_base = hex_rgba("#B0407E")
    spore_dark = hex_rgba("#5A1840")
    soil = stone_base(4101, spore_base, spore_dark, contrast=0.34)

    def spore_speck(x, y, cur):
        n = fbm(x * 2.2, y * 2.2, 16, 4102, octaves=3, base_period=5)
        if n > 0.68:
            return mix(cur, hex_rgba("#FF9AD8"), (n - 0.68) / 0.32 * 0.7)
        return cur

    soil.each(spore_speck)
    speckle(soil, 4103, 0.05, [hex_rgba("#FFC2E8"), shade(spore_dark, -0.2)])
    emit(soil, BLOCKS, "voidbound_glowspore_soil", roughness=216,
         emissive_from=(255, 154, 216), emissive_gain=0.85, emissive_threshold=0.5)

    # The cap: concentric rings, so a giant mushroom does not tile as a grid.
    cap = Canvas(16)
    cap_hi = hex_rgba("#FF6FB4")
    cap_lo = hex_rgba("#7A2050")

    def cap_face(x, y, _cur):
        d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
        ring = math.sin(d * 1.5) * 0.5 + 0.5
        n = fbm(x * 1.6, y * 1.6, 16, 4104, octaves=3, base_period=6)
        base = mix(cap_lo, cap_hi, min(1.0, ring * 0.7 + n * 0.4))
        if d > 7.2:
            return shade(base, -0.3)
        return base

    cap.each(cap_face)
    emit(cap, BLOCKS, "voidbound_sporelight_cap", roughness=190,
         emissive_from=cap_hi[:3], emissive_gain=1.35, emissive_threshold=0.34)

    # The fungus: a slim stalk under a wide glowing cap.
    fungus = Canvas(16)
    stalk = hex_rgba("#F0D8E8")
    glow = hex_rgba("#FF8FD0")
    for y in range(8, 16):
        fungus.set(7, y, stalk)
        fungus.set(8, y, shade(stalk, -0.22))
    for y in range(3, 9):
        spread = 6 - abs(y - 6)
        for x in range(8 - spread, 9 + spread):
            if not 0 <= x < 16:
                continue
            fungus.blend(x, y, glow if y < 7 else mix(glow, spore_dark, 0.45))
    for x in range(3, 13, 2):
        fungus.blend(x, 8, shade(glow, 0.4))
    emit(fungus, BLOCKS, "voidbound_sporelight_fungus", roughness=168,
         emissive_from=glow[:3], emissive_gain=1.6, emissive_threshold=0.26)

    # --- Bonespire Reach: pale bone under a cold sky ----------------------
    bone = hex_rgba("#DDD6C0")
    bone_dark = hex_rgba("#7E7866")
    spire = stone_base(4201, bone, bone_dark, contrast=0.30)

    def grain(x, y, cur):
        # Vertical striation, so a spire reads as grown rather than quarried.
        n = fbm(x * 3.4, y * 0.7, 16, 4202, octaves=3, base_period=4)
        return shade(cur, (n - 0.5) * 0.34)

    spire.each(grain)
    veins(spire, 4203, 4, shade(bone_dark, -0.28), 12, wobble=0.7)
    emit(spire, BLOCKS, "voidbound_bonespire_stone", roughness=228)

    frost = Canvas(16)
    petal = hex_rgba("#CFE8FF")
    petal_lo = hex_rgba("#5F7FA8")
    heart = hex_rgba("#FFFFFF")
    for i in range(6):
        angle = i * math.pi / 3
        for t in range(1, 7):
            fx = 8 + math.cos(angle) * t * 0.95
            fy = 9 - math.sin(angle) * t * 0.95
            frost.blend(int(round(fx)), int(round(fy)), mix(petal, petal_lo, t / 7.0))
            if t < 4:
                frost.blend(int(round(fx)) + 1, int(round(fy)), mix(petal_lo, petal, 0.4))
    for y in range(10, 16):
        frost.set(8, y, mix(petal_lo, bone_dark, 0.4))
    frost.blend(8, 9, heart)
    emit(frost, BLOCKS, "voidbound_frost_bloom", roughness=110,
         emissive_from=petal[:3], emissive_gain=1.25, emissive_threshold=0.4)

    # --- Crystalline Expanse: end stone shot through with violet ----------
    crystal = stone_base(4301, PALETTE["endstone"], PALETTE["endstone_dark"], contrast=0.22)
    seam = hex_rgba("#A768F0")
    veins(crystal, 4302, 6, seam, 14, wobble=1.4)
    veins(crystal, 4303, 4, shade(seam, 0.45), 9, wobble=1.8)
    speckle(crystal, 4304, 0.035, [hex_rgba("#DCC0FF"), shade(seam, -0.3)])
    emit(crystal, BLOCKS, "voidbound_crystalline_end_stone", roughness=140,
         emissive_from=seam[:3], emissive_gain=1.1, emissive_threshold=0.4)

    # --- Ashen Wastes: burnt stone, and the vents that burnt it -----------
    ash = hex_rgba("#3E3A38")
    ash_dark = hex_rgba("#1C1A19")
    ashen = stone_base(4401, ash, ash_dark, contrast=0.36)
    speckle(ashen, 4402, 0.05, [hex_rgba("#6B6360"), shade(ash_dark, -0.3)])
    emit(ashen, BLOCKS, "voidbound_ashen_end_stone", roughness=248)

    vent = Canvas(16)
    ember_hot = hex_rgba("#FFD08A")
    ember_mid = hex_rgba("#E8621E")

    def vent_face(x, y, _cur):
        n = fbm(x * 1.9, y * 1.9, 16, 4403, octaves=3, base_period=5)
        base = mix(ash_dark, ash, n)
        # Cracks running with heat: hottest at the centre of each fissure.
        crack = fbm(x * 3.1, y * 3.1, 16, 4404, octaves=2, base_period=7)
        if crack > 0.62:
            heat = (crack - 0.62) / 0.38
            return mix(mix(base, ember_mid, 0.8), ember_hot, heat)
        return base

    vent.each(vent_face)
    emit(vent, BLOCKS, "voidbound_ember_vent", roughness=226,
         emissive_from=ember_hot[:3], emissive_gain=1.7, emissive_threshold=0.28)

    # --- Aurora Shelf: pale iridescent stone under the lights -------------
    aurora_a = hex_rgba("#8FC6C0")
    aurora_b = hex_rgba("#3A5E74")
    shelf = stone_base(4501, aurora_a, aurora_b, contrast=0.24)

    def iridescent(x, y, cur):
        # Two offset fields at different periods, so the sheen shifts across
        # the face instead of sitting in one place.
        a = fbm(x * 1.3, y * 1.3, 16, 4502, octaves=3, base_period=7)
        b = fbm(x * 1.3 + 40, y * 1.3 + 40, 16, 4503, octaves=3, base_period=5)
        tint = hex_rgba("#C8F0E4") if a > b else hex_rgba("#9AB4F0")
        return mix(cur, tint, abs(a - b) * 0.6)

    shelf.each(iridescent)
    emit(shelf, BLOCKS, "voidbound_aurora_stone", roughness=126,
         emissive_from=(200, 240, 228), emissive_gain=0.6, emissive_threshold=0.56)


def block_underside_set():
    """What hangs off the bottom of an island, one per biome.

    End islands stop dead at their own underside, which is the single biggest
    reason they read as generated rather than grown. Every one of these is
    built to be seen from *below and at a distance*, so they are top-heavy:
    dense where they meet the rock, thinning to nothing, because that is the
    shape the eye reads as hanging.
    """
    def hanging(seed, cord, cord_hi, bead, name, strands=5, bead_chance=0.14,
                gain=1.1, threshold=0.3, taper=True):
        c = Canvas(16)
        rng = Rng(seed)
        for start in range(1, 16, max(2, 16 // strands)):
            px = float(start)
            depth = rng.int(9, 16)
            for y in range(depth):
                px += rng.range(-0.3, 0.3)
                x = int(round(px)) % 16
                t = y / max(1, depth - 1)
                c.blend(x, y, mix(cord_hi, cord, t))
                # The second column drops away as the strand thins, which is
                # what makes it taper instead of ending in a stump.
                if not (taper and t > 0.62):
                    c.blend((x + 1) % 16, y, shade(cord, -0.22))
                if rng.chance(bead_chance):
                    c.blend(x, y, bead)
        emit(c, BLOCKS, name, roughness=196,
             emissive_from=bead[:3], emissive_gain=gain, emissive_threshold=threshold)

    # Glowspore: fat wet tendrils with spore pods down their length.
    hanging(6410, mix(PALETTE["void"], hex_rgba("#C0508E"), 0.7),
            hex_rgba("#FF9AD8"), hex_rgba("#FFD0EC"), "voidbound_spore_tendril",
            strands=4, bead_chance=0.20, gain=1.4, threshold=0.24)

    # Bonespire: icicles, so straight columns rather than wandering strands.
    ice = Canvas(16)
    ice_hi = hex_rgba("#DCEEFF")
    ice_lo = hex_rgba("#5C7EA6")
    rng = Rng(6420)
    for start in (1, 4, 7, 10, 13):
        depth = rng.int(6, 15)
        width_at = lambda t: max(0, int(round((1.0 - t) * 1.6)))
        for y in range(depth):
            t = y / max(1, depth - 1)
            half = width_at(t)
            for dx in range(-half, half + 1):
                x = (start + dx) % 16
                ice.blend(x, y, mix(ice_hi, ice_lo, t * 0.85))
        ice.blend(start % 16, min(15, depth - 1), hex_rgba("#FFFFFF"))
    emit(ice, BLOCKS, "voidbound_frost_icicle", roughness=64,
         emissive_from=ice_hi[:3], emissive_gain=1.2, emissive_threshold=0.42)

    # Crystalline: faceted dripstone, wide at the rock and pointed below.
    drip = Canvas(16)
    facet = hex_rgba("#B07CF4")
    facet_lo = hex_rgba("#3E1E6E")
    for start, depth in ((3, 13), (8, 16), (12, 10)):
        for y in range(depth):
            t = y / max(1, depth - 1)
            half = max(0, int(round((1.0 - t) * 2.2)))
            for dx in range(-half, half + 1):
                x = (start + dx) % 16
                # A bright core column, darker flanks: reads as a facet edge.
                lit = 0.0 if dx == 0 else abs(dx) / max(1, half)
                drip.blend(x, y, shade(mix(facet, facet_lo, t), 0.25 - lit * 0.5))
    emit(drip, BLOCKS, "voidbound_crystal_dripstone", roughness=52,
         emissive_from=facet[:3], emissive_gain=1.45, emissive_threshold=0.3)

    # Ashen: brittle grey stalactites, no glow at all - the one dead biome.
    ash = Canvas(16)
    ash_hi = hex_rgba("#6A625E")
    ash_lo = hex_rgba("#1E1B1A")
    rng = Rng(6440)
    for start in (2, 6, 9, 13):
        depth = rng.int(5, 14)
        for y in range(depth):
            t = y / max(1, depth - 1)
            half = max(0, int(round((1.0 - t) * 1.8)))
            for dx in range(-half, half + 1):
                x = (start + dx) % 16
                ash.blend(x, y, mix(ash_hi, ash_lo, t * 0.9 + rng.range(0, 0.2)))
    emit(ash, BLOCKS, "voidbound_ash_stalactite", roughness=250, mer=True)

    # Aurora: a hanging sheet rather than strands - it should read as fabric.
    veil = Canvas(16)
    veil_hi = hex_rgba("#8FF0DC")
    veil_lo = hex_rgba("#2A5A7E")
    for y in range(16):
        for x in range(16):
            wave = math.sin((x / 16.0) * math.pi * 2 + y * 0.28) * 0.5 + 0.5
            fall = y / 15.0
            # The sheet frays as it falls: alpha follows both the wave and the
            # drop, so the bottom edge is ragged instead of a straight cut.
            alpha = max(0.0, (1.0 - fall * 1.15) * (0.35 + wave * 0.65))
            if alpha <= 0.04:
                continue
            colour = mix(veil_hi, veil_lo, fall * 0.8 + wave * 0.2)
            veil.set(x, y, (colour[0], colour[1], colour[2], int(255 * alpha)))
    emit(veil, BLOCKS, "voidbound_aurora_veil", roughness=90,
         emissive_from=veil_hi[:3], emissive_gain=1.3, emissive_threshold=0.3)


def block_crop_and_village():
    """The End crop through its four stages, and what a village is built of."""
    stalk = mix(PALETTE["void"], hex_rgba("#7FA88E"), 0.6)
    leaf = hex_rgba("#7FD8B0")
    bloom = hex_rgba("#FFE07A")
    bloom_hot = hex_rgba("#FFF6C8")

    for stage in range(4):
        c = Canvas(16)
        t = (stage + 1) / 4.0
        height = int(4 + 10 * t)
        for x in (5, 8, 11):
            for y in range(15, 15 - height, -1):
                c.set(x, y, stalk if (y + x) % 3 else shade(stalk, 0.2))
        # Leaves come in from stage 1, buds from stage 2, flowers at stage 3.
        if stage >= 1:
            for x, y in ((4, 11), (12, 12), (7, 9), (9, 10)):
                if 15 - y < height:
                    c.blend(x, y, leaf)
                    c.blend(x + (1 if x < 8 else -1), y, mix(leaf, stalk, 0.4))
        if stage >= 2:
            for x, y in ((5, 15 - height + 1), (11, 15 - height + 2)):
                c.blend(x, max(0, y), mix(bloom, leaf, 0.5))
        if stage == 3:
            for x in (5, 8, 11):
                top = max(0, 15 - height)
                c.blend(x, top, bloom_hot)
                c.blend(x, top + 1, bloom)
                c.blend(x - 1, top + 1, mix(bloom, leaf, 0.35))
                c.blend(x + 1, top + 1, mix(bloom, leaf, 0.35))
        emit(c, BLOCKS, "voidbound_bloomstalk_stage_%d" % stage, roughness=186,
             emissive_from=bloom_hot[:3], emissive_gain=1.2 if stage == 3 else 0.5,
             emissive_threshold=0.4)

    # Village stone: dressed, pale, deliberately unlike anything the biomes
    # make, so a village reads as *built* from a long way off.
    dressed = stone_base(7701, hex_rgba("#CFC6B0"), hex_rgba("#6E6858"), contrast=0.20)

    def dress(x, y, cur):
        if x in (0, 15) or y in (0, 15):
            return shade(cur, -0.34)
        if x in (1, 14) or y in (1, 14):
            return shade(cur, 0.16)
        return cur

    dressed.each(dress)
    emit(dressed, BLOCKS, "voidbound_dressed_end_stone", roughness=222)

    # Lantern-post block: a carved column with a lit slot on every face.
    post = Canvas(16)
    wood = mix(PALETTE["void"], hex_rgba("#8C7AA4"), 0.55)
    lamp = hex_rgba("#FFDC96")

    def post_face(x, y, _cur):
        n = fbm(x * 2.8, y * 0.8, 16, 7702, octaves=3, base_period=4)
        base = mix(shade(wood, -0.22), wood, n)
        if x in (0, 1, 14, 15):
            return shade(base, -0.3)
        if 5 <= x <= 10 and 4 <= y <= 10:
            d = max(abs(x - 7.5), abs(y - 7)) / 3.5
            return mix(lamp, shade(lamp, -0.5), d)
        return base

    post.each(post_face)
    emit(post, BLOCKS, "voidbound_lantern_post", roughness=170,
         emissive_from=lamp[:3], emissive_gain=1.5, emissive_threshold=0.34)


def item_farm_and_trade():
    """The seed, the harvest, and the currency a village runs on."""
    # Bloomstalk seed: a small pod with a pale husk split down one side.
    c = Canvas(16)
    husk = hex_rgba("#CFE8D4")
    core = hex_rgba("#7FD8B0")
    radial(c, 8, 9, 4.4, husk, mix(core, PALETTE["void"], 0.4), falloff=1.25)
    for y in range(5, 14):
        c.blend(8, y, shade(core, -0.25))
    for x, y in ((6, 6), (10, 11)):
        c.blend(x, y, hex_rgba("#FFFFFF"))
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.5))
    emit(c, ITEMS, "voidbound_bloomstalk_seed", roughness=180,
         emissive_from=core[:3], emissive_gain=0.7, emissive_threshold=0.45)

    # Bloom pod: the harvest. Fatter, brighter, and clearly the same plant.
    c = Canvas(16)
    pod = hex_rgba("#FFE07A")
    pod_hot = hex_rgba("#FFF6C8")
    radial(c, 8, 8.5, 5.6, pod_hot, mix(pod, hex_rgba("#5E7A38"), 0.55), falloff=1.15)
    for i in range(4):
        angle = i * math.pi / 4 + 0.4
        for t in range(2, 6):
            c.blend(int(round(8 + math.cos(angle) * t)),
                    int(round(8.5 + math.sin(angle) * t)),
                    mix(pod, hex_rgba("#8FBF6A"), 0.4))
    for y in range(1, 5):
        c.set(8, y, mix(PALETTE["void"], hex_rgba("#7FA88E"), 0.6))
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(c, ITEMS, "voidbound_bloom_pod", roughness=150,
         emissive_from=pod_hot[:3], emissive_gain=1.3, emissive_threshold=0.28)

    # Void sigil: what End villagers deal in. A coin has to read as struck
    # metal at 16px, so it is a disc with a raised rim and a cut mark.
    c = Canvas(16)
    metal = hex_rgba("#B9A6D8")
    metal_lo = hex_rgba("#4A3A68")
    mark = hex_rgba("#7CE8FF")
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            if d > 6.6:
                continue
            if d > 5.3:
                c.set(x, y, shade(metal_lo, 0.1))          # rim
            else:
                c.set(x, y, mix(metal, metal_lo, d / 5.3 * 0.7))
    for y in range(4, 12):
        c.blend(8, y, mark)
    for x in range(5, 12):
        c.blend(x, 8, mix(mark, metal, 0.35))
    c.blend(8, 8, hex_rgba("#EAFBFF"))
    bevel(c, light=0.34, dark=0.3)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.6))
    emit(c, ITEMS, "voidbound_void_sigil", metalness=215, roughness=56,
         emissive_from=mark[:3], emissive_gain=1.1, emissive_threshold=0.42)


def entity_end_villager():
    """64x64 on geometry.villager_v2: an End trader in a hooded robe."""
    c = Canvas(64, 64)
    robe = hex_rgba("#3E3060")
    robe_hi = hex_rgba("#6E5C96")
    robe_lo = hex_rgba("#241A3A")
    skin = hex_rgba("#5A4E74")
    skin_hi = hex_rgba("#7A6E96")
    eyes = hex_rgba("#C8F0FF")
    trim = hex_rgba("#E0B85C")

    def head(face, fx, fy, fw, fh):
        if face == "top":
            return robe_lo                       # hood crown
        if face == "north":
            # A dark hood opening with two lit eyes set into it - the whole
            # read of the face at 8px is those two pixels.
            if fy <= 2:
                return robe_lo
            if 1 <= fx <= fw - 2 and 3 <= fy <= 7:
                if fy == 5 and fx in (2, fw - 3):
                    return eyes
                if fy == 6 and fx in (2, fw - 3):
                    return mix(eyes, skin, 0.55)
                return mix(skin, robe_lo, 0.45 + (fy - 3) * 0.06)
            return robe
        if face == "bottom":
            return skin
        # Side and back of the hood, with a fold running down each side.
        return robe_lo if fx in (0, fw - 1) else mix(robe, robe_hi, 0.25)

    paint_box(c, 0, 0, 8, 10, 8, head)

    def nose(face, _fx, _fy, _fw, _fh):
        return skin_hi if face in ("north", "top") else skin

    paint_box(c, 24, 0, 2, 4, 2, nose)

    def body(face, fx, fy, fw, fh):
        if face == "north":
            # The sash: a diagonal band of trim across the chest, which is
            # what tells one profession from another at a glance.
            if abs((fx / max(1.0, fw - 1.0)) - (fy / max(1.0, fh - 1.0))) < 0.18:
                return trim
            if fy >= fh - 3:
                return robe_lo                  # hem
            return robe
        if face == "top":
            return robe_lo
        if fy >= fh - 3:
            return robe_lo
        # Vertical folds down the robe.
        return shade(robe, -0.16) if int(fx) % 3 == 0 else robe

    paint_box(c, 16, 20, 8, 12, 6, body)
    # The over-robe layer, one shade lighter so it separates from the body.
    paint_box(c, 0, 38, 8, 18, 6,
              lambda face, fx, fy, fw, fh: (robe_lo if fy >= fh - 4 else
                                            mix(robe, robe_hi, 0.3 if int(fx) % 4 else 0.0)))

    def arms(face, _fx, fy, _fw, fh):
        return mix(robe, robe_hi, 0.2) if fy < fh - 2 else skin

    paint_box(c, 40, 38, 8, 4, 4, arms)
    paint_box(c, 44, 22, 4, 8, 4, arms)

    def legs(face, _fx, fy, _fw, fh):
        return robe_lo if fy < fh - 3 else mix(skin, robe_lo, 0.4)

    paint_box(c, 0, 22, 4, 12, 4, legs)

    emit(c, ENTITY, "voidbound_end_villager", roughness=214,
         emissive_from=eyes[:3], emissive_gain=1.4, emissive_threshold=0.5)


def enderman_skin(name, body_rgb, limb_rgb, eye_rgb, mark_rgb, mark_style):
    """64x32 on geometry.enderman.v1.8 - one biome's enderman.

    Every one of these has to still read as an enderman, so the body stays
    near-black and only the *markings* change: the shape they take, and the
    colour of the eyes. That is the difference between a variant and a
    different mob wearing the wrong skeleton.
    """
    c = Canvas(64, 32)
    body = hex_rgba(body_rgb)
    body_hi = shade(body, 0.22)
    limb = hex_rgba(limb_rgb)
    eyes = hex_rgba(eye_rgb)
    mark = hex_rgba(mark_rgb)

    def marked(face, fx, fy, fw, fh, base, zone="body"):
        """Apply this variant's marking pattern to one face.

        Only the head and torso are ever marked. An enderman's limbs are two
        pixels wide and thirty tall, so *any* repeating pattern on them tiles
        into obvious stripes - and the eye reads a striped enderman as a
        different creature rather than a variant of one. Keeping the limbs
        plain is what holds all six of these together as endermen.
        """
        if zone == "limb":
            return base
        # These are markings on near-black skin, seen at the distance an
        # enderman is usually seen from. Every threshold here is set so only a
        # handful of pixels per face are touched: enough to tell the variants
        # apart, not enough to stop reading as skin.
        if mark_style == "veins":
            n = fbm(fx * 3.4, fy * 3.4, 16, 771, octaves=2, base_period=5)
            if n > 0.80:
                return mix(base, mark, (n - 0.80) / 0.20 * 0.75)
        elif mark_style == "bands":
            # Broken, not continuous. A solid stripe every fourth row turned
            # the whole creature into a bandaged mummy.
            if int(fy) % 6 == 2 and (int(fx) + int(fy)) % 3 != 0:
                return mix(base, mark, 0.20)
        elif mark_style == "speckle":
            n = fbm(fx * 5.1, fy * 5.1, 16, 772, octaves=2, base_period=3)
            if n > 0.90:
                return mix(base, mark, 0.85)
            if n > 0.85:
                return mix(base, mark, 0.35)
        elif mark_style == "frost":
            t = 1.0 - fy / max(1.0, fh - 1.0)
            n = fbm(fx * 4.0, fy * 4.0, 16, 773, octaves=2, base_period=4)
            if n > 0.90 - t * 0.05:
                return mix(base, mark, 0.25 + t * 0.25)
        elif mark_style == "ember":
            n = fbm(fx * 3.0, fy * 3.0, 16, 774, octaves=2, base_period=6)
            if n > 0.84:
                return mix(base, mark, (n - 0.84) / 0.16 * 0.7)
        elif mark_style == "sheen":
            wave = math.sin((fx / max(1.0, fw)) * math.pi * 2 + fy * 0.42) * 0.5 + 0.5
            if wave > 0.88:
                return mix(base, mark, (wave - 0.88) / 0.12 * 0.35)
        return base

    def head(face, fx, fy, fw, fh):
        base = body if face != "top" else shade(body, -0.15)
        if face == "north":
            # The eyes, and the pale bar between them: an enderman's whole
            # face is that horizontal streak, so it stays exactly where
            # vanilla puts it.
            if fy == 3 and 1 <= fx <= fw - 2:
                return mix(eyes, base, 0.62)
            if fy == 3 and fx in (1, 2, fw - 3, fw - 2):
                return eyes
            if fy == 2 and fx in (1, 2, fw - 3, fw - 2):
                return eyes
        return marked(face, fx, fy, fw, fh, base)

    paint_box(c, 0, 0, 8, 8, 8, head)
    # The hat layer sits half a pixel proud; used here as a shadow pass so the
    # head has depth rather than being one flat colour.
    paint_box(c, 0, 16, 8, 8, 8,
              lambda face, fx, fy, fw, fh: None if face == "north" and fy in (2, 3)
              else shade(body, -0.28))

    def torso(face, fx, fy, fw, fh):
        base = body_hi if face in ("north", "south") else body
        return marked(face, fx, fy, fw, fh, base)

    paint_box(c, 32, 16, 8, 12, 4, torso)

    def spindle(face, fx, fy, fw, fh):
        # Long thin limbs, darkening toward the extremities. Unmarked, and a
        # faint edge highlight so they still have form against a dark sky.
        t = fy / max(1.0, fh - 1.0)
        base = mix(limb, shade(limb, -0.4), t * 0.7)
        if fx == 0:
            base = shade(base, 0.20)
        return marked(face, fx, fy, fw, fh, base, zone="limb")

    paint_box(c, 56, 0, 2, 30, 2, spindle)

    emit(c, ENTITY, name, roughness=206,
         emissive_from=eyes[:3], emissive_gain=1.6, emissive_threshold=0.34)


def entity_biome_endermen():
    """One enderman per painted biome, plus the vanilla-dark Barrens variant."""
    # body, limb, eyes, marking, style
    VARIANTS = [
        ("voidbound_enderman_glowspore", "#241028", "#180A1C", "#FF6FD0", "#C4308E", "veins"),
        ("voidbound_enderman_bonespire", "#1A1E28", "#101318", "#DCEEFF", "#CFC6A8", "bands"),
        ("voidbound_enderman_crystalline", "#1C1230", "#120C20", "#C89AFF", "#8E4CE0", "speckle"),
        ("voidbound_enderman_verdant", "#101E18", "#0A140F", "#7FF0C0", "#3EA870", "frost"),
        ("voidbound_enderman_ashen", "#1A1614", "#0E0C0B", "#FFB070", "#E8621E", "ember"),
        ("voidbound_enderman_aurora", "#101C24", "#0A1218", "#8FF0DC", "#5EA8D8", "sheen"),
    ]
    for name, bodyc, limbc, eyec, markc, style in VARIANTS:
        enderman_skin(name, bodyc, limbc, eyec, markc, style)


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
        item_raw_haunch,
        item_cooked_haunch,
        item_echo_bread,
        tool_set,
        entity_rift_sovereign,
        entity_endstone_golem,
        entity_void_titan,
        entity_end_villager,
        entity_biome_endermen,
        block_ender_log,
        block_ender_leaves,
        block_ender_bush,
        block_building_set,
        block_decor_set,
        block_waystone,
        block_flora_and_stone,
        block_end_detail,
        block_biome_set,
        block_underside_set,
        block_crop_and_village,
        item_gameplay_set,
        item_ender_fruit,
        item_sovereign_crown,
        item_material_set,
        item_farm_and_trade,
        particle_atlas,
        armor_layers,
        item_void_helmet,
        item_void_chestplate,
        item_void_leggings,
        item_void_boots,
        end_sky,
        moon_phases,
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
