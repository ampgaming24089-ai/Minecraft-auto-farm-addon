import sys, json
sys.path.insert(0, "tools")
from artlib import Canvas, hex_rgba, mix, shade, fbm
from mobpaint import paint, edge_light
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0B0711")
DEEP    = hex_rgba("#1A0830")
ROYAL   = hex_rgba("#300D4D")
ORCHID  = hex_rgba("#A640FF")
MAGENTA = hex_rgba("#FF3DFF")
WHITE   = hex_rgba("#FFFFFF")
BONE    = hex_rgba("#B7A9C4")   # ashen, not ivory: bright white teeth on a
                               # black spider read as a pasted-on decal

geo = json.load(open("RP/models/entity/end_spider.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def carapace(fx, fy, fw, fh, seed):
    """Hard shell with a fine pitted grain and a lit ridge along the top."""
    n = fbm(fx * 2.8, fy * 2.8, 16, seed, octaves=3, base_period=3)
    base = mix(VOID, ROYAL, 0.2 + n * 0.45)
    if n > 0.80:
        return shade(base, -0.3)                 # pit
    if fy == 0:
        return shade(base, 0.24)
    return base


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff
    if bone.startswith("eye_"):
        # Eight lit beads. They are the single most recognisable thing about a
        # spider, so they are full brightness with a dark rim.
        r = max(abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0),
                abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0))
        return shade(VOID, -0.3) if r > 0.7 else mix(MAGENTA, WHITE, 0.55)
    if bone.startswith("fang") or "_tooth_" in bone:
        return mix(BONE, ROYAL, 0.25 + fy / max(1.0, fh - 1.0) * 0.6)
    if bone.endswith("_maw"):
        return mix(hex_rgba("#0A0308"), MAGENTA, 0.25)
    if bone.startswith("stud"):
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(ORCHID, MAGENTA, 0.4), WHITE, max(0.0, 0.55 - t * 0.6))
    if bone.startswith("spinneret"):
        # Dark nozzle, lit only down the bore.
        if 0 < fx < fw - 1 and 0 < fy < fh - 1:
            return mix(ORCHID, WHITE, 0.45)
        return shade(VOID, -0.25)
    if bone.startswith("bristle"):
        return mix(VOID, ORCHID, 0.3 + (1.0 - fy / max(1.0, fh - 1.0)) * 0.4)
    if bone.startswith("shell"):
        base = carapace(fx, fy, fw, fh, seed)
        if fy == 0:
            return mix(base, ORCHID, 0.45)
        return edge_light(base, fx, fy, fw, fh)
    if bone == "abdomen":
        base = carapace(fx, fy, fw, fh, seed)
        # An hourglass marking, because a spider needs a warning on its back -
        # and on the rear plate, which is the face anything chasing it sees.
        if face in ("up", "south"):
            t = abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
            waist = abs(fy - (fh - 1) / 2.0) / max(1.0, (fh - 1) / 2.0)
            if t < 0.34 + waist * 0.4:
                return mix(base, MAGENTA, 0.55 - waist * 0.2)
        return edge_light(base, fx, fy, fw, fh)
    if bone.startswith("leg"):
        base = carapace(fx, fy, fw, fh, seed)
        # Joint banding, so eight identical limbs still have articulation.
        if fy % 5 == 0:
            return mix(base, ORCHID, 0.4)
        return base
    return edge_light(carapace(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_end_spider", roughness=182,
     emissive_from=MAGENTA[:3], emissive_gain=1.7, emissive_threshold=0.3)
print("spider texture written")
