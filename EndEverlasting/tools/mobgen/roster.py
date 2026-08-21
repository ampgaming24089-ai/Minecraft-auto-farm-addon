"""
The twenty Eternal End mobs: shape, palette, stats and behaviour.

One entry per mob in `specs/mobs.json`, in the same order and under the same
identifiers. Each entry owns its geometry - built out of the bone/cube helpers
in `geom.py` - the materials that geometry is painted in, the numbers that go
into the behaviour pack, and a short description of how it moves so the
animation writer can put a gait on it without a second file per mob.

Colours are sampled from the design sheets in `design/references/`. The whole
roster shares one End palette so twenty separate creatures still read as one
pack: obsidian and deep purple bodies, violet and magenta emissive growths, and
one cool accent per creature to tell it apart from its neighbours.
"""

from __future__ import annotations

from geom import Model
from paint import Mat

# ---------------------------------------------------------------------------
# The shared palette.
# ---------------------------------------------------------------------------

VOID = "#241A38"          # the darkest body tone, near-black with a violet cast
OBSIDIAN = "#282334"      # neutral black rock
DEEP = "#2A1140"          # deep purple body
PURPUR = "#5A2A6B"        # purpur-block purple
DUSK = "#3B2352"          # mid purple, for panels and plating
VIOLET = "#B04CFF"        # the pack's main glow
MAGENTA = "#F05CF0"       # hotter glow, for bosses and cores
CYAN = "#3FE8F5"          # cool accent
ICE = "#9FE8FF"           # pale cool accent
GOLD = "#E8A020"          # the End King's regalia
BONE = "#E6DCC4"          # pale horn and bone
TAN = "#CDAE8C"           # the Chorus Cow's markings
EMBER = "#FF7A2A"         # the Ender Bird's warm flash


class Mob:
    """One roster entry."""

    def __init__(self, ident, name, category, model, gait, stats, spawn=None,
                 loot=None, egg=("#2A1140", "#B04CFF"), summary=""):
        self.id = ident
        self.name = name
        self.category = category
        self.model = model
        self.gait = gait
        self.stats = stats
        self.spawn = spawn
        self.loot = loot or []
        self.egg = egg
        self.summary = summary


# ---------------------------------------------------------------------------
# Shape helpers shared by more than one mob.
# ---------------------------------------------------------------------------

def _quadruped_legs(model, hide, *, top, length, thickness, spread_x, front_z,
                    back_z, glow=None):
    """Four legs hung off `body`, named so one gait covers every quadruped."""
    half = thickness / 2
    for name, sx, sz in (
        ("leg_front_left", -spread_x, front_z),
        ("leg_front_right", spread_x, front_z),
        ("leg_back_left", -spread_x, back_z),
        ("leg_back_right", spread_x, back_z),
    ):
        bone = model.bone(name, [sx, top, sz], parent="body")
        bone.cube([sx - half, top - length, sz - half], [thickness, length, thickness],
                  Mat(hide, glow=glow, pattern="fur", density=0.1))


# ---------------------------------------------------------------------------
# 01 - Void Dragon (boss)
# ---------------------------------------------------------------------------

def _void_dragon():
    m = Model("void_dragon", 7.0, 5.0, (0, 2.4, 0))
    hide = Mat(VOID, glow=VIOLET, pattern="scales", accent=DEEP, density=0.2)
    plate = Mat(DEEP, glow=MAGENTA, pattern="crystals", accent=PURPUR, density=0.22)
    wing = Mat(DEEP, glow=VIOLET, pattern="membrane", accent=PURPUR, density=0.3)

    body = m.bone("body", [0, 34, 0])
    body.cube([-9, 26, -14], [18, 16, 28], hide)
    body.cube([-7, 41, -10], [14, 3, 20], plate)          # dorsal ridge

    # Neck and skull carried well forward and up, so the profile is a dragon
    # rather than a lizard: the head has to clear the shoulders to read at all.
    neck = m.bone("neck", [0, 40, -14], parent="body")
    neck.cube([-5, 38, -25], [10, 11, 12], hide)
    neck.cube([-3, 48, -22], [6, 4, 10], plate)

    head = m.bone("head", [0, 44, -25], parent="neck")
    head.cube([-6, 40, -38], [12, 11, 14],
              Mat(VOID, glow=VIOLET, pattern="scales", accent=DEEP,
                  eyes=MAGENTA, density=0.18))
    jaw = m.bone("jaw", [0, 40, -34], parent="head")
    jaw.cube([-5, 35, -39], [10, 5, 14], Mat(OBSIDIAN, glow=MAGENTA,
                                             pattern="veins", density=0.22))
    for side, sign in (("left", -1), ("right", 1)):
        horn = m.bone(f"horn_{side}", [sign * 5, 51, -28], parent="head")
        horn.cube([sign * 5 - 2, 50, -30], [4, 12, 5], plate)

    # Wings. Stepped rather than rotated: each segment sits higher and further
    # out than the last, which gives the swept profile of a folded wing without
    # depending on how a given Bedrock build resolves a bone's rest rotation.
    for side, sign in (("left", -1), ("right", 1)):
        wing_bone = m.bone(f"wing_{side}", [sign * 9, 44, -6], parent="body")
        wing_bone.cube([min(sign * 9, sign * 26), 44, -9], [17, 5, 7], plate)
        wing_bone.cube([min(sign * 11, sign * 26), 30, -7], [15, 15, 3], wing)
        wing_bone.cube([min(sign * 11, sign * 26), 32, 2], [15, 13, 3], wing)
        tip = m.bone(f"wingtip_{side}", [sign * 26, 48, -6], parent=f"wing_{side}")
        tip.cube([min(sign * 26, sign * 45), 48, -10], [19, 4, 6], plate)
        tip.cube([min(sign * 27, sign * 45), 33, -8], [18, 16, 3], wing)
        tip.cube([min(sign * 27, sign * 43), 30, 2], [16, 19, 3], wing)

    _quadruped_legs(m, VOID, top=27, length=19, thickness=7, spread_x=7,
                    front_z=-9, back_z=8, glow=VIOLET)

    tail = m.bone("tail", [0, 34, 14], parent="body")
    tail.cube([-6, 29, 14], [12, 11, 18], hide)
    tail2 = m.bone("tail2", [0, 34, 32], parent="tail")
    tail2.cube([-4, 30, 32], [8, 8, 18], hide)
    tail3 = m.bone("tail3", [0, 34, 50], parent="tail2")
    tail3.cube([-2, 31, 50], [4, 6, 16], plate)
    return m


# ---------------------------------------------------------------------------
# 02 - Ender Overlord (boss)
# ---------------------------------------------------------------------------

