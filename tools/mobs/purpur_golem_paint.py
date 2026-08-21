import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

DEEP    = hex_rgba("#1A0830")
ROYAL   = hex_rgba("#300D4D")
PURPUR  = hex_rgba("#8A5C9E")
PURPUR2 = hex_rgba("#B486C6")
VIOLET  = hex_rgba("#6B1FFF")
MAGENTA = hex_rgba("#FF3DFF")
AMBER   = hex_rgba("#FFC24A")
WHITE   = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/purpur_golem.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def stone(fx, fy, fw, fh, seed):
    """Purpur: a speckled pale violet with a mortar line every four pixels, so
    the golem visibly reads as built out of blocks."""
    n = fbm(fx * 2.4, fy * 2.4, 16, seed, octaves=3, base_period=4)
    base = mix(PURPUR, ROYAL, 0.25 + n * 0.45)
    if n > 0.78:
        base = mix(base, PURPUR2, 0.6)
    if fx % 4 == 0 or fy % 4 == 0:
        return shade(base, -0.26)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff

    if bone == "core":
        # The furnace it runs on. White at the middle, amber out to the bezel.
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        return mix(mix(WHITE, AMBER, r), MAGENTA, max(0.0, r - 0.5) * 1.6)

    if bone == "core_frame":
        n = fbm(fx * 2.4, fy * 2.4, 16, seed, octaves=2, base_period=3)
        iron = mix(hex_rgba("#3A3040"), hex_rgba("#7A6C88"), 0.2 + n * 0.4)
        if fy == 0:
            return mix(iron, AMBER, 0.4)
        return iron

    if bone.startswith("band") or bone.startswith("armband"):
        # Iron banding: lit top edge, dark bottom, bolts along the length.
        n = fbm(fx * 2.8, fy * 2.8, 16, seed, octaves=2, base_period=3)
        iron = mix(hex_rgba("#332A3E"), hex_rgba("#847894"), 0.2 + n * 0.45)
        if fy == 0:
            return shade(iron, 0.3)
        if fy == fh - 1:
            return shade(iron, -0.35)
        if fx % 5 == 2:
            return mix(iron, WHITE, 0.3)              # bolt
        return iron

    if bone.startswith("bigshard") or bone.startswith("shard"):
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(VIOLET, MAGENTA, 0.4), WHITE, max(0.0, 0.6 - t * 0.6))

    if bone == "head" and face == "north":
        # Two amber eyes deep under the brow. A golem's face is one slab and
        # two lights, and it works because nothing else on it glows warm.
        if fy in (4, 5) and fx in (3, 4, fw - 5, fw - 4):
            return WHITE if fy == 4 else AMBER

    base = stone(fx, fy, fw, fh, seed)
    # Fissures with light in them, threading between the blocks.
    crack = fbm(fx * 3.4, fy * 3.4, 16, seed + 611, octaves=2, base_period=6)
    if crack > 0.84:
        return mix(base, MAGENTA, (crack - 0.84) / 0.16 * 0.85)
    # Runework: short straight strokes on a grid, so it reads as carved
    # lettering rather than as more cracking.
    if face in ("north", "east", "west") and fw >= 8 and fh >= 8:
        gx, gy = fx % 6, fy % 6
        if (gx == 2 and 1 <= gy <= 4) or (gy == 2 and 1 <= gx <= 3):
            if fbm(fx // 6 * 3.0, fy // 6 * 3.0, 16, seed + 77,
                   octaves=1, base_period=2) > 0.5:
                return mix(base, AMBER, 0.55)
    if bone.endswith("_brow") or bone == "brow":
        base = shade(base, -0.2)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_purpur_golem", roughness=232,
     emissive_from=MAGENTA[:3], emissive_gain=1.4, emissive_threshold=0.34)
print("golem texture written")
