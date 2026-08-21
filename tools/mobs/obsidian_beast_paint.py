import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#08060E")
DEEP    = hex_rgba("#1B0A2E")
ROYAL   = hex_rgba("#3A1060")
MAGENTA = hex_rgba("#FF3DFF")
ORCHID  = hex_rgba("#A640FF")
EMBER   = hex_rgba("#FF7A2E")
GOLD    = hex_rgba("#FFC65A")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#8C7FA6")
IRON    = hex_rgba("#6A5C82")

geo = json.load(open("RP/models/entity/obsidian_beast.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def glass(fx, fy, fw, fh, seed, lift=0.0):
    """Obsidian: near-black with conchoidal facets - big flat planes meeting
    at hard edges, not a rough surface. The highlight is a sharp line, never
    a soft gradient, because that is what volcanic glass does to light.

    The base has to sit off pure black or none of that survives the render:
    a facet you cannot see is just an expensive way to paint a shadow.
    """
    n = fbm(fx * 1.7, fy * 1.7, 16, seed, octaves=2, base_period=5)
    base = mix(VOID, DEEP, 0.35 + n * 0.5 + lift)
    facet = fbm(fx * 3.4, fy * 3.4, 16, seed + 41, octaves=1, base_period=4)
    if facet > 0.74:
        return mix(base, ORCHID, 0.42)          # a plane catching the light
    if facet > 0.66:
        return mix(base, ROYAL, 0.5)            # its shoulder
    if facet < 0.20:
        return shade(base, -0.45)               # a plane facing away
    return base


def molten(base, fx, fy, fw, fh, seed, threshold=0.85):
    """Light out of the cracks, never off the surface."""
    seam = fbm(fx * 3.4, fy * 3.4, 16, seed + 707, octaves=2, base_period=7)
    if seam > threshold:
        t = (seam - threshold) / max(0.01, 1.0 - threshold)
        return mix(base, mix(EMBER, MAGENTA, 0.45), min(1.0, t * 1.3))
    return None


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)                 # 0 at the top of a side face

    if bone.startswith("horn") or bone.startswith("browshard"):
        # Obsidian horns, not bone ones. A gold line down the length read as
        # brass trim, which is the last thing a lump of volcanic glass should
        # look like - so the heat lives at the point and in the fractures.
        base = glass(fx, fy, fw, fh, seed, lift=0.14)
        crack = molten(base, fx, fy, fw, fh, seed, threshold=0.80)
        if crack:
            return crack
        if bone.endswith("_3"):                 # the last segment: the point
            u = fx / max(1.0, fw - 1.0)
            if u < 0.3:
                return mix(base, mix(MAGENTA, WHITE, 0.3), 0.3 + (0.3 - u) * 1.6)
        return edge_light(base, fx, fy, fw, fh)
    if bone.startswith("tusk") or "_tooth_" in bone:
        # Ash-grey, dulled toward the gum. Bright white teeth on a black
        # animal read as a printed sticker.
        return mix(mix(ASH, ROYAL, 0.25), DEEP, min(1.0, t * 0.85))
    if bone.startswith("vent"):
        return mix(EMBER, GOLD, 0.4) if 0 < fx < fw - 1 else shade(VOID, -0.2)
    if bone == "ring":
        n = fbm(fx * 2.6, fy * 2.6, 16, seed, octaves=2, base_period=3)
        return mix(IRON, hex_rgba("#2A2038"), 0.3 + n * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0A0308"), EMBER, (1.0 - t) * 0.6)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)            # a lid and a socket edge
        if fy == 1 and fx == 1:
            return WHITE                        # one specular pixel, no more
        return mix(EMBER, MAGENTA, 0.3 + t * 0.4)
    if bone.startswith(("shard", "rumpshard", "splinter", "macespike")):
        # A shard is a piece of the same black glass. It is lit from inside
        # near the point and nowhere else, so the eye reads a hot tip rather
        # than a pink block.
        base = glass(fx, fy, fw, fh, seed, lift=0.05)
        if t < 0.24:
            heat = (0.24 - t) / 0.24
            return mix(base, mix(MAGENTA, WHITE, heat * 0.4), 0.18 + heat * 0.55)
        return edge_light(base, fx, fy, fw, fh)
    if bone == "tailmace" or bone.startswith("collar") or bone.startswith("plate"):
        base = glass(fx, fy, fw, fh, seed, lift=0.08)
        crack = molten(base, fx, fy, fw, fh, seed, threshold=0.80)
        return crack or edge_light(base, fx, fy, fw, fh)

    base = glass(fx, fy, fw, fh, seed)
    return molten(base, fx, fy, fw, fh, seed) or edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_obsidian_beast", metalness=60, roughness=64,
     emissive_from=EMBER[:3], emissive_gain=1.8, emissive_threshold=0.28)
print("obsidian beast texture written")
