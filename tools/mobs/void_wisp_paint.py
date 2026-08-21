import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#070510")
DEEP    = hex_rgba("#130826")
ROYAL   = hex_rgba("#2A0F4A")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
CYAN    = hex_rgba("#6FF0FF")
WHITE   = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/void_wisp.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def rag(fx, fy, fw, fh, seed, fade=1.0):
    """Shadow-cloth: dark, softly clouded, and thinning toward the hem where
    the light from the core comes through it."""
    n = fbm(fx * 2.0, fy * 2.0, 16, seed, octaves=3, base_period=5)
    t = fy / max(1.0, fh - 1.0)
    base = mix(VOID, ROYAL, 0.15 + n * 0.4)
    lit = mix(base, mix(ORCHID, MAGENTA, 0.4), t * 0.55 * fade)
    if n > 0.86:
        return mix(lit, ORCHID, 0.25)
    return lit


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone == "core":
        return mix(mix(CYAN, WHITE, 0.5), MAGENTA, 0.2)
    if bone == "glow":
        n = fbm(fx * 2.6, fy * 2.6, 16, seed, octaves=2, base_period=4)
        return mix(mix(ORCHID, MAGENTA, 0.4), CYAN, 0.2 + n * 0.35)
    if bone.startswith("mote"):
        return mix(CYAN, MAGENTA, 0.35)
    if bone.startswith("flare"):
        return mix(mix(CYAN, WHITE, 0.4), MAGENTA, 0.15 + t * 0.5)
    if bone.startswith("trail"):
        # Fading out along the chain: later links are darker, so the tail
        # dissolves instead of stopping.
        depth = int(bone.rsplit("_", 1)[-1]) if bone.rsplit("_", 1)[-1].isdigit() else 0
        return mix(mix(ORCHID, MAGENTA, 0.4), VOID, min(0.85, 0.12 + depth * 0.19))
    if "_tooth_" in bone:
        return mix(hex_rgba("#CFC3E0"), ROYAL, 0.2 + t * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#08030C"), MAGENTA, 0.3)
    if "_eye_" in bone:
        return shade(VOID, -0.4) if (fy == 0 or fx == 0) else mix(CYAN, WHITE, 0.5)
    if bone.startswith("face"):
        # The face is lit from inside the hood, brightest at the mouth line.
        return mix(mix(ROYAL, ORCHID, 0.4), MAGENTA, max(0.0, t - 0.3) * 0.6)
    if bone in ("cowl", "nape"):
        return rag(fx, fy, fw, fh, seed, fade=0.35)
    if bone.startswith("rag"):
        return rag(fx, fy, fw, fh, seed, fade=1.0 if "hem" in bone else 0.7)

    return edge_light(rag(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_void_wisp", roughness=110,
     emissive_from=CYAN[:3], emissive_gain=2.1, emissive_threshold=0.26)
print("void wisp texture written")
