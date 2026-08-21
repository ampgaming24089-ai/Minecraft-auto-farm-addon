import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0711")
ROYAL   = hex_rgba("#300D4D")
CHORUS  = hex_rgba("#7A4A8C")
CHORUS2 = hex_rgba("#B08AC4")
MAGENTA = hex_rgba("#FF3DFF")
AMBER   = hex_rgba("#FFC24A")
WHITE   = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/chorus_fiend.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def flesh(fx, fy, fw, fh, seed):
    """Chorus plant: pale mottled violet with darker pores, not a smooth
    surface - the vanilla block is blotchy and it should still read as kin."""
    n = fbm(fx * 2.2, fy * 2.2, 16, seed, octaves=3, base_period=4)
    base = mix(CHORUS, ROYAL, 0.2 + n * 0.5)
    if n > 0.76:
        return mix(base, CHORUS2, 0.55)
    if n < 0.22:
        return shade(base, -0.28)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    if bone.startswith("glow"):
        return mix(AMBER, WHITE, 0.5)
    if bone == "hollow":
        # A burned-out cavity: black at the rim, hot at the back.
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        return mix(mix(AMBER, MAGENTA, 0.4), VOID, min(1.0, r * 1.3))
    if bone.startswith("bud"):
        # Buds glow from the inside, brightest at the tip of each branch.
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        return mix(mix(MAGENTA, AMBER, 0.3), flesh(fx, fy, fw, fh, seed), r * 0.75)
    if "knuckle" in bone:
        return shade(flesh(fx, fy, fw, fh, seed), -0.24)
    if bone.startswith("root"):
        return shade(flesh(fx, fy, fw, fh, seed), -0.18)
    base = flesh(fx, fy, fw, fh, seed)
    # Veins of light running up the trunk toward the buds.
    vein = fbm(fx * 3.0, fy * 3.0, 16, seed + 313, octaves=2, base_period=6)
    if vein > 0.85:
        return mix(base, MAGENTA, (vein - 0.85) / 0.15 * 0.8)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_chorus_fiend", roughness=214,
     emissive_from=MAGENTA[:3], emissive_gain=1.6, emissive_threshold=0.3)
print("chorus fiend texture written")
