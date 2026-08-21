import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0814")
HIDE    = hex_rgba("#37294A")   # a grazer's dusty coat, not void-black
DARK    = hex_rgba("#1C1330")
BLOTCH  = hex_rgba("#6B2E9C")
CHORUS  = hex_rgba("#8E44C4")
FRUIT   = hex_rgba("#C060E8")
MAGENTA = hex_rgba("#FF6BFF")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#CBBEDA")
HOOF    = hex_rgba("#241A33")

geo = json.load(open("RP/models/entity/chorus_cow.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def coat(fx, fy, fw, fh, seed):
    """Cow hide: a plain dusty base broken by big soft blotches of the purple
    that has got into it. The blotches are what makes it read as a cow rather
    than as a purple animal - patches, not a tint."""
    n = fbm(fx * 1.6, fy * 1.6, 16, seed, octaves=2, base_period=7)
    grain = fbm(fx * 3.6, fy * 3.6, 16, seed + 91, octaves=2, base_period=3)
    base = mix(DARK, HIDE, 0.3 + grain * 0.5)
    if n > 0.62:
        edge = min(1.0, (n - 0.62) / 0.12)
        return mix(base, mix(BLOTCH, CHORUS, grain * 0.5), 0.35 + edge * 0.45)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith("fruit"):
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        return mix(mix(FRUIT, MAGENTA, 0.4), WHITE, max(0.0, 0.7 - r * 0.9))
    if bone.startswith(("stem", "bud")):
        n = fbm(fx * 3.0, fy * 3.0, 16, seed, octaves=2, base_period=3)
        base = mix(mix(CHORUS, BLOTCH, 0.45), FRUIT, n * 0.4)
        if fy == 0:
            return mix(base, FRUIT, 0.4)         # a lit joint collar
        return shade(base, -0.12 + n * 0.2)
    if bone.startswith("horn"):
        return mix(ASH, DARK, 0.15 + t * 0.7)
    if "_tooth_" in bone:
        return mix(ASH, DARK, 0.25 + t * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#150610"), MAGENTA, 0.2)
    if "_eye_" in bone:
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(MAGENTA, FRUIT, 0.35)
    if bone.endswith("_snout"):
        # A soft pink muzzle, the way a cow's is.
        return mix(mix(HIDE, MAGENTA, 0.35), FRUIT, 0.15 + (1.0 - t) * 0.2)
    if bone.startswith(("udder", "teat")):
        return mix(mix(HIDE, MAGENTA, 0.3), DARK, t * 0.4)
    if bone == "tuft":
        return mix(DARK, CHORUS, 0.2 + t * 0.4)
    if bone.endswith("_foot"):
        return mix(HOOF, VOID, t * 0.4)

    return edge_light(coat(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_chorus_cow", roughness=222,
     emissive_from=FRUIT[:3], emissive_gain=1.5, emissive_threshold=0.42)
print("chorus cow texture written")
