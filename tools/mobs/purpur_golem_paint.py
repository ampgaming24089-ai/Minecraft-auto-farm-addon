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

    if bone.startswith("shard"):
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(VIOLET, MAGENTA, 0.4), WHITE, max(0.0, 0.5 - t * 0.5))

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
    if bone.endswith("_brow") or bone == "brow":
        base = shade(base, -0.2)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_purpur_golem", roughness=232,
     emissive_from=MAGENTA[:3], emissive_gain=1.4, emissive_threshold=0.34)
print("golem texture written")
