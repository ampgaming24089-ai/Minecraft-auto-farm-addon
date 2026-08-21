import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0A0714")
DEEP    = hex_rgba("#1A0C31")
ROYAL   = hex_rgba("#331451")
MAUVE   = hex_rgba("#5D3B7A")
ORCHID  = hex_rgba("#A75CFF")
MAGENTA = hex_rgba("#FF6BFF")
CYAN    = hex_rgba("#8AF3FF")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#CBBEDA")

geo = json.load(open("RP/models/entity/ender_deer.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def pelt(fx, fy, fw, fh, seed, lift=0.0):
    """Short fur: a fine directional grain, paler along the back and dark
    underneath, with faint constellation flecks scattered through it."""
    n = fbm(fx * 2.4, fy * 3.2, 16, seed, octaves=3, base_period=4)
    t = fy / max(1.0, fh - 1.0)
    base = mix(DEEP, MAUVE, 0.3 + n * 0.5 + lift)
    base = mix(base, VOID, t * 0.35)             # counter-shading
    if n > 0.93:
        return mix(base, CYAN, 0.55)             # a fleck
    if n < 0.12:
        return shade(base, -0.3)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith("antler"):
        # Grown crystal, not bone: dark at the skull, lit at every point.
        heat = max(0.0, 1.0 - t * 1.6)
        return mix(mix(ROYAL, ORCHID, 0.45), mix(CYAN, WHITE, 0.4),
                   0.15 + heat * 0.7)
    if bone.startswith("ridge"):
        return mix(mix(ROYAL, ORCHID, 0.5), CYAN, max(0.0, 0.55 - t * 0.6))
    if bone == "flag":
        return mix(ASH, MAUVE, 0.2 + t * 0.5)
    if bone.startswith("ear"):
        return mix(pelt(fx, fy, fw, fh, seed), MAGENTA, max(0.0, 0.3 - t * 0.4))
    if "_tooth_" in bone:
        return mix(ASH, ROYAL, 0.25 + t * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0A0308"), MAGENTA, 0.2)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(CYAN, MAGENTA, 0.35)
    if "_toe" in bone or bone.endswith("_foot"):
        # Dark polished hooves - the one hard surface on the animal.
        return mix(VOID, ROYAL, 0.15 + (1.0 - t) * 0.3)
    if bone.startswith(("fore_", "hind_")):
        return pelt(fx, fy, fw, fh, seed, lift=-0.04)

    return edge_light(pelt(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_ender_deer", roughness=214,
     emissive_from=CYAN[:3], emissive_gain=1.7, emissive_threshold=0.34)
print("ender deer texture written")
