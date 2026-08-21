import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0714")
DEEP    = hex_rgba("#1D0A33")
ROYAL   = hex_rgba("#3C1263")
PLUM    = hex_rgba("#5B2088")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
CYAN    = hex_rgba("#5BE9FF")
WHITE   = hex_rgba("#FFFFFF")
ASH     = hex_rgba("#B7A9C4")

geo = json.load(open("RP/models/entity/end_crab.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def shell(fx, fy, fw, fh, seed, lift=0.0):
    """Wet chitin: a coarse pebbled grain, dark in the pits, with a hard
    highlight along the top edge where the shell curves away."""
    n = fbm(fx * 2.4, fy * 2.4, 16, seed, octaves=3, base_period=4)
    base = mix(DEEP, ROYAL, 0.15 + n * 0.6 + lift)
    if n > 0.82:
        return shade(base, -0.35)                # a pit
    if n < 0.16:
        return mix(base, PLUM, 0.5)              # a raised pebble
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    t = fy / max(1.0, fh - 1.0)

    if bone.startswith("crystal"):
        # Growths lit from within, brightest at the point.
        heat = max(0.0, 1.0 - t * 1.5)
        return mix(mix(ROYAL, ORCHID, 0.55), mix(CYAN, ORCHID, 0.35),
                   0.15 + heat * 0.7)
    if bone.startswith("eyeball"):
        if fy == 0 or fx == 0:
            return shade(VOID, -0.4)
        if fy == 1 and fx == 1:
            return WHITE
        return mix(MAGENTA, CYAN, 0.25)
    if bone.startswith("stalk"):
        return mix(DEEP, PLUM, 0.3 + (1.0 - t) * 0.35)
    if "_tooth_" in bone or bone.startswith("serr"):
        return mix(ASH, ROYAL, 0.25 + t * 0.5)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0A0308"), MAGENTA, 0.22)
    if "_eye_" in bone:
        return shade(VOID, -0.35) if (fy == 0 or fx == 0) else mix(MAGENTA, WHITE, 0.4)
    if bone.startswith(("claw", "nip")):
        # The business end: paler, scuffed, with a bright biting edge.
        base = shell(fx, fy, fw, fh, seed, lift=0.16)
        if fy == fh - 1 and bone.startswith("claw"):
            return mix(base, ASH, 0.55)
        if fy == 0 and bone.startswith("nip"):
            return mix(base, ASH, 0.55)
        return edge_light(base, fx, fy, fw, fh)
    if bone.startswith("leg"):
        base = shell(fx, fy, fw, fh, seed)
        if fy % 5 == 0:                          # joint banding
            return mix(base, ORCHID, 0.35)
        return base
    if bone.startswith("dome") or bone == "shell":
        base = shell(fx, fy, fw, fh, seed, lift=0.06)
        # Fine veins of the same crystal running through the carapace.
        vein = fbm(fx * 3.2, fy * 3.2, 16, seed + 313, octaves=2, base_period=6)
        if vein > 0.86:
            return mix(base, mix(CYAN, ORCHID, 0.5), (vein - 0.86) / 0.14)
        return edge_light(base, fx, fy, fw, fh)

    return edge_light(shell(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_end_crab", roughness=150,
     emissive_from=CYAN[:3], emissive_gain=1.6, emissive_threshold=0.32)
print("end crab texture written")
