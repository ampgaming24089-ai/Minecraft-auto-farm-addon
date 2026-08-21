import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#090610")
DEEP    = hex_rgba("#170A2B")
ROYAL   = hex_rgba("#34115A")
PLUM    = hex_rgba("#55207F")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#B7A9C4")

geo = json.load(open("RP/models/entity/endermite_hive.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def chitin(fx, fy, fw, fh, seed, lift=0.0):
    """Segment plate: fine scaled grain, banded so each segment has a lit
    leading edge and falls away into shadow at its trailing one."""
    n = fbm(fx * 2.9, fy * 2.9, 16, seed, octaves=3, base_period=3)
    base = mix(VOID, ROYAL, 0.22 + n * 0.5 + lift)
    if n > 0.84:
        return mix(base, PLUM, 0.45)
    if n < 0.15:
        return shade(base, -0.35)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith("brood"):
        # A larva in its cell. Flooding the whole face with near-white turns
        # it into a blank sticker on the shell, so the light is radial: a
        # small hot core, saturated magenta around it, dark at the rim where
        # the cell wall is.
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        n = fbm(fx * 3.0, fy * 3.0, 16, seed, octaves=2, base_period=3)
        if r > 0.86:
            return shade(DEEP, -0.25)
        core = max(0.0, 1.0 - r * 1.5) + n * 0.12
        return mix(mix(ROYAL, MAGENTA, 0.55), mix(MAGENTA, WHITE, 0.55),
                   min(1.0, core))
    if bone.startswith("cell"):
        # The rim: dark, so the brood inside it looks sunk into the shell.
        if 0 < fx < fw - 1 and 0 < fy < fh - 1 and face == "up":
            return mix(ROYAL, MAGENTA, 0.4)
        return shade(chitin(fx, fy, fw, fh, seed), -0.3)
    if bone.startswith("rift"):
        return mix(mix(MAGENTA, ORCHID, 0.4), WHITE, max(0.0, 0.4 - t * 0.5))
    if bone.startswith("miteeye") or bone.startswith("eye_"):
        return mix(MAGENTA, WHITE, 0.5)
    if "_eye_" in bone:
        return shade(VOID, -0.35) if (fy == 0 or fx == 0) else mix(MAGENTA, WHITE, 0.45)
    if bone.startswith("mite"):
        return chitin(fx, fy, fw, fh, seed, lift=0.1)
    if bone.startswith("mandible") or "_tooth_" in bone:
        return mix(ASH, ROYAL, 0.2 + t * 0.6)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0A0308"), MAGENTA, 0.25)
    if bone.startswith("lip"):
        base = chitin(fx, fy, fw, fh, seed, lift=0.14)
        return mix(base, ORCHID, 0.3) if fy == 0 else edge_light(base, fx, fy, fw, fh)
    if bone.startswith("leg"):
        base = chitin(fx, fy, fw, fh, seed)
        return mix(base, PLUM, 0.35) if fy % 4 == 0 else base

    return edge_light(chitin(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_endermite_hive", roughness=170,
     emissive_from=MAGENTA[:3], emissive_gain=1.9, emissive_threshold=0.3)
print("endermite hive texture written")
