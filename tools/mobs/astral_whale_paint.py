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
CYAN   = hex_rgba("#00E6FF")
ICE    = hex_rgba("#B4FFF9")
WHITE  = hex_rgba("#FFFFFF")
# The ironmongery. Warm metal against a cold animal is the whole contrast the
# design rests on, so the gold is genuinely gold and not a tinted violet.
GOLD   = hex_rgba("#E8C766")
GOLD_HI = hex_rgba("#FFF0B4")
GOLD_LO = hex_rgba("#7A5C1E")
LAMP   = hex_rgba("#FFD98A")

geo = json.load(open("RP/models/entity/astral_whale.geo.json"))["minecraft:geometry"][0]
c = Canvas(512, 512)


def metal(fx, fy, fw, fh, seed):
    """Struck gold: a bright top edge, a dark bottom, and hammer marks."""
    n = fbm(fx * 2.4, fy * 2.4, 16, seed, octaves=2, base_period=3)
    base = mix(GOLD, GOLD_LO, 0.35 + n * 0.4)
    if fy == 0:
        return GOLD_HI
    if fy == fh - 1:
        return GOLD_LO
    if n > 0.72:
        return mix(base, GOLD_HI, 0.5)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    n = fbm(fx * 1.5, fy * 1.5, 16, seed, octaves=3, base_period=5)
    top, belly = face == "up", face == "down"

    if bone.startswith("strap") and "lantern" not in bone:
        if "buckle" in bone:
            # A buckle needs a hole through it or it is just a gold box.
            if 1 < fx < fw - 2 and 1 < fy < fh - 2:
                return shade(GOLD_LO, -0.35)
            return metal(fx, fy, fw, fh, seed)
        if "chain" in bone:
            return GOLD_LO if fy % 2 else GOLD
        return metal(fx, fy, fw, fh, seed)

    if "lantern" in bone:
        # Gold cage, lit core, brightest through the side panels.
        if fx in (0, fw - 1) or fy in (0, fh - 1):
            return metal(fx, fy, fw, fh, seed)
        return mix(LAMP, WHITE, 0.35 + n * 0.4)

    if bone.startswith("banner"):
        # Cloth: a violet field with a gold border and a cyan sigil.
        if fx in (0, fw - 1):
            return GOLD
        if fy == fh - 1:
            return GOLD_LO
        if abs(fx - fw / 2.0) < 1.6 and 2 < fy < fh - 3:
            return CYAN
        return mix(ROYAL, VIOLET, 0.3 + n * 0.4)

    if bone.startswith("ridge"):
        return mix(mix(ROYAL, ORCHID, 0.3 + n * 0.45), WHITE, 0.2 if fy == 0 else 0.0)

    if bone.startswith("baleen"):
        return mix(ICE, DEEP, 0.3 + (fx % 2) * 0.5)

    if bone.startswith("fluke") or bone.startswith("fin"):
        if belly:
            band = 1.0 if fy % 4 == 0 else 0.0
            return mix(mix(DEEP, CYAN, 0.5 + n * 0.2), ICE, band * 0.5)
        return edge_light(mix(DEEP, ROYAL, n * 0.7), fx, fy, fw, fh)

    if bone in ("head", "brow", "jaw", "blowhole"):
        if bone == "head" and face == "north":
            if fy in (5, 6) and fx in (3, 4, fw - 5, fw - 4):
                return CYAN if fy == 5 else ICE
        if bone == "brow":
            return mix(metal(fx, fy, fw, fh, seed), ROYAL, 0.25)   # gold browplate
        base = mix(VOID, ROYAL, 0.3 + n * 0.5)
        if bone == "blowhole":
            return mix(base, CYAN, 0.5)
        return edge_light(base, fx, fy, fw, fh)

    if bone.startswith("tail"):
        return edge_light(mix(mix(DEEP, ROYAL, n * 0.6), VIOLET, 0.3), fx, fy, fw, fh)

    # Hull. Dark violet hide, a lit belly, a lateral line, and constellation
    # points scattered over the flanks - it is called the Astral Whale.
    if belly:
        mid = 1.0 - abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
        return mix(mix(DEEP, CYAN, 0.35), ICE, mid * 0.5)
    base = mix(VOID, ROYAL, 0.3 + n * 0.5)
    if top:
        base = mix(base, VIOLET, 0.2 if fy % 5 < 2 else 0.04)
    if face in ("east", "west"):
        star = fbm(fx * 4.2, fy * 4.2, 16, seed + 909, octaves=2, base_period=3)
        if star > 0.88:
            return WHITE
        if star > 0.83:
            return mix(base, ICE, 0.6)
        if fy == fh // 2:
            base = mix(base, CYAN, 0.55)
    return edge_light(base, fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_astral_whale", metalness=90, roughness=160,
     emissive_from=LAMP[:3], emissive_gain=1.5, emissive_threshold=0.3)
print("whale texture written")