def _ender_overlord():
    m = Model("ender_overlord", 6.0, 6.0, (0, 2.6, 0))
    shell = Mat(VOID, glow=VIOLET, pattern="veins", accent=DUSK, density=0.24)
    eye = Mat(DEEP, glow=MAGENTA, pattern="core", accent=PURPUR, density=0.5)
    limb = Mat(DEEP, glow=VIOLET, pattern="crystals", accent=PURPUR, density=0.26)

    body = m.bone("body", [0, 40, 0])
    body.cube([-11, 32, -11], [22, 20, 22], shell)
    body.cube([-13, 36, -13], [26, 8, 26], shell)          # mantle
    body.cube([-7, 34, -14], [14, 14, 4], eye)             # the great eye

    crown = m.bone("crown", [0, 52, 0], parent="body")
    for index, (ox, oz) in enumerate(((-9, -9), (5, -9), (-9, 5), (5, 5))):
        crown.cube([ox, 52, oz], [4, 11, 4], limb)

    # Six tentacles, named so the gait can wave them out of phase.
    positions = ((-9, -6), (0, -10), (9, -6), (-9, 6), (0, 10), (9, 6))
    for index, (ox, oz) in enumerate(positions):
        upper = m.bone(f"tentacle_{index}", [ox, 32, oz], parent="body")
        upper.cube([ox - 2, 20, oz - 2], [5, 13, 5], limb)
        lower = m.bone(f"tentacle_{index}_tip", [ox, 20, oz],
                       parent=f"tentacle_{index}")
        lower.cube([ox - 2, 8, oz - 2], [4, 13, 4], limb)
    return m


# ---------------------------------------------------------------------------
# 03 - The End King (boss)
# ---------------------------------------------------------------------------

def _end_king():
    m = Model("end_king", 4.0, 6.0, (0, 2.6, 0))
    armour = Mat(OBSIDIAN, glow=VIOLET, pattern="metal", accent=DUSK, density=0.14,
                 plate=VOID)
    regalia = Mat("#4A3208", glow=GOLD, pattern="metal", accent=GOLD, density=0.5)
    cape = Mat(DEEP, glow=MAGENTA, pattern="cloth", accent=PURPUR, density=0.16)

    body = m.bone("body", [0, 42, 0])
    body.cube([-10, 34, -5], [20, 26, 11], armour)
    body.cube([-12, 54, -6], [24, 7, 13], armour)          # pauldrons

    head = m.bone("head", [0, 60, 0], parent="body")
    head.cube([-6, 60, -6], [12, 12, 12],
              Mat(VOID, glow=MAGENTA, pattern="veins", accent=DEEP,
                  eyes=MAGENTA, density=0.2))
    crown = m.bone("crown", [0, 72, 0], parent="head")
    crown.cube([-7, 72, -7], [14, 4, 14], regalia)
    for ox, oz in ((-6, -6), (2, -6), (-6, 2), (2, 2), (-2, -7), (-2, 5)):
        crown.cube([ox, 76, oz], [4, 7, 4], regalia)

    body.cube([-5, 44, -7], [10, 9, 3], regalia)           # breastplate sigil

    cape_bone = m.bone("cape", [0, 60, 5], parent="body")
    cape_bone.cube([-9, 26, 5], [18, 35, 3], cape)

    for side, sign in (("left", -1), ("right", 1)):
        arm = m.bone(f"arm_{side}", [sign * 12, 56, 0], parent="body")
        arm.cube([sign * 12 - 3, 36, -3], [7, 21, 7], armour)
    blade = m.bone("blade", [-12, 38, 0], parent="arm_left")
    blade.cube([-16, 4, -3], [5, 36, 6],
               Mat(DEEP, glow=MAGENTA, pattern="flame", accent=VIOLET, density=0.6))

    for side, sign in (("left", -1), ("right", 1)):
        leg = m.bone(f"leg_{side}", [sign * 5, 34, 0], parent="body")
        leg.cube([sign * 5 - 4, 0, -4], [9, 35, 9], armour)
    return m


# ---------------------------------------------------------------------------
# 04 - Void Stalker
# ---------------------------------------------------------------------------

def _void_stalker():
    m = Model("void_stalker", 3.0, 2.5, (0, 1.0, 0))
    hide = Mat(VOID, glow=VIOLET, pattern="fur", accent=DEEP, density=0.14)
    spine = Mat(DEEP, glow=VIOLET, pattern="crystals", accent=PURPUR, density=0.4)

    body = m.bone("body", [0, 18, 0])
    body.cube([-5, 13, -10], [10, 10, 21], hide)
    body.cube([-2, 22, -6], [4, 5, 14], spine)

    head = m.bone("head", [0, 20, -10], parent="body")
    head.cube([-4, 15, -18], [8, 8, 9],
              Mat(VOID, glow=VIOLET, pattern="fur", accent=DEEP, eyes=MAGENTA,
                  density=0.12))
    jaw = m.bone("jaw", [0, 16, -15], parent="head")
    jaw.cube([-3, 12, -19], [6, 4, 8], Mat(OBSIDIAN, glow=MAGENTA, pattern="veins"))
    for sign in (-1, 1):
        head.cube([sign * 4 - 1, 22, -15], [3, 6, 3], spine)

    _quadruped_legs(m, VOID, top=14, length=14, thickness=4, spread_x=4,
                    front_z=-7, back_z=7, glow=VIOLET)

    tail = m.bone("tail", [0, 18, 11], parent="body")
    tail.cube([-2, 16, 11], [4, 4, 14], spine)
    return m


# ---------------------------------------------------------------------------
# 05 - Endermite Hive
# ---------------------------------------------------------------------------

def _endermite_hive():
    m = Model("endermite_hive", 2.4, 2.0, (0, 0.8, 0))
    crust = Mat("#22102E", glow=MAGENTA, pattern="crystals", accent=PURPUR,
                density=0.34)
    mite = Mat(VOID, glow=MAGENTA, pattern="dither", accent=DEEP, eyes=MAGENTA,
               density=0.2)

    body = m.bone("body", [0, 8, 0])
    body.cube([-9, 0, -9], [18, 10, 18], crust)
    body.cube([-6, 10, -6], [12, 8, 12], crust)
    body.cube([-3, 18, -3], [6, 6, 6], crust)

    # Mites breaking out of the crust: each one is its own bone so the idle can
    # have them squirm independently, which is what sells it as a nest.
    for index, (ox, oy, oz, w) in enumerate((
        (-11, 4, -2, 5), (7, 5, -4, 5), (-4, 11, -9, 4),
        (2, 12, 7, 4), (-9, 3, 6, 4),
    )):
        bone = m.bone(f"mite_{index}", [ox + w / 2, oy + 2, oz + w / 2], parent="body")
        bone.cube([ox, oy, oz], [w, w, w + 2], mite)
    return m


# ---------------------------------------------------------------------------
# 06 - Purpur Golem
# ---------------------------------------------------------------------------

