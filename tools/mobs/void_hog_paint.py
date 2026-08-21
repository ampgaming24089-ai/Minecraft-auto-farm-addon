import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0A0712")
DARK    = hex_rgba("#1B1229")
HIDE    = hex_rgba("#3B2A48")   # coarse grey-violet bristle
MUD     = hex_rgba("#4A3350")
ORCHID  = hex_rgba("#9A48E0")
MAGENTA = hex_rgba("#FF5CE8")
EMBER   = hex_rgba("#FF8A3D")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#C9BCD6")

geo = json.load(open("RP/models/entity/void_hog.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def bristly(fx, fy, fw, fh, seed, lift=0.0):
    """Coarse hair over thick hide: a strong vertical grain, with the hair
    lying darker where it thickens over the shoulder."""
    hair = fbm(fx * 4.2, fy * 1.6, 16, seed, octaves=2, base_period=3)
    cloud = fbm(fx * 1.4, fy * 1.4, 16, seed + 57, octaves=2, base_period=8)
    base = mix(DARK, HIDE, 0.25 + hair * 0.5 + lift)
    base = mix(base, MUD, cloud * 0.35)
    if hair > 0.86:
        return mix(base, ASH, 0.2)               # a pale guard hair
    if hair < 0.14:
        return shade(base, -0.35)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith(("tusk", "uptusk")) or "_tooth_" in bone:
        # Old ivory, stained toward the root.
        return mix(ASH, mix(MUD, DARK, 0.5), 0.15 + t * 0.7)
    if bone.startswith(("bristle", "backbristle")):
        return mix(mix(DARK, ORCHID, 0.3), MAGENTA, max(0.0, 0.45 - t * 0.55))
    if bone == "disc":
        # The snout disc, damp and pink.
        return mix(mix(MUD, MAGENTA, 0.4), DARK, t * 0.35)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#140510"), EMBER, 0.2)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(EMBER, MAGENTA, 0.4)
    if bone.startswith("ear"):
        return mix(bristly(fx, fy, fw, fh, seed), MUD, max(0.0, 0.3 - t * 0.35))
    if bone == "tuft":
        return mix(DARK, ORCHID, 0.2 + t * 0.35)
    if "_toe" in bone or bone.endswith("_foot"):
        return mix(hex_rgba("#231830"), VOID, t * 0.45)
    if bone == "crest":
        return bristly(fx, fy, fw, fh, seed, lift=0.08)

    return edge_light(bristly(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_void_hog", roughness=228,
     emissive_from=MAGENTA[:3], emissive_gain=1.5, emissive_threshold=0.4)
print("void hog texture written")
