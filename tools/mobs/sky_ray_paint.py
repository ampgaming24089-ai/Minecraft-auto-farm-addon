import sys, json, math
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

# The End palette from the reference sheet.
VOID     = hex_rgba("#0B0711")
DEEP     = hex_rgba("#1A0830")
ROYAL    = hex_rgba("#300D4D")
VIOLET   = hex_rgba("#6B1FFF")
ORCHID   = hex_rgba("#A640FF")
CYAN     = hex_rgba("#00E6FF")
ICE      = hex_rgba("#B4FFF9")
WHITE    = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/sky_ray.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)

def painter(bone, face, fx, fy, fw, fh):
    top = face == "up"
    belly = face == "down"
    n = fbm(fx * 1.7, fy * 1.7, 16, hash(bone) & 0xffff, octaves=3, base_period=4)

    if bone.startswith("wing"):
        # Wings: dark topside, luminous underside with rib lines showing
        # through the membrane, which is how a real ray reads from below.
        if belly:
            band = 1.0 if (fy % 4 == 0) else 0.0
            return mix(mix(DEEP, CYAN, 0.55 + n * 0.2), ICE, band * 0.55)
        base = mix(DEEP, ROYAL, n * 0.7)
        if top and fy % 5 == 0:
            base = mix(base, VIOLET, 0.35)
        return edge_light(base, fx, fy, fw, fh)

    if bone.startswith("ridge"):
        return mix(mix(ROYAL, ORCHID, 0.35 + n * 0.4), WHITE, 0.15 if fy == 0 else 0.0)

    if bone.startswith("gill"):
        return mix(CYAN, ICE, 0.4 + n * 0.4)

    if bone.startswith("tail") or bone == "barb":
        t = float(bone.split("_")[-1]) / 8.0 if bone.startswith("tail_") else 1.0
        base = mix(mix(DEEP, ROYAL, n * 0.6), VIOLET, t * 0.45)
        return edge_light(base, fx, fy, fw, fh)

    if bone == "head" or bone.startswith("horn"):
        if face == "north" and bone == "head":
            # Two lit eyes and a bright brow bar.
            if fy in (1, 2) and fx in (2, 3, fw - 4, fw - 3):
                return CYAN if fy == 1 else ICE
            if fy == 0:
                return mix(ORCHID, WHITE, 0.35)
        base = mix(DEEP, ROYAL, 0.35 + n * 0.5)
        if bone.startswith("horn"):
            base = mix(base, ORCHID, 0.45 - fy / max(1.0, fh) * 0.35)
        return edge_light(base, fx, fy, fw, fh)

    # Body: dark violet hide above, glowing belly, a lit lateral line.
    if belly:
        mid = 1.0 - abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
        return mix(mix(DEEP, CYAN, 0.4), ICE, mid * 0.55)
    base = mix(VOID, ROYAL, 0.35 + n * 0.55)
    if top:
        base = mix(base, VIOLET, 0.25 if (fy % 4 < 2) else 0.05)
    if face in ("east", "west") and fy == fh // 2:
        base = mix(base, CYAN, 0.6)      # lateral line
    return edge_light(base, fx, fy, fw, fh)

paint(c, geo, painter)
emit(c, ENTITY, "voidbound_sky_ray", roughness=170,
     emissive_from=CYAN[:3], emissive_gain=1.5, emissive_threshold=0.26)
print("sky ray texture written")