def _purpur_golem():
    m = Model("purpur_golem", 3.0, 4.0, (0, 1.6, 0))
    rock = Mat(PURPUR, glow=VIOLET, pattern="stone", accent="#7A4090", density=0.12,
               plate="#3E1C4C")
    core = Mat(DEEP, glow=MAGENTA, pattern="core", accent=VIOLET, density=0.6)

    body = m.bone("body", [0, 30, 0])
    body.cube([-9, 22, -6], [18, 22, 12], rock)
    body.cube([-4, 28, -8], [8, 8, 3], core)

    head = m.bone("head", [0, 44, 0], parent="body")
    head.cube([-5, 44, -5], [10, 10, 10],
              Mat(PURPUR, glow=VIOLET, pattern="stone", accent="#7A4090",
                  eyes=VIOLET, density=0.12))

    for side, sign in (("left", -1), ("right", 1)):
        arm = m.bone(f"arm_{side}", [sign * 11, 42, 0], parent="body")
        arm.cube([sign * 11 - 4, 20, -4], [9, 23, 9], rock)
        fist = m.bone(f"fist_{side}", [sign * 11, 20, 0], parent=f"arm_{side}")
        fist.cube([sign * 11 - 5, 12, -5], [11, 9, 11], rock)

    for side, sign in (("left", -1), ("right", 1)):
        leg = m.bone(f"leg_{side}", [sign * 5, 22, 0], parent="body")
        leg.cube([sign * 5 - 4, 0, -4], [9, 23, 9], rock)
    return m


# ---------------------------------------------------------------------------
# 07 - Shulker Beast
# ---------------------------------------------------------------------------

def _shulker_beast():
    m = Model("shulker_beast", 3.5, 3.0, (0, 1.4, 0))
    shell = Mat("#2E1440", glow=VIOLET, pattern="crystals", accent=PURPUR,
                density=0.24, plate=VOID)
    soft = Mat(DEEP, glow=MAGENTA, pattern="dither", accent=PURPUR, density=0.2)
    wing = Mat(DUSK, glow=VIOLET, pattern="membrane", accent=PURPUR, density=0.3)

    body = m.bone("body", [0, 22, 0])
    body.cube([-8, 14, -8], [16, 16, 16], shell)
    lid = m.bone("lid", [0, 30, 0], parent="body")
    lid.cube([-9, 30, -9], [18, 7, 18], shell)

    head = m.bone("head", [0, 22, -8], parent="body")
    head.cube([-4, 18, -14], [8, 8, 7],
              Mat(VOID, glow=MAGENTA, pattern="dither", accent=DEEP, eyes=MAGENTA,
                  density=0.22))

    for side, sign in (("left", -1), ("right", 1)):
        bone = m.bone(f"wing_{side}", [sign * 8, 26, 0], parent="body")
        bone.cube([min(sign * 8, sign * 19), 24, -9], [11, 4, 20], wing)
        bone.cube([min(sign * 19, sign * 31), 27, -6], [12, 3, 15], wing)

    for index, (ox, oz) in enumerate(((-5, -5), (5, -5), (-5, 5), (5, 5))):
        foot = m.bone(f"foot_{index}", [ox, 14, oz], parent="body")
        foot.cube([ox - 2, 4, oz - 2], [5, 11, 5], soft)
    return m


# ---------------------------------------------------------------------------
# 08 - Void Wisp
# ---------------------------------------------------------------------------

def _void_wisp():
    m = Model("void_wisp", 1.6, 1.8, (0, 0.9, 0))
    flame = Mat("#1B0A3A", glow=VIOLET, pattern="flame", accent="#6B2AD0",
                density=0.6)
    heart = Mat(DEEP, glow=MAGENTA, pattern="core", accent=VIOLET, density=0.7)

    body = m.bone("body", [0, 12, 0])
    body.cube([-4, 8, -4], [8, 9, 8], heart)

    hood = m.bone("hood", [0, 17, 0], parent="body")
    hood.cube([-5, 17, -5], [10, 8, 10],
              Mat("#1B0A3A", glow=VIOLET, pattern="flame", accent="#6B2AD0",
                  eyes=MAGENTA, density=0.6))

    # Three tapering flame tips, each its own bone so the idle can lick.
    for index, (ox, oz, w) in enumerate(((-3, -1, 4), (2, 2, 4), (-1, 3, 3))):
        tip = m.bone(f"flame_{index}", [ox + w / 2, 25, oz + w / 2], parent="hood")
        tip.cube([ox, 25, oz], [w, 8, w], flame)

    for index, (ox, oz) in enumerate(((-5, 0), (4, 0))):
        wisp = m.bone(f"trail_{index}", [ox, 8, oz], parent="body")
        wisp.cube([ox - 1, 0, oz - 2], [3, 9, 4], flame)
    return m


# ---------------------------------------------------------------------------
# 09 - End Spider
# ---------------------------------------------------------------------------

def _end_spider():
    m = Model("end_spider", 3.0, 1.6, (0, 0.6, 0))
    chitin = Mat("#1E1030", glow=VIOLET, pattern="crystals", accent=DUSK,
                 density=0.2)
    leg_mat = Mat(VOID, glow=VIOLET, pattern="dither", accent=DUSK, density=0.14)

    body = m.bone("body", [0, 15, 0])
    body.cube([-6, 10, -2], [12, 10, 14], chitin)          # abdomen
    body.cube([-4, 11, -8], [8, 7, 7], chitin)             # thorax

    head = m.bone("head", [0, 15, -8], parent="body")
    head.cube([-4, 11, -14], [8, 7, 6],
              Mat("#1E1030", glow=MAGENTA, pattern="dither", accent=DUSK,
                  eyes=MAGENTA, density=0.2))

    # Eight legs in four mirrored pairs: a thigh straight out from the hip and
    # a shin dropping from the knee. Built as two static cubes rather than a
    # rotated bone, so the leg lands where it looks like it will on any build,
    # and one bone still owns the whole limb for the walk cycle.
    for index, (oz, reach) in enumerate(((-6, 12), (-1, 15), (3, 15), (7, 12))):
        for side, sign in (("left", -1), ("right", 1)):
            hip = sign * 4
            knee = hip + sign * reach
            bone = m.bone(f"leg_{index}_{side}", [hip, 17, oz], parent="body")
            bone.cube([min(hip, knee), 17, oz - 1], [reach, 3, 3], leg_mat)
            bone.cube([min(knee, knee - sign * 3), 0, oz - 1], [3, 18, 3], leg_mat)
    return m


# ---------------------------------------------------------------------------
# 10 - Corrupted Enderman
# ---------------------------------------------------------------------------

def _corrupted_enderman():
    m = Model("corrupted_enderman", 2.0, 4.0, (0, 1.6, 0))
    skin = Mat(VOID, glow=VIOLET, pattern="veins", accent=DEEP, density=0.26)

    body = m.bone("body", [0, 38, 0])
    body.cube([-4, 26, -3], [8, 22, 6], skin)
    body.cube([-6, 44, -4], [12, 5, 8], skin)              # shoulders

    head = m.bone("head", [0, 49, 0], parent="body")
    head.cube([-4, 49, -4], [8, 8, 8],
              Mat(VOID, glow=MAGENTA, pattern="veins", accent=DEEP, eyes=MAGENTA,
                  mouth=VIOLET, density=0.3))

    for side, sign in (("left", -1), ("right", 1)):
        arm = m.bone(f"arm_{side}", [sign * 5, 46, 0], parent="body")
        arm.cube([sign * 5 - 2, 16, -2], [4, 30, 4], skin)
    for side, sign in (("left", -1), ("right", 1)):
        leg = m.bone(f"leg_{side}", [sign * 2, 26, 0], parent="body")
        leg.cube([sign * 2 - 2, 0, -2], [4, 26, 4], skin)
    return m


