import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0A0714")
DEEP    = hex_rgba("#180A30")
ROYAL   = hex_rgba("#2E1052")
PLUM    = hex_rgba("#4C1C78")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
WHITE   = hex_rgba("#FFFFFF")
STONE   = hex_rgba("#D9D2A6")   # swallowed end stone

geo = json.load(open("RP/models/entity/void_slime.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def jelly(fx, fy, fw, fh, seed):
    """Semi-clear void jelly. Bedrock will not give us real transparency on an
    entity, so depth is faked the way a painter fakes it: a bright rim where
    the light grazes the surface, a dark interior, and slow drifting cloud so
    the volume never reads as a flat wall of colour."""
    n = fbm(fx * 1.5, fy * 1.5, 16, seed, octaves=3, base_period=6)
    base = mix(ROYAL, PLUM, 0.25 + n * 0.6)
    edge = min(fx, fy, fw - 1 - fx, fh - 1 - fy)
    # A rim this much brighter than a near-black interior turns every slab
    # into a lit picture frame around a hole, and the stack reads as shelving.
    # The interior carries the colour; the rim only leans on it.
    if edge == 0:
        return mix(base, ORCHID, 0.3)           # the grazing rim
    if n > 0.86:
        return mix(base, ORCHID, 0.22)          # a suspended wisp
    if n < 0.14:
        return mix(base, DEEP, 0.5)             # a denser clot
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone == "core":
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        return mix(mix(ORCHID, MAGENTA, 0.5), WHITE, max(0.0, 1.0 - r * 1.3))
    if bone == "socket":
        return mix(DEEP, ROYAL, 0.3 + t * 0.3)
    if bone == "halo":
        # A soft shell around the core so the light looks like it is coming
        # through jelly rather than off a cube.
        n = fbm(fx * 2.2, fy * 2.2, 16, seed, octaves=2, base_period=4)
        return mix(mix(ROYAL, ORCHID, 0.5), MAGENTA, 0.15 + n * 0.35)
    if bone.startswith("rubble"):
        # End stone it has not finished dissolving - the one warm colour on it.
        n = fbm(fx * 3.4, fy * 3.4, 16, seed, octaves=3, base_period=3)
        rock = mix(mix(STONE, ROYAL, 0.35), STONE, n * 0.5)
        return shade(rock, -0.15 + n * 0.2)
    if bone.startswith("shard"):
        return mix(mix(STONE, ORCHID, 0.4), WHITE, max(0.0, 0.5 - t * 0.6))
    if bone == "gullet":
        return mix(hex_rgba("#08030C"), MAGENTA, 0.12 + (1.0 - t) * 0.2)
    if bone.startswith("eye_"):
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(MAGENTA, ORCHID, 0.3)
    if bone.startswith("lip"):
        base = jelly(fx, fy, fw, fh, seed)
        return mix(base, MAGENTA, 0.3) if (fy == 0 or fy == fh - 1) else base
    if bone.startswith("drip"):
        return mix(jelly(fx, fy, fw, fh, seed), ORCHID, 0.15 + t * 0.35)

    return jelly(fx, fy, fw, fh, seed)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_void_slime", roughness=90,
     emissive_from=MAGENTA[:3], emissive_gain=1.8, emissive_threshold=0.3)
print("void slime texture written")
