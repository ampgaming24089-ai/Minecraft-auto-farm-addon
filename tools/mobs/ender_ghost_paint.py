import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#070510")
DEEP    = hex_rgba("#120824")
ROYAL   = hex_rgba("#281046")
SLATE   = hex_rgba("#3E3159")
ORCHID  = hex_rgba("#9A3CF5")
MAGENTA = hex_rgba("#FF3DFF")
CYAN    = hex_rgba("#7CF2FF")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#C4B7D4")

geo = json.load(open("RP/models/entity/ender_ghost.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def cloth(fx, fy, fw, fh, seed, lift=0.0):
    """Grave-cloth: a coarse woven grain, worn pale along the top of every
    fold and rotted dark in the hollows."""
    weave = (fx + fy) % 3 == 0
    n = fbm(fx * 2.2, fy * 2.2, 16, seed, octaves=3, base_period=5)
    base = mix(VOID, ROYAL, 0.16 + n * 0.42 + lift)
    if weave and n > 0.5:
        base = mix(base, SLATE, 0.22)
    if n > 0.87:
        return mix(base, SLATE, 0.35)            # a worn thread
    if n < 0.13:
        return shade(base, -0.4)                 # rot
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if "_tooth_" in bone:
        return mix(ASH, ROYAL, 0.2 + t * 0.55)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#07020A"), CYAN, 0.22)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.45)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(CYAN, WHITE, 0.35)
    if bone.startswith("face"):
        # The only lit part of it. Cold, not hot - a ghost is not a furnace.
        return mix(mix(ROYAL, ORCHID, 0.35), CYAN, max(0.0, 0.55 - t * 0.5))
    if bone.startswith("claw"):
        return mix(mix(ASH, ROYAL, 0.35), CYAN, max(0.0, 0.5 - t * 0.6))
    if bone.startswith("crest"):
        return cloth(fx, fy, fw, fh, seed, lift=0.05)
    if bone.startswith("tatter"):
        # Fraying out: the further down a strip, the more of it has gone.
        fade = 0.55 if bone.endswith("_end") else 0.2
        return mix(cloth(fx, fy, fw, fh, seed), VOID, min(0.85, fade + t * 0.45))
    if bone.startswith("wisp"):
        depth = bone.rsplit("_", 1)[-1]
        depth = int(depth) if depth.isdigit() else 0
        return mix(mix(ORCHID, ROYAL, 0.5), VOID, min(0.88, 0.2 + depth * 0.2))
    if bone in ("mantle", "collar", "brim"):
        base = cloth(fx, fy, fw, fh, seed, lift=0.1)
        # A thread of cold light picked out along the mantle's top edge.
        if fy == 0:
            return mix(base, CYAN, 0.28)
        return edge_light(base, fx, fy, fw, fh)

    return edge_light(cloth(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_ender_ghost", roughness=205,
     emissive_from=CYAN[:3], emissive_gain=1.9, emissive_threshold=0.3)
print("ender ghost texture written")