# ---------------------------------------------------------------------------
# 11 - Chorus Fiend
# ---------------------------------------------------------------------------

def _chorus_fiend():
    m = Model("chorus_fiend", 3.0, 3.2, (0, 1.4, 0))
    hide = Mat("#241030", glow=VIOLET, pattern="crystals", accent=PURPUR,
               density=0.3)
    growth = Mat(PURPUR, glow=MAGENTA, pattern="crystals", accent="#8A4AA0",
                 density=0.5)

    body = m.bone("body", [0, 30, 0])
    body.cube([-8, 22, -6], [16, 20, 13], hide)
    body.cube([-5, 40, -3], [10, 8, 8], growth)            # chorus bloom

    head = m.bone("head", [0, 34, -6], parent="body")
    head.cube([-5, 28, -14], [10, 9, 9],
              Mat("#241030", glow=MAGENTA, pattern="crystals", accent=PURPUR,
                  eyes=MAGENTA, mouth=VIOLET, density=0.24))

    for side, sign in (("left", -1), ("right", 1)):
        arm = m.bone(f"arm_{side}", [sign * 9, 38, -2], parent="body")
        arm.cube([sign * 9 - 4, 14, -6], [8, 25, 8], hide)
        claw = m.bone(f"claw_{side}", [sign * 9, 14, -2], parent=f"arm_{side}")
        claw.cube([sign * 9 - 4, 6, -7], [8, 9, 9], growth)
    for side, sign in (("left", -1), ("right", 1)):
        leg = m.bone(f"leg_{side}", [sign * 4, 22, 0], parent="body")
        leg.cube([sign * 4 - 4, 0, -4], [8, 23, 9], hide)
    return m


# ---------------------------------------------------------------------------
# 12 - Void Slime
# ---------------------------------------------------------------------------

def _void_slime():
    m = Model("void_slime", 2.0, 2.0, (0, 0.8, 0))
    jelly = Mat("#1A0A34", glow=VIOLET, pattern="dither", accent="#3A1A66",
                density=0.2)

    body = m.bone("body", [0, 8, 0])
    body.cube([-8, 0, -8], [16, 16, 16], jelly)

    face = m.bone("face", [0, 8, -8], parent="body")
    face.cube([-6, 3, -9], [12, 10, 2],
              Mat("#1A0A34", glow=MAGENTA, pattern="dither", accent="#3A1A66",
                  eyes=MAGENTA, mouth=VIOLET, density=0.2))

    core = m.bone("core", [0, 8, 0], parent="body")
    core.cube([-4, 4, -4], [8, 8, 8],
              Mat(DEEP, glow=MAGENTA, pattern="core", accent=VIOLET, density=0.8))
    return m


# ---------------------------------------------------------------------------
# 13 - Teleporter
# ---------------------------------------------------------------------------

def _teleporter():
    m = Model("teleporter", 2.4, 3.2, (0, 1.4, 0))
    robe = Mat("#1E1030", glow=MAGENTA, pattern="cloth", accent=DUSK, density=0.24)
    ring_mat = Mat(DEEP, glow=MAGENTA, pattern="flame", accent=VIOLET, density=0.8)

    body = m.bone("body", [0, 30, 0])
    body.cube([-5, 16, -4], [10, 20, 8], robe)
    body.cube([-7, 10, -5], [14, 8, 10], robe)             # hem

    head = m.bone("head", [0, 36, 0], parent="body")
    head.cube([-4, 36, -4], [8, 9, 8],
              Mat("#1E1030", glow=MAGENTA, pattern="veins", accent=DUSK,
                  eyes=MAGENTA, density=0.3))
    hood = m.bone("hood", [0, 45, 0], parent="head")
    hood.cube([-5, 43, -5], [10, 6, 10], robe)

    for side, sign in (("left", -1), ("right", 1)):
        arm = m.bone(f"arm_{side}", [sign * 6, 34, 0], parent="body")
        arm.cube([sign * 6 - 2, 18, -2], [5, 17, 5], robe)

    # The teleport ring: four arcs orbiting the caster, one bone so the whole
    # ring can spin as a unit.
    ring = m.bone("ring", [0, 26, 0], parent="body")
    for ox, oz, w, d in ((-11, -2, 3, 5), (9, -2, 3, 5), (-2, -11, 5, 3), (-2, 9, 5, 3)):
        ring.cube([ox, 24, oz], [w, 3, d], ring_mat)
    return m


# ---------------------------------------------------------------------------
# 14 - End Crab
# ---------------------------------------------------------------------------

def _end_crab():
    m = Model("end_crab", 2.6, 1.6, (0, 0.6, 0))
    shell = Mat("#2A1038", glow=VIOLET, pattern="crystals", accent=PURPUR,
                density=0.34, plate=VOID)
    limb = Mat("#20102C", glow=VIOLET, pattern="scales", accent=DUSK, density=0.16)

    body = m.bone("body", [0, 9, 0])
    body.cube([-9, 5, -7], [18, 8, 14], shell)
    body.cube([-6, 13, -4], [12, 4, 9], shell)

    head = m.bone("head", [0, 9, -7], parent="body")
    head.cube([-5, 6, -10], [10, 5, 4],
              Mat("#2A1038", glow=MAGENTA, pattern="dither", accent=PURPUR,
                  eyes=MAGENTA, density=0.3))
    for sign in (-1, 1):
        head.cube([sign * 3 - 1, 11, -9], [2, 5, 2],
                  Mat(DEEP, glow=MAGENTA, pattern="core", density=0.9))

    # Claws carried out in front, where a crab holds them, rather than out to
    # the side where they read as sticks glued to the shell.
    for side, sign in (("left", -1), ("right", 1)):
        arm = m.bone(f"claw_{side}", [sign * 8, 8, -6], parent="body")
        arm.cube([min(sign * 8, sign * 14), 6, -8], [6, 5, 5], limb)
        pincer = m.bone(f"pincer_{side}", [sign * 13, 8, -9], parent=f"claw_{side}")
        pincer.cube([min(sign * 9, sign * 18), 3, -17], [9, 9, 10], shell)
        pincer.cube([min(sign * 10, sign * 17), 11, -19], [7, 4, 7], shell)

    for index, oz in enumerate((-3, 1, 5)):
        for side, sign in (("left", -1), ("right", 1)):
            hip = sign * 8
            knee = hip + sign * 7
            leg = m.bone(f"leg_{index}_{side}", [hip, 7, oz], parent="body")
            leg.cube([min(hip, knee), 7, oz - 1], [7, 3, 3], limb)
            leg.cube([min(knee, knee - sign * 3), 0, oz - 1], [3, 8, 3], limb)
    return m


