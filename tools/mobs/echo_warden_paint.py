import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#080611")
DEEP    = hex_rgba("#14152B")
STEEL   = hex_rgba("#2E3350")
PALE    = hex_rgba("#5A6488")
CYAN    = hex_rgba("#4FE3E8")
TEAL    = hex_rgba("#1E8A96")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#C3C9D8")

geo = json.load(open("RP/models/entity/echo_warden.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def armour(fx, fy, fw, fh, seed, lift=0.0):
    """Dark blued metal: a hammered grain, a bright top edge on every plate,
    and a wash of verdigris in the low spots."""
    n = fbm(fx * 2.6, fy * 2.6, 16, seed, octaves=3, base_period=4)
    base = mix(DEEP, STEEL, 0.25 + n * 0.5 + lift)
    if fy == 0:
        return mix(base, PALE, 0.45)
    if n < 0.15:
        return mix(shade(base, -0.3), TEAL, 0.25)
    if n > 0.88:
        return mix(base, PALE, 0.3)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone == "resonator":
        # Concentric rings, so it reads as a drum head rather than a lit box.
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        ring = int(r * 4) % 2
        return mix(mix(TEAL, CYAN, 0.6 if ring else 0.2), WHITE,
                   max(0.0, 0.55 - r * 0.7))
    if bone.startswith("ribcage"):
        return mix(armour(fx, fy, fw, fh, seed, lift=0.1), CYAN, 0.2)
    if bone.startswith("vane"):
        # Listening blades, lit along the leading edge only.
        if fx == 0 or fx == fw - 1:
            return mix(CYAN, WHITE, max(0.0, 0.5 - t * 0.5))
        return armour(fx, fy, fw, fh, seed, lift=0.06)
    if bone.startswith("crest"):
        return mix(mix(STEEL, TEAL, 0.5), CYAN, max(0.0, 0.6 - t * 0.7))
    if "_tooth_" in bone or bone.startswith("knuckle"):
        return mix(ASH, STEEL, 0.2 + t * 0.6)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#05080C"), CYAN, 0.3)
    if "_eye_" in bone:
        # It is blind: the sockets are plated over and only hum.
        return mix(TEAL, CYAN, 0.3 + t * 0.3)
    if bone.startswith(("plate", "pauldron", "belt", "fist")):
        return armour(fx, fy, fw, fh, seed, lift=0.12)

    return edge_light(armour(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_echo_warden", metalness=140, roughness=110,
     emissive_from=CYAN[:3], emissive_gain=1.8, emissive_threshold=0.3)
print("echo warden texture written")
