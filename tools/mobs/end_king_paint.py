import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0711")
DEEP    = hex_rgba("#1A0830")
ROYAL   = hex_rgba("#300D4D")
VIOLET  = hex_rgba("#6B1FFF")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
CYAN    = hex_rgba("#00E6FF")
WHITE   = hex_rgba("#FFFFFF")
GOLD    = hex_rgba("#E8C766")
GOLD_HI = hex_rgba("#FFF0B4")
GOLD_LO = hex_rgba("#7A5C1E")
EMBER   = hex_rgba("#FF7A2E")

geo = json.load(open("RP/models/entity/end_king.geo.json"))["minecraft:geometry"][0]
c = Canvas(512, 512)


def plate(fx, fy, fw, fh, seed, base, light, trim=True):
    """Worked plate: a bevelled edge all the way round, a lit top, hammer
    marks in the field. Armour that has no rim reads as paint on skin."""
    n = fbm(fx * 2.3, fy * 2.3, 16, seed, octaves=2, base_period=4)
    tone = mix(base, light, 0.12 + n * 0.28)
    if trim and (fx == 0 or fx == fw - 1 or fy == fh - 1):
        return shade(tone, -0.34)
    if trim and fy == 0:
        return shade(tone, 0.26)
    if n > 0.76:
        return shade(tone, 0.14)
    return tone


def gilt(fx, fy, fw, fh, seed):
    n = fbm(fx * 2.6, fy * 2.6, 16, seed, octaves=2, base_period=3)
    if fy == 0:
        return GOLD_HI
    if fy == fh - 1:
        return GOLD_LO
    return mix(GOLD, GOLD_LO, 0.3 + n * 0.45)


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    radial = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                 abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))

    if bone.startswith("crown") or bone == "guard" or bone.startswith("cheek"):
        return gilt(fx, fy, fw, fh, seed)

    if bone == "core":
        # The gem in the breastplate: gold bezel, white-hot centre.
        if radial > 0.72:
            return gilt(fx, fy, fw, fh, seed)
        return mix(mix(MAGENTA, ORCHID, radial), WHITE, max(0.0, 0.7 - radial))

    if bone.startswith("blade"):
        # A blade needs bright edges and a dark spine or it is a plank. The
        # fuller runs hot down the middle, which is where the King's power
        # reads from - the blade is lit from inside, not reflecting.
        if face in ("east", "west"):
            return mix(WHITE, EMBER, 0.3)          # the cutting edge
        if abs(fx - (fw - 1) / 2.0) < 1.0:
            return mix(EMBER, WHITE, 0.45)         # the fuller
        return mix(mix(DEEP, ROYAL, 0.4), ORCHID, 0.2)

    if bone == "pommel":
        return gilt(fx, fy, fw, fh, seed)

    if bone == "grip":
        return mix(VOID, ROYAL, 0.3) if fy % 2 else shade(VOID, -0.2)

    if bone.startswith("cape"):
        # Cloth, not plate: no rim, a gold hem, and folds down the length.
        if fy >= fh - 2:
            return gilt(fx, fy, fw, fh, seed)
        fold = 1.0 if (fx + fy // 3) % 5 == 0 else 0.0
        # Brighter than the armour, or a black cape on black plate is nothing.
        return mix(mix(VIOLET, ORCHID, 0.35), ROYAL, fold * 0.55)

    if bone.startswith("tasset"):
        base = plate(fx, fy, fw, fh, seed, VOID, ROYAL)
        return mix(base, GOLD, 0.5) if fy == fh - 1 else base

    if bone.startswith("pauldron") or bone.startswith("cuirass"):
        base = plate(fx, fy, fw, fh, seed, VOID, VIOLET)
        # Gold banding along the leading edge of every major plate.
        if fy in (0, 1):
            return mix(base, gilt(fx, fy, fw, fh, seed), 0.65)
        return base

    if bone == "helm":
        base = plate(fx, fy, fw, fh, seed, VOID, VIOLET)
        if face == "north" and 2 <= fy <= 4 and 2 <= fx <= fw - 3:
            return shade(VOID, -0.4)            # the visor slot
        return base

    if bone.endswith("_maw"):
        return shade(VOID, -0.35)

    if "_tooth_" in bone:
        return WHITE if fy == 0 else mix(WHITE, CYAN, 0.35)

    if bone.startswith("head"):
        # Under the helm it is not flesh - it is the same void the endermen
        # are made of, which is what the crown is sitting on. The eyes go on
        # the front rather than in the side sockets the muzzle builds, because
        # the cheek guards cover those completely on a helmeted head.
        if bone == "head" and face == "north" and fy in (3, 4):
            if fx in (2, 3, fw - 4, fw - 3):
                return WHITE if fy == 3 else mix(MAGENTA, WHITE, 0.5)
        if "_eye_" in bone:
            return shade(VOID, -0.4)
        return mix(VOID, DEEP, 0.3 + fbm(fx * 2.0, fy * 2.0, 16, seed,
                                         octaves=2, base_period=4) * 0.4)

    if bone.startswith("vambrace") or bone.startswith("leg") or bone.startswith("arm"):
        return plate(fx, fy, fw, fh, seed, VOID, ROYAL)

    return edge_light(plate(fx, fy, fw, fh, seed, VOID, ROYAL, trim=False),
                      fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_end_king", metalness=140, roughness=110,
     emissive_from=MAGENTA[:3], emissive_gain=1.6, emissive_threshold=0.3)
print("end king texture written")
