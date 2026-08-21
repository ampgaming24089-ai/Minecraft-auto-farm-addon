import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#080611")
DEEP    = hex_rgba("#150927")
ROYAL   = hex_rgba("#2C1050")
SLATE   = hex_rgba("#463A63")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
CYAN    = hex_rgba("#63E8FF")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#BEB0CE")

geo = json.load(open("RP/models/entity/teleporter.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def hide(fx, fy, fw, fh, seed, lift=0.0):
    """Ender hide: matte black-violet with a fine noise and a cold sheen along
    the top of each plane, so a body made of separated blocks still reads as
    one material."""
    n = fbm(fx * 2.6, fy * 2.6, 16, seed, octaves=3, base_period=4)
    base = mix(VOID, ROYAL, 0.2 + n * 0.45 + lift)
    if fy == 0:
        return mix(base, SLATE, 0.4)
    if n > 0.85:
        return mix(base, SLATE, 0.25)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith("rift"):
        # The tear between the pieces. Hot in the middle, cold at the edges,
        # because this is the one place you can see through the mob.
        r = abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
        return mix(mix(MAGENTA, WHITE, 0.5), mix(ORCHID, CYAN, 0.4),
                   min(1.0, r * 1.2))
    if bone.startswith("ring"):
        return mix(mix(CYAN, ORCHID, 0.4), WHITE, 0.25 + (1.0 - t) * 0.3)
    if bone.startswith("spike"):
        return mix(mix(ROYAL, ORCHID, 0.5), CYAN, max(0.0, 0.6 - t * 0.7))
    if bone.startswith("digit"):
        return mix(mix(ASH, ROYAL, 0.4), MAGENTA, max(0.0, 0.4 - t * 0.5))
    if "_tooth_" in bone:
        return mix(ASH, ROYAL, 0.25 + t * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#08030C"), MAGENTA, 0.28)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(MAGENTA, CYAN, 0.3)
    if bone.startswith("leg_"):
        # The legs are already half gone: each link further down is fainter.
        depth = bone.rsplit("_", 1)[-1]
        depth = int(depth) if depth.isdigit() else 0
        return mix(hide(fx, fy, fw, fh, seed), mix(ORCHID, VOID, 0.6),
                   min(0.8, 0.1 + depth * 0.22))
    if bone.startswith(("pauldron", "hand")):
        base = hide(fx, fy, fw, fh, seed, lift=0.12)
        # A lit seam around the broken faces, so the pieces look cut, not lost.
        if fx in (0, fw - 1) or fy in (0, fh - 1):
            return mix(base, ORCHID, 0.35)
        return base

    return edge_light(hide(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_teleporter", roughness=140,
     emissive_from=MAGENTA[:3], emissive_gain=2.0, emissive_threshold=0.28)
print("teleporter texture written")
