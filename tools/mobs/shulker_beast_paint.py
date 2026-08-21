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
WHITE   = hex_rgba("#FFFFFF")
BONE    = hex_rgba("#F2E9D8")

geo = json.load(open("RP/models/entity/shulker_beast.geo.json"))["minecraft:geometry"][0]
c = Canvas(256, 256)


def hide(fx, fy, fw, fh, seed):
    n = fbm(fx * 2.1, fy * 2.1, 16, seed, octaves=3, base_period=4)
    return mix(VOID, ROYAL, 0.2 + n * 0.5)


def painter(bone, face, fx, fy, fw, fh):
    seed = hash(bone) & 0xffff

    if "_tooth_" in bone:
        # The teeth are the whole point of this animal, so they are bone
        # white with a shadowed root rather than a flat block of colour.
        t = fy / max(1.0, fh - 1.0)
        return mix(BONE, ROYAL, t * 0.55)

    if bone.endswith("_maw"):
        t = 1.0 - fy / max(1.0, fh - 1.0)
        return mix(hex_rgba("#0A0308"), MAGENTA, t * 0.5)

    if "_eye_" in bone:
        if fy in (0, fh - 1) or fx in (0, fw - 1):
            return shade(VOID, -0.35)
        return mix(MAGENTA, WHITE, 0.5)

    if "_w" in bone and bone.startswith("wing"):
        n = fbm(fx * 1.4, fy * 1.4, 16, seed, octaves=3, base_period=6)
        base = mix(ROYAL, VIOLET, 0.25 + n * 0.4)
        if face == "down":
            base = mix(base, MAGENTA, 0.3)
        if int(fy) % 5 == 0:
            base = mix(base, ORCHID, 0.5)
        return base

    if bone.startswith("spike") or bone == "barb":
        t = fy / max(1.0, fh - 1.0)
        return mix(mix(ORCHID, MAGENTA, 0.45), WHITE, max(0.0, 0.55 - t * 0.6))

    if bone.startswith("vent") or "_claw" in bone:
        # Vents burn; claws are bone. Both need to be brighter than the hide
        # or they vanish against it.
        if bone.startswith("vent"):
            t = 1.0 - fy / max(1.0, fh - 1.0)
            return mix(MAGENTA, WHITE, t * 0.6)
        return mix(BONE, ROYAL, fy / max(1.0, fh - 1.0) * 0.5)

    if bone.startswith("shell"):
        # Shulker plate: hard, banded, with a lit rim on the leading edge.
        band = shade(mix(ROYAL, ORCHID, 0.3), -0.1 if fy % 3 else 0.18)
        if fy == 0:
            return mix(band, MAGENTA, 0.45)
        return band

    if bone.startswith("horn") or bone.startswith("claw"):
        t = fy / max(1.0, fh - 1.0)
        return mix(BONE, ROYAL, 0.25 + t * 0.5)

    return edge_light(hide(fx, fy, fw, fh, seed), fx, fy, fw, fh)


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_shulker_beast", roughness=190,
     emissive_from=MAGENTA[:3], emissive_gain=1.6, emissive_threshold=0.3)
print("shulker beast texture written")