# ---------------------------------------------------------------------------
# 15 - Obsidian Beast
# ---------------------------------------------------------------------------

def _obsidian_beast():
    m = Model("obsidian_beast", 4.0, 3.4, (0, 1.5, 0))
    rock = Mat(OBSIDIAN, glow=VIOLET, pattern="stone", accent="#2E2833", density=0.16,
               plate="#0E0C12")
    crystal = Mat(DEEP, glow=VIOLET, pattern="crystals", accent=PURPUR, density=0.55)

    body = m.bone("body", [0, 28, 0])
    body.cube([-9, 20, -12], [18, 18, 26], rock)
    for ox, oz, h in ((-6, -6, 8), (2, -2, 10), (-4, 6, 7), (3, 10, 6)):
        body.cube([ox, 38, oz], [5, h, 5], crystal)

    head = m.bone("head", [0, 28, -12], parent="body")
    head.cube([-7, 20, -24], [14, 12, 13],
              Mat(OBSIDIAN, glow=VIOLET, pattern="stone", accent="#2E2833",
                  eyes=VIOLET, density=0.16))
    for sign in (-1, 1):
        horn = m.bone(f"horn_{'left' if sign < 0 else 'right'}",
                      [sign * 6, 32, -20], parent="head")
        horn.cube([sign * 7 - 3, 30, -22], [5, 5, 14], crystal)

    _quadruped_legs(m, OBSIDIAN, top=21, length=21, thickness=8, spread_x=6,
                    front_z=-8, back_z=9, glow=VIOLET)

    tail = m.bone("tail", [0, 28, 14], parent="body")
    tail.cube([-3, 24, 14], [6, 6, 12], rock)
    return m


# ---------------------------------------------------------------------------
# 16 - Ender Deer (passive, tameable)
# ---------------------------------------------------------------------------

def _ender_deer():
    m = Model("ender_deer", 2.4, 2.6, (0, 1.1, 0))
    hide = Mat("#141A26", glow=CYAN, pattern="fur", accent="#25303F", density=0.1)
    antler = Mat("#1C2A34", glow=CYAN, pattern="crystals", accent=ICE, density=0.6)

    body = m.bone("body", [0, 24, 0])
    body.cube([-4, 19, -9], [9, 11, 19], hide)

    neck = m.bone("neck", [0, 28, -8], parent="body")
    neck.cube([-3, 27, -13], [6, 10, 7], hide)
    head = m.bone("head", [0, 36, -11], parent="neck")
    head.cube([-3, 33, -18], [6, 6, 8],
              Mat("#141A26", glow=CYAN, pattern="fur", accent="#25303F", eyes=ICE,
                  density=0.1))
    for side, sign in (("left", -1), ("right", 1)):
        rack = m.bone(f"antler_{side}", [sign * 2, 39, -14], parent="head")
        rack.cube([sign * 3 - 1, 39, -15], [3, 11, 3], antler)
        rack.cube([min(sign * 3, sign * 8), 45, -15], [6, 3, 3], antler)
        rack.cube([min(sign * 3, sign * 7), 48, -12], [5, 3, 3], antler)

    _quadruped_legs(m, "#141A26", top=20, length=20, thickness=4, spread_x=3,
                    front_z=-6, back_z=6, glow=CYAN)

    tail = m.bone("tail", [0, 27, 10], parent="body")
    tail.cube([-2, 24, 10], [4, 5, 4], antler)
    return m


# ---------------------------------------------------------------------------
# 17 - Chorus Cow (passive, tameable)
# ---------------------------------------------------------------------------

def _chorus_cow():
    m = Model("chorus_cow", 2.8, 2.4, (0, 1.0, 0))
    hide = Mat("#2A1428", glow=VIOLET, pattern="fur", accent=TAN, density=0.22)
    growth = Mat(PURPUR, glow=MAGENTA, pattern="crystals", accent="#8A4AA0",
                 density=0.55)

    body = m.bone("body", [0, 22, 0])
    body.cube([-6, 14, -10], [13, 13, 21], hide)
    for ox, oz, h in ((-5, -6, 6), (1, -1, 7), (-3, 5, 5), (2, 9, 6)):
        body.cube([ox, 27, oz], [4, h, 4], growth)

    head = m.bone("head", [0, 24, -10], parent="body")
    head.cube([-4, 19, -18], [9, 9, 9],
              Mat("#2A1428", glow=VIOLET, pattern="fur", accent=TAN, eyes=MAGENTA,
                  density=0.24))
    head.cube([-3, 19, -20], [7, 5, 3], Mat(TAN, pattern="dither", accent="#E4CBAA"))
    for sign in (-1, 1):
        head.cube([sign * 5 - 1, 26, -15], [4, 4, 4], growth)   # horns

    _quadruped_legs(m, "#2A1428", top=15, length=15, thickness=5, spread_x=4,
                    front_z=-6, back_z=7, glow=VIOLET)

    tail = m.bone("tail", [0, 25, 11], parent="body")
    tail.cube([-1, 12, 11], [3, 14, 3], hide)
    return m


# ---------------------------------------------------------------------------
# 18 - Void Hog (passive, tameable)
# ---------------------------------------------------------------------------

def _void_hog():
    m = Model("void_hog", 2.2, 1.8, (0, 0.8, 0))
    hide = Mat("#191622", glow=VIOLET, pattern="fur", accent="#2C2634", density=0.14)
    spike = Mat(DEEP, glow=VIOLET, pattern="crystals", accent=PURPUR, density=0.6)
    tusk = Mat(BONE, pattern="dither", accent="#FFF6E0", density=0.2)

    body = m.bone("body", [0, 14, 0])
    body.cube([-6, 8, -9], [12, 12, 19], hide)
    for ox, oz, h in ((-4, -5, 5), (0, 0, 6), (-3, 5, 4)):
        body.cube([ox, 20, oz], [4, h, 4], spike)

    head = m.bone("head", [0, 15, -9], parent="body")
    head.cube([-4, 9, -17], [9, 9, 9],
              Mat("#191622", glow=VIOLET, pattern="fur", accent="#2C2634",
                  eyes=MAGENTA, density=0.14))
    head.cube([-3, 9, -19], [6, 4, 3], Mat("#241E2E", pattern="dither"))
    for sign in (-1, 1):
        head.cube([sign * 4 - 1, 12, -19], [2, 4, 2], tusk)

    _quadruped_legs(m, "#191622", top=9, length=9, thickness=4, spread_x=4,
                    front_z=-6, back_z=6, glow=VIOLET)

    tail = m.bone("tail", [0, 17, 10], parent="body")
    tail.cube([-1, 15, 10], [3, 3, 5], hide)
    return m


