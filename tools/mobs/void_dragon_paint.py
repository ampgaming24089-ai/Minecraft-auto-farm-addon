import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID   = hex_rgba("#0B0711")
DEEP   = hex_rgba("#1A0830")
ROYAL  = hex_rgba("#300D4D")
VIOLET = hex_rgba("#6B1FFF")
ORCHID = hex_rgba("#A640FF")
MAGENTA= hex_rgba("#FF3DFF")
CYAN   = hex_rgba("#00E6FF")
ICE    = hex_rgba("#B4FFF9")
WHITE  = hex_rgba("#FFFFFF")

geo = json.load(open("RP/models/entity/void_dragon.geo.json"))["minecraft:geometry"][0]
c = Canvas(512, 512)


def scaled(fx, fy, fw, fh, seed, base, light):
    """Overlapping scale plates. A dragon whose hide is flat noise reads as
    rubber; the thing the eye wants is rows of hard little edges."""
    row = int(fy) // 2
    off = (int(fx) + row * 2) % 4
    n = fbm(fx * 2.6, fy * 2.6, 16, seed, octaves=2, base_period=4)
    tone = mix(base, light, 0.12 + n * 0.3)
    if off == 0:
        return shade(tone, -0.28)             # the seam between plates
    if int(fy) % 2 == 0:
        return shade(tone, 0.16)              # the lit lip of each plate
    return tone


def glowing_crack(fx, fy, fw, fh, seed, base):
    """Magma-style fissures, but violet: the light comes from inside it."""
    crack = fbm(fx * 3.1, fy * 3.1, 16, seed + 4141, octaves=2, base_period=6)
    if crack > 0.80:
        heat = (crack - 0.80) / 0.20
        return mix(mix(base, MAGENTA, 0.7), WHITE, heat * 0.5)
    if crack > 0.75:
        return mix(base, VIOLET, 0.4)
    return None


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    top, belly = face == "up", face == "down"

    if "web_" in bone:
        # Membrane: translucent-looking, veins running down it, lit from below.
        n = fbm(fx * 1.3, fy * 1.3, 16, seed, octaves=3, base_period=6)
        base = mix(ROYAL, VIOLET, 0.25 + n * 0.35)
        if belly:
            base = mix(base, MAGENTA, 0.35)
        if int(fy) % 6 == 0:
            base = mix(base, ORCHID, 0.55)     # rib shadow through the skin
        return base

    if "finger" in bone or bone.endswith("_fore") or bone.startswith("wing"):
        return edge_light(scaled(fx, fy, fw, fh, seed, VOID, ROYAL), fx, fy, fw, fh)

    if bone.startswith("tooth"):
        return WHITE if fy == 0 else ICE

    if bone.startswith("horn") or bone.startswith("frill") or bone == "brow":
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(DEEP, ROYAL, 0.4), ORCHID, max(0.0, 0.45 - t * 0.45))

    if bone == "skull" or bone == "jaw":
        if bone == "skull" and face == "north":
            if fy in (2, 3) and fx in (1, 2, fw - 3, fw - 2):
                return MAGENTA if fy == 2 else WHITE
        if bone == "jaw" and top:
            return mix(MAGENTA, WHITE, 0.4)    # lit maw
        return edge_light(scaled(fx, fy, fw, fh, seed, VOID, ROYAL), fx, fy, fw, fh)

    if bone.startswith("spine") or bone.startswith("hipspine") or bone.startswith("tailfin"):
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(ROYAL, ORCHID, 0.4), WHITE, max(0.0, 0.35 - t * 0.35))

    # Hide everywhere else: scale plates, a lit belly, and cracks that glow.
    base = VOID if not belly else DEEP
    tone = scaled(fx, fy, fw, fh, seed, base, ROYAL)
    if belly:
        mid = 1.0 - abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
        tone = mix(tone, MAGENTA, 0.2 + mid * 0.35)
    crack = glowing_crack(fx, fy, fw, fh, seed, tone)
    if crack is not None:
        return crack
    return edge_light(tone, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_void_dragon", roughness=176,
     emissive_from=MAGENTA[:3], emissive_gain=1.7, emissive_threshold=0.28)
print("dragon texture written")
