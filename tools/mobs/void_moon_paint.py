import sys, json, math
sys.path.insert(0, "tools")
from artlib import Canvas, TRANSPARENT, hex_rgba, mix, shade, fbm
from mobpaint import paint
from gen_art import emit, ENTITY

VOID    = hex_rgba("#0A0616")
CRUST   = hex_rgba("#3C1C63")
CRUST_HI= hex_rgba("#6B39A0")
SEA     = hex_rgba("#1B0C33")
GLOW    = hex_rgba("#C455FF")
HOT     = hex_rgba("#FF7BEE")
RIM     = hex_rgba("#E6A8FF")

geo = json.load(open("RP/models/entity/void_moon.geo.json"))["minecraft:geometry"][0]
c = Canvas(128, 128)

# The face the player sees. Every other face of the plate is transparent, so
# the plate is invisible edge-on and from behind.
FRONT = "north"


def painter(bone, face, fx, fy, fw, fh):
    if face != FRONT:
        return TRANSPARENT

    # Position on the disc, -1..1 in both axes.
    nx = (fx - (fw - 1) / 2.0) / ((fw - 1) / 2.0)
    ny = (fy - (fh - 1) / 2.0) / ((fh - 1) / 2.0)
    r = math.hypot(nx, ny)

    if r > 1.0:
        return TRANSPARENT
    if r > 0.90:
        # Atmosphere. Alpha-test is binary, so the falloff is dithered - at the
        # distance this thing is held that reads as a haze rather than as dots.
        t = (r - 0.90) / 0.10
        keep = fbm(fx * 1.0, fy * 1.0, 128, 991, octaves=3, base_period=16)
        if keep < t * 1.15:
            return TRANSPARENT
        return mix(RIM, HOT, t)

    # A sphere, not a disc: the surface is shaded by how far round it is, and
    # the terminator runs down the left because that is where the nebula is
    # brightest in the sky texture.
    z = math.sqrt(max(0.0, 1.0 - r * r))
    lit = max(0.0, (-nx * 0.62 + ny * 0.24 + z * 0.74))

    # Continents and seas, on a sphere-projected coordinate so they wrap round
    # the limb instead of being stamped flat on a circle.
    u = nx / max(0.35, z + 0.35)
    v = ny / max(0.35, z + 0.35)
    land = fbm((u + 2.0) * 24, (v + 2.0) * 24, 128, 992, octaves=4, base_period=5)
    grain = fbm(fx * 1.0, fy * 1.0, 128, 993, octaves=4, base_period=9)

    if land > 0.54:
        base = mix(CRUST, CRUST_HI, (land - 0.54) / 0.46)
    else:
        base = mix(SEA, CRUST, land / 0.54 * 0.5)
    base = mix(base, shade(base, -0.3), grain * 0.3)
    # Veins of the same light that is in the sky behind it, so the planet
    # belongs to this dimension rather than being a grey rock tinted purple.
    vein = fbm((u + 9.0) * 30, (v + 9.0) * 30, 128, 995, octaves=3, base_period=6)
    if vein > 0.78:
        base = mix(base, GLOW, (vein - 0.78) / 0.22 * 0.7)

    # Craters: dark floors with a lit rim on the sunward side.
    crater = fbm((u + 5.0) * 46, (v + 5.0) * 46, 128, 994, octaves=2, base_period=4)
    if crater > 0.80:
        base = shade(base, -0.35)
    elif crater > 0.74:
        base = mix(base, CRUST_HI, 0.4)

    surface = mix(shade(base, -0.5), mix(base, CRUST_HI, 0.18),
                  0.3 + lit * 0.7)

    # The night side is not black - it is lit by the nebula behind it, which is
    # what stops the planet reading as a hole cut in the sky.
    if lit < 0.24:
        surface = mix(surface, mix(GLOW, VOID, 0.55), (0.24 - lit) / 0.24 * 0.45)
    # A thin bright edge all the way round, from the atmosphere.
    if r > 0.86:
        surface = mix(surface, RIM, (r - 0.86) / 0.04 * 0.45)
    return surface


paint(c, geo, painter)
emit(c, ENTITY, "voidbound_void_moon", roughness=250,
     emissive_from=GLOW[:3], emissive_gain=0.9, emissive_threshold=0.55)
print("void moon texture written")