# ---------------------------------------------------------------------------
# 19 - Sky Ray (passive, tameable, rideable)
# ---------------------------------------------------------------------------

def _sky_ray():
    m = Model("sky_ray", 5.0, 2.0, (0, 1.0, 0))
    back = Mat("#1A1836", glow=CYAN, pattern="feather", accent="#2E2A5E",
               density=0.24)
    fin = Mat("#221E44", glow=CYAN, pattern="membrane", accent=ICE, density=0.3)
    belly = Mat("#2C2856", glow=VIOLET, pattern="dither", accent="#3E3A72",
                density=0.16)

    body = m.bone("body", [0, 16, 0])
    body.cube([-7, 13, -14], [14, 9, 26], back)
    body.cube([-4, 22, -10], [8, 5, 17], back)             # dorsal keel
    body.cube([-5, 10, -10], [10, 3, 18], belly)

    head = m.bone("head", [0, 17, -14], parent="body")
    head.cube([-5, 14, -21], [10, 7, 8],
              Mat("#1A1836", glow=CYAN, pattern="feather", accent="#2E2A5E",
                  eyes=ICE, density=0.24))

    for side, sign in (("left", -1), ("right", 1)):
        wing = m.bone(f"wing_{side}", [sign * 7, 17, -2], parent="body")
        wing.cube([min(sign * 7, sign * 24), 15, -13], [17, 4, 24], fin)
        tip = m.bone(f"wingtip_{side}", [sign * 24, 18, -2], parent=f"wing_{side}")
        tip.cube([min(sign * 24, sign * 38), 17, -8], [14, 3, 17], fin)
        tip.cube([min(sign * 38, sign * 46), 19, -3], [8, 2, 10], fin)

    tail = m.bone("tail", [0, 17, 12], parent="body")
    tail.cube([-2, 15, 12], [4, 3, 18], back)
    tail2 = m.bone("tail2", [0, 17, 30], parent="tail")
    tail2.cube([-1, 15, 30], [3, 3, 12],
               Mat(DEEP, glow=CYAN, pattern="crystals", accent=ICE, density=0.6))
    return m


# ---------------------------------------------------------------------------
# 20 - Ender Bird (passive, tameable)
# ---------------------------------------------------------------------------

def _ender_bird():
    m = Model("ender_bird", 2.4, 1.8, (0, 0.8, 0))
    plume = Mat("#161435", glow=CYAN, pattern="feather", accent="#2A2668",
                density=0.3)
    flight = Mat("#1E1A48", glow=CYAN, pattern="feather", accent=ICE, density=0.34)
    beak = Mat("#8A3A10", glow=EMBER, pattern="metal", accent=EMBER, density=0.3)

    body = m.bone("body", [0, 12, 0])
    body.cube([-4, 8, -6], [8, 10, 13], plume)

    head = m.bone("head", [0, 17, -4], parent="body")
    head.cube([-3, 17, -9], [7, 7, 7],
              Mat("#161435", glow=CYAN, pattern="feather", accent="#2A2668",
                  eyes=ICE, density=0.3))
    head.cube([-1, 19, -12], [3, 3, 4], beak)
    crest = m.bone("crest", [0, 24, -6], parent="head")
    crest.cube([-1, 24, -8], [3, 6, 5],
               Mat(DEEP, glow=CYAN, pattern="crystals", accent=ICE, density=0.7))

    for side, sign in (("left", -1), ("right", 1)):
        wing = m.bone(f"wing_{side}", [sign * 4, 16, -2], parent="body")
        wing.cube([min(sign * 4, sign * 13), 14, -5], [9, 4, 9], flight)
        wing.cube([min(sign * 13, sign * 22), 15, -1], [9, 3, 9], flight)

    tail = m.bone("tail", [0, 12, 7], parent="body")
    tail.cube([-4, 10, 7], [8, 2, 12], flight)

    for side, sign in (("left", -1), ("right", 1)):
        leg = m.bone(f"leg_{side}", [sign * 2, 8, 0], parent="body")
        leg.cube([sign * 2 - 1, 2, -2], [3, 6, 3],
                 Mat("#241C46", pattern="dither", accent="#372C64"))
        leg.cube([sign * 2 - 1, 0, -4], [3, 2, 5], beak)
    return m


# ---------------------------------------------------------------------------
# Gaits. What moves, and how, so animations can be written once.
# ---------------------------------------------------------------------------

def gait(**kwargs):
    base = dict(
        legs=[],           # [(bone, phase sign)] swung on the walk cycle
        wings=[],          # [(bone, sign)] flapped on z
        head=None,         # bone that looks around on idle
        jaw=None,          # bone that opens on attack
        tail=[],           # bones that sway
        arms=[],           # [(bone, sign)] swung on the walk, thrown on attack
        extra=[],          # bones that drift on idle (tentacles, flames, mites)
        hover=False,       # floats rather than walks
        bob=0.0,           # vertical bob amplitude in model units
        swing=42,          # leg swing, degrees
        flap=34,           # wing flap, degrees
        spin=None,         # bone that rotates continuously on y
        lunge=None,        # bone thrown forward on attack (a blade, a claw)
    )
    base.update(kwargs)
    return base


QUAD_LEGS = [
    ("leg_front_left", 1), ("leg_front_right", -1),
    ("leg_back_left", -1), ("leg_back_right", 1),
]


# ---------------------------------------------------------------------------
# The roster.
# ---------------------------------------------------------------------------

