import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0711")
DEEP    = hex_rgba("#1A0830")
ROYAL   = hex_rgba("#300D4D")
VIOLET  = hex_rgba("#6B1FFF")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
CYAN    = hex_rgba("#00E6FF")
WHITE   = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/ender_overlord.geo.json"))["minecraft:geometry"][0]
c = Canvas(512, 512)


def chitin(fx, fy, fw, fh, seed, base, light):
    """Hard, faceted shell - hexagonal-ish cells rather than soft noise."""
    n = fbm(fx * 2.2, fy * 2.2, 16, seed, octaves=3, base_period=4)
    cell = fbm(fx * 4.4, fy * 4.4, 16, seed + 31, octaves=1, base_period=3)
    tone = mix(base, light, 0.15 + n * 0.35)
    if cell > 0.78:
        return shade(tone, -0.30)          # cell seam
    if cell < 0.22:
        return shade(tone, 0.18)           # lit facet
    return tone


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    cx = abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
    cy = abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0)
    radial = max(cx, cy)

    if bone.startswith("iris"):
        depth = int(bone.split("_")[1])
        if face == "north":
            # Each ring is brighter and hotter than the one behind it, so the
            # eye reads as looking out of a socket rather than painted on.
            t = depth / 4.0
            inner = mix(mix(ROYAL, MAGENTA, t), WHITE, max(0.0, t - 0.5) * 1.4)
            return mix(inner, VOID, radial * (0.55 - t * 0.4))
        return chitin(fx, fy, fw, fh, seed, DEEP, ROYAL)

    if bone.startswith("pupil"):
        # A pupil is a hole, not a bead. Near-black with a hot core, so the
        # satellite eyes read as the same organ as the big one rather than as
        # teal dice glued to the stalks.
        if radial > 0.55:
            return shade(VOID, -0.3)
        return mix(MAGENTA, WHITE, 0.6)

    if bone.startswith("eye_"):
        if face == "north":
            return mix(mix(ROYAL, MAGENTA, 0.6), WHITE, max(0.0, 0.6 - radial))
        return chitin(fx, fy, fw, fh, seed, VOID, ROYAL)

    if bone.startswith("stalk") or bone.startswith("tent") or bone.startswith("barb"):
        # Tentacles darken and cool toward the tip, with a lit stripe down the
        # front so a writhing limb still reads against a dark sky.
        band = 1.0 if fy % 4 == 0 else 0.0
        base = chitin(fx, fy, fw, fh, seed, VOID, ROYAL)
        return mix(base, ORCHID if bone.startswith("stalk") else MAGENTA, band * 0.45)

    if bone.startswith("spike"):
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(ROYAL, ORCHID, 0.4), WHITE, max(0.0, 0.4 - t * 0.4))

    if bone == "lid":
        return edge_light(chitin(fx, fy, fw, fh, seed, VOID, VIOLET), fx, fy, fw, fh)

    # Shell and core: dark faceted chitin with veins of light running through.
    base = chitin(fx, fy, fw, fh, seed, VOID, ROYAL)
    vein = fbm(fx * 3.0, fy * 3.0, 16, seed + 808, octaves=2, base_period=6)
    if vein > 0.82:
        return mix(base, MAGENTA, (vein - 0.82) / 0.18 * 0.8)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_ender_overlord", roughness=150,
     emissive_from=MAGENTA[:3], emissive_gain=1.8, emissive_threshold=0.26)
print("overlord texture written")
