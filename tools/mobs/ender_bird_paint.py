import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#08060F")
DARK    = hex_rgba("#150B26")
SLATE   = hex_rgba("#2E1B4A")
STEEL   = hex_rgba("#4A3268")
ORCHID  = hex_rgba("#9A48E0")
MAGENTA = hex_rgba("#FF5CE8")
CYAN    = hex_rgba("#7BEEFF")
WHITE   = hex_rgba("#FFFFFF")
HORN    = hex_rgba("#C9BCD6")

geo = json.load(open("RP/models/entity/ender_bird.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def plume(fx, fy, fw, fh, seed, lift=0.0):
    """Body feathers: overlapping scallops rather than noise. A bird painted
    with a fur grain reads as a rodent, so the pattern is banded across the
    face with a lit edge at the top of every band - that is what an eye reads
    as feathers."""
    band = fy % 4
    n = fbm(fx * 3.0, fy * 3.0, 16, seed, octaves=2, base_period=3)
    base = mix(DARK, SLATE, 0.25 + n * 0.45 + lift)
    if band == 0:
        return mix(base, STEEL, 0.4)             # the lit lip of a feather
    if band == 3:
        return shade(base, -0.3)                 # the shadow under it
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith(("primary", "tailfeather")):
        # Flight feathers: a dark shaft down the middle, a lit vane either
        # side, and a cold burning tip.
        along = fx / max(1.0, fw - 1.0)
        base = mix(DARK, SLATE, 0.2 + t * 0.4)
        if abs(along - 0.5) < 0.2:
            base = shade(base, -0.35)            # the shaft
        n = fbm(fx * 2.0, fy * 4.0, 16, seed, octaves=2, base_period=4)
        base = mix(base, STEEL, n * 0.35)
        if fy <= 1:
            return mix(base, mix(ORCHID, CYAN, 0.4), 0.4)
        return base
    if bone.startswith("quill"):
        return mix(mix(SLATE, ORCHID, 0.4), CYAN, max(0.0, 0.6 - t * 0.7))
    if bone.startswith("talon") or bone.startswith("spur"):
        return mix(HORN, DARK, 0.2 + t * 0.6)
    if bone.startswith(("thigh", "shank")):
        return mix(mix(DARK, STEEL, 0.35), VOID, t * 0.3)
    if "_tooth_" in bone:
        return mix(HORN, SLATE, 0.25 + t * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0C0410"), MAGENTA, 0.24)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(CYAN, MAGENTA, 0.35)
    if bone.startswith("head_snout") or bone == "head_jaw":
        # The bill: smooth horn, not feathers, and paler toward the tip.
        depth = fx / max(1.0, fw - 1.0)
        return mix(mix(SLATE, HORN, 0.35), HORN, max(0.0, 0.55 - depth * 0.6))
    if bone.startswith("wing_") and "_web" in bone:
        return plume(fx, fy, fw, fh, seed, lift=-0.05)
    if bone.startswith("covert"):
        return plume(fx, fy, fw, fh, seed, lift=0.08)

    return edge_light(plume(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_ender_bird", roughness=196,
     emissive_from=CYAN[:3], emissive_gain=1.7, emissive_threshold=0.36)
print("ender bird texture written")