ROSTER = [
    Mob(
        "void_dragon", "Void Dragon", "boss", _void_dragon,
        gait(legs=QUAD_LEGS, wings=[("wing_left", 1), ("wing_right", -1)],
             head="head", jaw="jaw", tail=["tail", "tail2", "tail3"],
             hover=True, bob=1.6, swing=26, flap=26,
             extra=["wingtip_left", "wingtip_right"]),
        dict(health=420, damage=22, speed=0.30, fly_speed=0.62, knockback=1.0,
             xp=500, scale=1.0, width=4.4, height=3.6, ranged=True,
             projectile="eternal_end:void_breath", boss=True, flying=True,
             fire_immune=True, boss_name="Void Dragon"),
        spawn=None,
        loot=[("eternal_end:void_scale", 6, 12), ("minecraft:dragon_breath", 2, 5),
              ("eternal_end:void_heart", 1, 1)],
        egg=("#120A22", "#B04CFF"),
        summary="Final aerial boss. Void breath, wing buffet, and a dive that "
                "cracks the ground under it.",
    ),
    Mob(
        "ender_overlord", "Ender Overlord", "boss", _ender_overlord,
        gait(head=None, hover=True, bob=2.2,
             extra=[f"tentacle_{i}" for i in range(6)]
                   + [f"tentacle_{i}_tip" for i in range(6)] + ["crown"]),
        dict(health=360, damage=18, speed=0.26, fly_speed=0.5, knockback=1.0,
             xp=400, scale=1.0, width=3.2, height=3.6, ranged=True,
             projectile="eternal_end:void_lance", boss=True, flying=True,
             teleports=True, fire_immune=True, boss_name="Ender Overlord"),
        loot=[("eternal_end:void_scale", 4, 9), ("minecraft:ender_pearl", 4, 10),
              ("eternal_end:overlord_eye", 1, 1)],
        egg=("#150B28", "#F05CF0"),
        summary="Cosmic tentacled boss. Fires void lances, blinks away when "
                "cornered, and drags its victims in with its tentacles.",
    ),
    Mob(
        "end_king", "The End King", "boss", _end_king,
        gait(legs=[("leg_left", 1), ("leg_right", -1)],
             arms=[("arm_left", 1), ("arm_right", -1)],
             head="head", tail=["cape"], swing=30, lunge="blade",
             extra=["crown"]),
        dict(health=480, damage=26, speed=0.31, knockback=1.0, xp=600, scale=1.0,
             width=1.8, height=4.6, boss=True, ranged=True,
             projectile="eternal_end:royal_bolt", fire_immune=True,
             boss_name="The End King"),
        loot=[("eternal_end:void_scale", 5, 10), ("minecraft:gold_ingot", 6, 14),
              ("eternal_end:crown_shard", 1, 1)],
        egg=("#1A1418", "#E8A020"),
        summary="Royal humanoid boss. Sweeps with an energy blade, calls royal "
                "bolts, and summons Corrupted Endermen when wounded.",
    ),
    Mob(
        "void_stalker", "Void Stalker", "hostile", _void_stalker,
        gait(legs=QUAD_LEGS, head="head", jaw="jaw", tail=["tail"], swing=48),
        dict(health=34, damage=7, speed=0.36, knockback=0.4, xp=10, width=1.3,
             height=1.5, sprint=True),
        spawn=dict(weight=22, herd=(1, 2), light="dark"),
        loot=[("eternal_end:void_scale", 0, 2), ("minecraft:ender_pearl", 0, 1)],
        summary="Ambush hunter. Fast, low to the ground, and it commits.",
    ),
    Mob(
        "endermite_hive", "Endermite Hive", "hostile", _endermite_hive,
        gait(head=None, bob=0.6, extra=[f"mite_{i}" for i in range(5)]),
        dict(health=40, damage=4, speed=0.2, knockback=0.7, xp=8, width=1.2,
             height=1.5, summons="minecraft:endermite"),
        spawn=dict(weight=12, herd=(1, 1), light="dark"),
        loot=[("minecraft:ender_pearl", 0, 2), ("eternal_end:void_scale", 0, 1)],
        summary="A nest that walks. Releases endermites while it lives.",
    ),
    Mob(
        "purpur_golem", "Purpur Golem", "hostile", _purpur_golem,
        gait(legs=[("leg_left", 1), ("leg_right", -1)],
             arms=[("arm_left", 1), ("arm_right", -1)], head="head", swing=26,
             extra=["fist_left", "fist_right"]),
        dict(health=90, damage=12, speed=0.22, knockback=0.95, xp=16, width=1.5,
             height=2.7, armour=8),
        spawn=dict(weight=10, herd=(1, 1), light="any"),
        loot=[("minecraft:purpur_block", 2, 6), ("eternal_end:void_scale", 1, 3)],
        egg=("#5A2A6B", "#B04CFF"),
        summary="Tank. Slow, heavily armoured, and it does not stop coming.",
    ),
    Mob(
        "shulker_beast", "Shulker Beast", "hostile", _shulker_beast,
        gait(wings=[("wing_left", 1), ("wing_right", -1)], head="head",
             hover=True, bob=1.4, flap=40,
             extra=["lid", "foot_0", "foot_1", "foot_2", "foot_3"]),
        dict(health=52, damage=8, speed=0.24, fly_speed=0.42, knockback=0.6, xp=14,
             width=1.7, height=1.8, flying=True, ranged=True,
             projectile="minecraft:shulker_bullet"),
        spawn=dict(weight=9, herd=(1, 1), light="any"),
        loot=[("minecraft:shulker_shell", 0, 2), ("eternal_end:void_scale", 1, 3)],
        summary="Flying attacker. Opens its shell to fire, closes it to take "
                "the hit.",
    ),
    Mob(
        "void_wisp", "Void Wisp", "hostile", _void_wisp,
        gait(head="hood", hover=True, bob=2.0,
             extra=["flame_0", "flame_1", "flame_2", "trail_0", "trail_1"]),
        dict(health=22, damage=5, speed=0.24, fly_speed=0.5, knockback=0.1, xp=9,
             width=0.8, height=1.4, flying=True, ranged=True,
             projectile="eternal_end:wisp_flame", fire_immune=True),
        spawn=dict(weight=18, herd=(1, 3), light="dark"),
        loot=[("eternal_end:void_ember", 1, 2)],
        egg=("#1B0A3A", "#B04CFF"),
        summary="Floating caster. Drifts in and burns from range.",
    ),
    Mob(
        "end_spider", "End Spider", "hostile", _end_spider,
        gait(legs=[(f"leg_{i}_{side}", 1 if (i + (side == 'right')) % 2 else -1)
                   for i in range(4) for side in ("left", "right")],
             head="head", swing=22),
        dict(health=26, damage=6, speed=0.34, knockback=0.3, xp=9, width=1.4,
             height=0.9, climbs=True),
        spawn=dict(weight=20, herd=(1, 3), light="dark"),
        loot=[("minecraft:string", 0, 2), ("eternal_end:void_scale", 0, 1)],
        summary="Climber. Comes down walls and over ceilings.",
    ),
    Mob(
        "corrupted_enderman", "Corrupted Enderman", "hostile", _corrupted_enderman,
        gait(legs=[("leg_left", 1), ("leg_right", -1)],
             arms=[("arm_left", 1), ("arm_right", -1)], head="head", swing=34),
        dict(health=48, damage=10, speed=0.32, knockback=0.5, xp=12, width=0.7,
             height=3.0, teleports=True),
        spawn=dict(weight=16, herd=(1, 2), light="dark"),
        loot=[("minecraft:ender_pearl", 1, 3), ("eternal_end:void_scale", 0, 2)],
        summary="Teleporting melee. Blinks behind you and hits hard.",
    ),
    Mob(
        "chorus_fiend", "Chorus Fiend", "hostile", _chorus_fiend,
        gait(legs=[("leg_left", 1), ("leg_right", -1)],
             arms=[("arm_left", 1), ("arm_right", -1)], head="head", swing=30,
             extra=["claw_left", "claw_right"]),
        dict(health=64, damage=11, speed=0.3, knockback=0.7, xp=14, width=1.5,
             height=2.6, teleports=True),
        spawn=dict(weight=12, herd=(1, 2), light="any"),
        loot=[("minecraft:chorus_fruit", 1, 4), ("eternal_end:void_scale", 0, 2)],
        summary="Bruiser. Chorus-infused, short-hops toward its target.",
    ),
    Mob(
        "void_slime", "Void Slime", "hostile", _void_slime,
        gait(head="face", bob=0.0, extra=["core"], hop=True),
        dict(health=30, damage=6, speed=0.28, knockback=0.2, xp=8, width=1.2,
             height=1.2, hops=True),
        spawn=dict(weight=18, herd=(2, 4), light="dark"),
        loot=[("minecraft:slime_ball", 1, 3), ("eternal_end:void_ember", 0, 1)],
        summary="Jumper. Bounces at you and keeps bouncing.",
    ),
    Mob(
        "teleporter", "Teleporter", "hostile", _teleporter,
        gait(arms=[("arm_left", 1), ("arm_right", -1)], head="head",
             spin="ring", hover=True, bob=1.0, extra=["hood"]),
        dict(health=36, damage=7, speed=0.3, knockback=0.3, xp=12, width=0.9,
             height=2.2, teleports=True, ranged=True,
             projectile="eternal_end:void_lance"),
        spawn=dict(weight=11, herd=(1, 1), light="dark"),
        loot=[("minecraft:ender_pearl", 1, 3), ("eternal_end:void_ember", 0, 2)],
        summary="Ranged teleport attacker. Never stays where you last saw it.",
    ),
    Mob(
        "end_crab", "End Crab", "hostile", _end_crab,
        gait(legs=[(f"leg_{i}_{side}", 1 if (i + (side == 'right')) % 2 else -1)
                   for i in range(3) for side in ("left", "right")],
             arms=[("claw_left", 1), ("claw_right", -1)], head="head", swing=20,
             extra=["pincer_left", "pincer_right"]),
        dict(health=44, damage=9, speed=0.26, knockback=0.8, xp=11, width=1.6,
             height=1.1, armour=6),
        spawn=dict(weight=14, herd=(1, 3), light="any"),
        loot=[("eternal_end:void_chitin_plate", 1, 3),
              ("eternal_end:void_scale", 0, 2)],
        summary="Armoured melee. Big claws, and a shell that shrugs off arrows.",
    ),
    Mob(
        "obsidian_beast", "Obsidian Beast", "hostile", _obsidian_beast,
        gait(legs=QUAD_LEGS, head="head", tail=["tail"], swing=24),
        dict(health=120, damage=14, speed=0.2, knockback=1.0, xp=20, width=2.4,
             height=2.6, armour=12),
        spawn=dict(weight=7, herd=(1, 1), light="any"),
        loot=[("minecraft:obsidian", 1, 4), ("eternal_end:void_scale", 2, 5)],
        egg=("#1C1720", "#B04CFF"),
        summary="Heavy tank. Slow, enormous, and almost unkillable head-on.",
    ),
    Mob(
        "ender_deer", "Ender Deer", "passive_tame", _ender_deer,
        gait(legs=QUAD_LEGS, head="head", tail=["tail"], swing=44,
             extra=["antler_left", "antler_right", "neck"]),
        dict(health=20, damage=2, speed=0.32, knockback=0.0, xp=3, width=1.0,
             height=1.9, tame=True, tame_item="eternal_end:lumen_feed",
             breed_item="eternal_end:lumen_feed", meat="ender_venison",
             panics=True),
        spawn=dict(weight=16, herd=(2, 4), light="any", passive=True),
        loot=[("eternal_end:raw_ender_venison", 1, 3)],
        egg=("#141A26", "#3FE8F5"),
        summary="Calm until struck. Tame with Lumen Feed; a renewable venison "
                "herd once it settles.",
    ),
    Mob(
        "chorus_cow", "Chorus Cow", "passive_tame", _chorus_cow,
        gait(legs=QUAD_LEGS, head="head", tail=["tail"], swing=32),
        dict(health=28, damage=0, speed=0.25, knockback=0.0, xp=3, width=1.3,
             height=1.6, tame=True, tame_item="eternal_end:lumen_feed",
             breed_item="minecraft:chorus_fruit", meat="chorus_beef",
             panics=True, milkable=True),
        spawn=dict(weight=14, herd=(2, 4), light="any", passive=True),
        loot=[("eternal_end:raw_chorus_beef", 1, 3), ("minecraft:leather", 0, 2)],
        egg=("#2A1428", "#F05CF0"),
        summary="Tameable livestock. Milk it with a bucket, breed it with "
                "chorus fruit.",
    ),
    Mob(
        "void_hog", "Void Hog", "passive_tame", _void_hog,
        gait(legs=QUAD_LEGS, head="head", tail=["tail"], swing=40),
        dict(health=22, damage=0, speed=0.28, knockback=0.0, xp=3, width=1.1,
             height=1.2, tame=True, tame_item="eternal_end:lumen_feed",
             breed_item="eternal_end:lumen_feed", meat="void_pork", panics=True),
        spawn=dict(weight=15, herd=(2, 4), light="any", passive=True),
        loot=[("eternal_end:raw_void_pork", 1, 3)],
        egg=("#191622", "#B04CFF"),
        summary="Tameable livestock, and it roots out Void Embers when it "
                "wanders.",
    ),
    Mob(
        "sky_ray", "Sky Ray", "passive_tame", _sky_ray,
        gait(wings=[("wing_left", 1), ("wing_right", -1)], head="head",
             tail=["tail", "tail2"], hover=True, bob=2.4, flap=22,
             extra=["wingtip_left", "wingtip_right"]),
        dict(health=32, damage=0, speed=0.2, fly_speed=0.5, knockback=0.0, xp=3,
             width=3.0, height=0.9, flying=True, tame=True,
             tame_item="eternal_end:lumen_feed", breed_item="eternal_end:lumen_feed",
             meat="ray_meat", rideable=True),
        spawn=dict(weight=8, herd=(1, 2), light="any", passive=True),
        loot=[("eternal_end:raw_ray_meat", 1, 2)],
        egg=("#1A1836", "#3FE8F5"),
        summary="Flying passive. Tame it, saddle it, and ride it across the "
                "void.",
    ),
    Mob(
        "ender_bird", "Ender Bird", "passive_tame", _ender_bird,
        gait(wings=[("wing_left", 1), ("wing_right", -1)],
             legs=[("leg_left", 1), ("leg_right", -1)], head="head",
             tail=["tail"], hover=True, bob=1.2, flap=52, extra=["crest"]),
        dict(health=14, damage=0, speed=0.25, fly_speed=0.55, knockback=0.0, xp=3,
             width=0.7, height=0.9, flying=True, tame=True,
             tame_item="eternal_end:lumen_feed", breed_item="eternal_end:lumen_feed",
             meat="ender_poultry", sits=True),
        spawn=dict(weight=17, herd=(2, 4), light="any", passive=True),
        loot=[("eternal_end:raw_ender_poultry", 1, 2), ("minecraft:feather", 0, 2)],
        egg=("#161435", "#3FE8F5"),
        summary="Tameable companion. Perches, follows, and lays into anything "
                "that hurts its owner.",
    ),
]

BY_ID = {mob.id: mob for mob in ROSTER}
