import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0711")
DEEP    = hex_rgba("#1A0830")
ROYAL   = hex_rgba("#300D4D")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
WHITE   = hex_rgba("#FFFFFF")
ICE     = hex_rgba("#B4FFF9")

geo = json.load(open("RP/models/entity/void_stalker.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def pelt(fx, fy, fw, fh, seed):
    """Short dense fur: fine vertical strokes, not blotches. Noise alone on a
    predator reads as mud."""
    n = fbm(fx * 2.0, fy * 5.0, 16, seed, octaves=3, base_period=3)
    base = mix(VOID, DEEP, 0.25 + n * 0.5)
    if n > 0.74:
        return mix(base, ROYAL, 0.45)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    if "_tooth_" in bone:
        return WHITE if fy == 0 else ICE
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0A0308"), MAGENTA, 0.2)
    if "_eye_" in bone:
        if fy in (0, fh - 1) or fx in (0, fw - 1):
            return shade(VOID, -0.35)
        return mix(MAGENTA, WHITE, 0.5)
    if bone.startswith("spine") or bone.startswith("rump"):
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(ROYAL, ORCHID, 0.45), WHITE, max(0.0, 0.4 - t * 0.4))
    if bone.endswith("_brow") or bone.startswith("ear"):
        return mix(pelt(fx, fy, fw, fh, seed), ROYAL, 0.3)
    if bone == "tail_tuft":
        # Fur, not a lamp. Dark at the root, hot only at the very tip, or the
        # tail ends in a glowing dice.
        t = fy / max(1.0, fh - 1.0)
        return mix(pelt(fx, fy, fw, fh, seed), MAGENTA, max(0.0, t - 0.55) * 1.6)

    base = pelt(fx, fy, fw, fh, seed)
    # Tiger striping over the flanks and haunches, so the animal has markings
    # rather than being one dark shape.
    if face in ("east", "west") and bone in ("chest", "hips") :
        if (fx + int(fy * 0.4)) % 6 == 0:
            base = mix(base, ORCHID, 0.35)
    if face == "down":
        base = mix(base, ROYAL, 0.25)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_void_stalker", roughness=210,
     emissive_from=MAGENTA[:3], emissive_gain=1.6, emissive_threshold=0.32)
print("stalker texture written")
