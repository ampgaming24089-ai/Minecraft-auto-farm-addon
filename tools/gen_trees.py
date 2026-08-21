#!/usr/bin/env python3
"""A tree species per biome: bark, canopy, sapling, blocks and atlas entries.

One tree in seven regions is one tree - a violet canopy on a bone spire looks
exactly as wrong as it sounds. Each region gets its own species instead, and
because a species is four textures, three block definitions, four atlas
entries and six lang lines, it is generated from one table entry rather than
assembled by hand seventeen times.

The shape of each tree lives alongside its colours here and is exported to the
script layer, so the thing that grows in a biome and the thing that is painted
for it can never be describing different trees.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

from artlib import (Canvas, TRANSPARENT, fbm, hex_rgba, mix, radial, shade,
                    speckle, veins)  # noqa: E402
from gen_art import BLOCKS, emit  # noqa: E402

# --------------------------------------------------------------------------
# The species
# --------------------------------------------------------------------------
# bark/leaf are the two colours everything else is derived from. `canopy` is
# the silhouette, and it is the part that actually distinguishes one species
# from another at distance - colour alone reads as the same tree tinted.
#
#   dome     a rounded crown, widest in the middle          (verdant)
#   spire    a narrow cone, tallest and thinnest            (bonespire)
#   parasol  a flat wide plate on a bare trunk              (glowspore)
#   cluster  loose blobs hung off the top of the trunk      (crystalline)
#   weeping  a crown that hangs down past the branch line   (aurora)
#   scrub    short, wide and gnarled                        (ashen)

SPECIES = {
    "verdant": dict(
        title="Verdant", bark="#4C6E52", leaf="#5FBF6E", glow="#9CF2A4",
        canopy="dome", height=(6, 9), light=2, sapling_on=[
            "voidbound:verdant_end_stone", "voidbound:mossy_end_stone"]),
    "bonespire": dict(
        title="Bonespire", bark="#B9B2A4", leaf="#DCE8F0", glow="#9FE6FF",
        canopy="spire", height=(8, 13), light=3, sapling_on=[
            "voidbound:bonespire_stone"]),
    "glowspore": dict(
        title="Sporecap", bark="#6A4A78", leaf="#E86BD8", glow="#FFB3F5",
        canopy="parasol", height=(5, 8), light=8, sapling_on=[
            "voidbound:glowspore_soil"]),
    "crystalline": dict(
        title="Crystalbough", bark="#4A3A6E", leaf="#8E6BFF", glow="#C8B0FF",
        canopy="cluster", height=(6, 10), light=6, sapling_on=[
            "voidbound:crystalline_end_stone"]),
    "aurora": dict(
        title="Auroral", bark="#3E5A78", leaf="#4FD8E8", glow="#B6FBFF",
        canopy="weeping", height=(7, 11), light=5, sapling_on=[
            "voidbound:aurora_stone", "minecraft:end_stone"]),
    "ashen": dict(
        title="Cinderbark", bark="#3A2A2E", leaf="#C4562E", glow="#FF9B4A",
        canopy="scrub", height=(4, 7), light=4, sapling_on=[
            "voidbound:ashen_end_stone"]),
}


# --------------------------------------------------------------------------
# Art
# --------------------------------------------------------------------------

def bark_textures(key, spec, seed):
    """Trunk sides and the cut end. The side is grain stretched hard on x so
    it reads as fibre rather than as noise; the end is rings."""
    bark = hex_rgba(spec["bark"])
    lo = mix(bark, hex_rgba("#0B0714"), 0.5)
    hi = mix(bark, hex_rgba("#EDE6F5"), 0.35)
    glow = hex_rgba(spec["glow"])

    side = Canvas(16)

    def grain(x, y, _cur):
        n = fbm(x * 3.6, y * 0.7, 16, seed, octaves=3, base_period=4)
        base = mix(lo, bark, n)
        if n > 0.64:
            base = mix(base, hi, (n - 0.64) / 0.36 * 0.8)
        return base

    side.each(grain)
    veins(side, seed + 1, 2, mix(glow, lo, 0.45), 18, wobble=0.25, width=1)
    emit(side, BLOCKS, "voidbound_%s_log" % key, roughness=236,
         emissive_from=glow[:3], emissive_gain=0.55, emissive_threshold=0.44)

    top = Canvas(16)

    def rings(x, y, _cur):
        d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
        n = fbm(x * 2, y * 2, 16, seed + 2, octaves=2, base_period=4)
        ring = (math.sin(d * 2.1 + n * 1.4) + 1) * 0.5
        return mix(lo, hi, ring * 0.75)

    top.each(rings)
    radial(top, 8, 8, 2.2, glow, mix(bark, glow, 0.2), falloff=1.4)
    emit(top, BLOCKS, "voidbound_%s_log_top" % key, roughness=232,
         emissive_from=glow[:3], emissive_gain=0.6, emissive_threshold=0.4)


def leaf_texture(key, spec, seed):
    """Alpha-tested canopy, so it needs real holes rather than dark pixels."""
    leaf = hex_rgba(spec["leaf"])
    lo = mix(leaf, hex_rgba("#0B0714"), 0.5)
    hi = mix(leaf, hex_rgba("#FFFFFF"), 0.45)
    glow = hex_rgba(spec["glow"])
    c = Canvas(16)

    def canopy(x, y, _cur):
        # Two scales of noise: a coarse one that decides where the foliage is
        # at all, and a fine one that gives it leaf-sized structure. With only
        # the coarse one the texture is a few big blobs of one colour, which
        # in game reads as a painted slab rather than as a canopy.
        clump = fbm(x * 1.9, y * 1.9, 16, seed + 1, octaves=3, base_period=3)
        if clump < 0.38:
            return TRANSPARENT
        n = fbm(x * 4.2, y * 4.2, 16, seed, octaves=3, base_period=2)
        # Pinholes right through, scattered through the mass rather than only
        # at its edge - that is what makes a canopy look like it has depth.
        if clump < 0.46 and n < 0.34:
            return TRANSPARENT
        base = mix(lo, leaf, 0.15 + n * 0.85)
        if n > 0.72:
            return mix(base, hi, (n - 0.72) / 0.28)
        if n < 0.22:
            return shade(base, -0.35)
        return base

    c.each(canopy)
    speckle(c, seed + 2, 0.07, [glow, shade(lo, -0.3)])
    emit(c, BLOCKS, "voidbound_%s_leaves" % key, roughness=222,
         emissive_from=glow[:3], emissive_gain=0.5, emissive_threshold=0.48)


def sapling_texture(key, spec, seed):
    """A seedling on a cross plane: a stem and a few leaves, mostly empty."""
    leaf = hex_rgba(spec["leaf"])
    glow = hex_rgba(spec["glow"])
    stem = mix(hex_rgba(spec["bark"]), hex_rgba("#0B0714"), 0.35)
    c = Canvas(16)

    for y in range(6, 15):
        c.set(8, y, stem if (y % 3) else mix(stem, glow, 0.4))
        if y > 11:
            c.set(7, y, shade(stem, -0.2))

    # Sprays of leaves. Filled discs give a solid wedge on a stick; what reads
    # as a seedling is a few separated tufts with sky between them, so every
    # pixel is dropped out against the same fine noise the canopy uses and the
    # discs are deliberately small.
    lo = mix(leaf, hex_rgba("#0B0714"), 0.45)
    for cx, cy, r in ((8, 4, 2.6), (5, 7, 2.0), (11, 7, 1.9),
                      (7, 10, 1.6), (10, 10, 1.4)):
        for y in range(16):
            for x in range(16):
                d = math.hypot(x - cx, y - cy)
                if d > r:
                    continue
                n = fbm(x * 4.0, y * 4.0, 16, seed, octaves=3, base_period=2)
                # Thinner toward the rim, and never solid even at the middle.
                if n < 0.12 + (d / r) * 0.5:
                    continue
                c.set(x, y, mix(lo, mix(leaf, glow, max(0.0, 0.5 - d / r)),
                                0.25 + n * 0.75))
    emit(c, BLOCKS, "voidbound_%s_sapling" % key, roughness=204,
         emissive_from=glow[:3], emissive_gain=0.7, emissive_threshold=0.4)


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------

def log_block(key, spec):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {"identifier": "voidbound:%s_log" % key,
                            "menu_category": {"category": "construction"}},
            "components": {
                "minecraft:display_name": "tile.voidbound:%s_log.name" % key,
                "minecraft:geometry": "minecraft:geometry.full_block",
                "minecraft:material_instances": {
                    "*": {"texture": "voidbound_%s_log" % key,
                          "render_method": "opaque", "ambient_occlusion": 1.0},
                    "up": {"texture": "voidbound_%s_log_top" % key,
                           "render_method": "opaque", "ambient_occlusion": 1.0},
                    "down": {"texture": "voidbound_%s_log_top" % key,
                             "render_method": "opaque", "ambient_occlusion": 1.0},
                },
                "minecraft:map_color": spec["bark"],
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 1.4},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
                "minecraft:light_emission": max(1, spec["light"] // 2),
                "minecraft:flammable": {"catch_chance_modifier": 0,
                                        "destroy_chance_modifier": 0},
            },
        },
    }


def leaves_block(key, spec):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {"identifier": "voidbound:%s_leaves" % key,
                            "menu_category": {"category": "nature"}},
            "components": {
                "minecraft:display_name": "tile.voidbound:%s_leaves.name" % key,
                "minecraft:geometry": "minecraft:geometry.full_block",
                "minecraft:material_instances": {
                    "*": {"texture": "voidbound_%s_leaves" % key,
                          "render_method": "alpha_test",
                          "ambient_occlusion": 0.0, "face_dimming": False},
                },
                "minecraft:map_color": spec["leaf"],
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 0.25},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 0.6},
                "minecraft:light_emission": spec["light"],
                "minecraft:light_dampening": 1,
                "minecraft:flammable": {"catch_chance_modifier": 0,
                                        "destroy_chance_modifier": 0},
            },
        },
    }


def sapling_block(key, spec):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {"identifier": "voidbound:%s_sapling" % key,
                            "menu_category": {"category": "nature"}},
            "components": {
                "minecraft:display_name": "tile.voidbound:%s_sapling.name" % key,
                "minecraft:geometry": "minecraft:geometry.cross",
                "minecraft:material_instances": {
                    "*": {"texture": "voidbound_%s_sapling" % key,
                          "render_method": "alpha_test",
                          "ambient_occlusion": 0.0, "face_dimming": False},
                },
                "minecraft:map_color": spec["leaf"],
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 0.0},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 0},
                "minecraft:light_emission": max(1, spec["light"] // 2),
                "minecraft:light_dampening": 0,
                "minecraft:collision_box": False,
                "minecraft:selection_box": {"origin": [-6, 0, -6],
                                            "size": [12, 14, 12]},
                "minecraft:replaceable": {},
                "minecraft:flower_pottable": {},
                "minecraft:random_offset": {
                    "x": {"range": {"min": -0.25, "max": 0.25}, "steps": 4},
                    "z": {"range": {"min": -0.25, "max": 0.25}, "steps": 4},
                },
                "minecraft:placement_filter": {
                    "conditions": [{
                        "allowed_faces": ["up"],
                        "block_filter": [{"name": block}
                                         for block in spec["sapling_on"]],
                    }],
                },
            },
        },
    }


# --------------------------------------------------------------------------

def write_json(path, data):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def main():
    atlas_path = os.path.join(ROOT, "RP", "textures", "terrain_texture.json")
    atlas = json.load(open(atlas_path))
    lang = []

    for index, (key, spec) in enumerate(SPECIES.items()):
        seed = 7400 + index * 40
        bark_textures(key, spec, seed)
        leaf_texture(key, spec, seed + 10)
        sapling_texture(key, spec, seed + 20)

        write_json("BP/blocks/%s_log.json" % key, log_block(key, spec))
        write_json("BP/blocks/%s_leaves.json" % key, leaves_block(key, spec))
        write_json("BP/blocks/%s_sapling.json" % key, sapling_block(key, spec))

        for suffix in ("log", "log_top", "leaves", "sapling"):
            name = "voidbound_%s_%s" % (key, suffix)
            atlas["texture_data"][name] = {"textures": "textures/blocks/" + name}

        title = spec["title"]
        lang += [
            "tile.voidbound:%s_log.name=%s Log" % (key, title),
            "tile.voidbound:%s_leaves.name=%s Leaves" % (key, title),
            "tile.voidbound:%s_sapling.name=%s Sapling" % (key, title),
        ]

    with open(atlas_path, "w") as handle:
        json.dump(atlas, handle, indent=2)
        handle.write("\n")

    # The species table the script layer grows from, written from the same
    # source as the art so a biome's tree and its textures cannot diverge.
    module = ['/**',
              ' * The tree species, one per region.',
              ' *',
              ' * Generated by tools/gen_trees.py alongside the blocks and the',
              ' * textures, so what grows in a region and what was painted for it',
              ' * are the same tree by construction rather than by discipline.',
              ' */',
              '',
              'export const TREES = {']
    for key, spec in SPECIES.items():
        module.append('  %s: {' % key)
        module.append('    log: "voidbound:%s_log",' % key)
        module.append('    leaves: "voidbound:%s_leaves",' % key)
        module.append('    sapling: "voidbound:%s_sapling",' % key)
        module.append('    canopy: "%s",' % spec["canopy"])
        module.append('    height: [%d, %d],' % spec["height"])
        module.append('  },')
    module.append('};')
    module.append('')
    with open(os.path.join(ROOT, "BP", "scripts", "world", "trees.js"), "w") as h:
        h.write("\n".join(module))

    print("%d species: %d blocks, %d textures, %d atlas entries"
          % (len(SPECIES), len(SPECIES) * 3, len(SPECIES) * 4, len(SPECIES) * 4))
    return lang


if __name__ == "__main__":
    for line in main():
        print("  " + line)
