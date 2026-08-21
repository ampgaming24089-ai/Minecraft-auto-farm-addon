import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0711")
DEEP    = hex_rgba("#1A0830")
ROYAL   = hex_rgba("#300D4D")
MAGENTA = hex_rgba("#FF3DFF")
AMBER   = hex_rgba("#FFB03A")
EMBER   = hex_rgba("#FF6A1E")
WHITE   = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/corrupted_enderman.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    n = fbm(fx * 2.4, fy * 2.4, 16, seed, octaves=3, base_period=4)

    if bone == "rift":
        # The corruption itself: white-hot at the centre, cooling outward.
        t = abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
        return mix(mix(WHITE, AMBER, t), EMBER, t * t)

    if bone.startswith("tooth"):
        return WHITE if fy == 0 else mix(WHITE, AMBER, 0.4)

    if bone == "head" and face == "north":
        # An enderman's face is the pale horizontal streak. Corrupted, it
        # burns amber instead of violet.
        if fy in (3, 4) and 1 <= fx <= fw - 2:
            if fx in (1, 2, fw - 3, fw - 2):
                return mix(AMBER, WHITE, 0.5)
            return mix(EMBER, VOID, 0.5)

    if bone.startswith("tatter"):
        # Rag, burning at the torn end. The further down the chain, the more
        # of it has gone.
        index = int(bone.split("_")[-1])
        t = min(1.0, index / 4.0)
        base = mix(VOID, DEEP, 0.3 + n * 0.4)
        return mix(base, EMBER, t * 0.55 + (0.3 if fy >= fh - 1 else 0.0))

    base = mix(VOID, DEEP, 0.25 + n * 0.45)
    # Embers creeping through the skin, denser toward the chest.
    burn = fbm(fx * 3.2, fy * 3.2, 16, seed + 511, octaves=2, base_period=5)
    if burn > 0.86:
        return mix(base, AMBER, (burn - 0.86) / 0.14 * 0.9)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_corrupted_enderman", roughness=200,
     emissive_from=AMBER[:3], emissive_gain=1.9, emissive_threshold=0.26)
print("corrupted enderman texture written")
