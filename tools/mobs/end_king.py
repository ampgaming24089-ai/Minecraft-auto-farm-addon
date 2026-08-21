import sys, math
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, limb, stand, taper_chain, write

# The End King: an armoured figure, so the design is almost entirely *layers*.
# A humanoid with a texture painted to look like armour reads as pyjamas; what
# makes plate read as plate is that it stands proud of what it covers, with a
# visible edge where one piece overlaps the next.
atlas = UVAtlas(512, 512, padding=1)
bones = []

HIP_Y = 24

# --- Torso: a chest, a narrower waist, and a plated cuirass over both -----
uv = atlas.box((16, 16, 10))
bones.append(bone("chest", [0, HIP_Y + 14, 0],
                  [cube([-8, HIP_Y + 8, -5], [16, 16, 10], uv)]))
uv = atlas.box((12, 8, 8))
bones.append(bone("waist", [0, HIP_Y + 6, 0],
                  [cube([-6, HIP_Y + 2, -4], [12, 8, 8], uv)], parent="chest"))
# Cuirass plates, each a little wider than the body beneath and stepped down.
for i, (w, h, d, y) in enumerate([(19, 7, 12, HIP_Y + 17),
                                  (18, 6, 12, HIP_Y + 12),
                                  (15, 5, 11, HIP_Y + 7)]):
    uv = atlas.box((w, h, d))
    bones.append(bone("cuirass_%d" % i, [0, y, 0],
                      [cube([-w / 2.0, y, -d / 2.0], [w, h, d], uv)], parent="chest"))
# The core: a lit gem set into the breastplate.
uv = atlas.box((6, 6, 3))
bones.append(bone("core", [0, HIP_Y + 15, -6],
                  [cube([-3, HIP_Y + 13, -7.5], [6, 6, 3], uv)], parent="chest"))

# --- Head: the muzzle builder, then a helm and crown over it -------------
bones.extend(muzzle(atlas, "head", "chest", [0, HIP_Y + 30, 4],
                    skull=(9, 9, 9), snout=(7, 4, 3),
                    jaw_drop=5.0, teeth=4, tooth_size=(1, 2, 1),
                    nostrils=False, brow=False))
uv = atlas.box((11, 6, 11))
bones.append(bone("helm", [0, HIP_Y + 32, 0],
                  [cube([-5.5, HIP_Y + 30, -5.5], [11, 6, 11], uv)], parent="head"))
for i in range(5):
    t = (i - 2) / 2.0
    h = 10 - abs(i - 2) * 3
    uv = atlas.box((2, h, 2))
    bones.append(bone("crown_%d" % i, [t * 4, HIP_Y + 35, -3],
                      [cube([t * 4 - 1, HIP_Y + 35, -4], [2, h, 2], uv)],
                      parent="helm", rotation=[-8, 0, t * 9]))
# Cheek guards, so the helm frames a face rather than swallowing it.
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((2, 8, 8))
    bones.append(bone("cheek_%s" % ("l" if side > 0 else "r"),
                      [side * 5, HIP_Y + 30, 0],
                      [cube([side * 5 - (0 if side > 0 else 2), HIP_Y + 24, -4],
                            [2, 8, 8], uv, mirror=mirror)], parent="helm"))

# --- Arms with pauldrons and vambraces -----------------------------------
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    arm = "arm_" + tag
    uv = atlas.box((5, 16, 5))
    ox = side * 8 if side > 0 else side * 8 - 5
    bones.append(bone(arm, [side * 9, HIP_Y + 22, 0],
                      [cube([ox, HIP_Y + 6, -2.5], [5, 16, 5], uv, mirror=mirror)],
                      parent="chest", rotation=[0, 0, side * -4]))
    uv = atlas.box((10, 7, 11))
    px = side * 8 if side > 0 else side * 8 - 10
    bones.append(bone("pauldron_" + tag, [side * 9, HIP_Y + 22, 0],
                      [cube([px, HIP_Y + 18, -5.5], [10, 7, 11], uv, mirror=mirror)],
                      parent=arm, rotation=[0, 0, side * -12]))
    uv = atlas.box((7, 6, 7))
    vx = side * 8 - 1 if side > 0 else side * 8 - 6
    bones.append(bone("vambrace_" + tag, [side * 9, HIP_Y + 12, 0],
                      [cube([vx, HIP_Y + 8, -3.5], [7, 6, 7], uv, mirror=mirror)],
                      parent=arm))

# --- Legs and a tasset skirt ---------------------------------------------
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(limb(atlas, "leg_" + tag, "waist", [side * 4, HIP_Y + 2, 0],
                      (6, 12, 6), (5, 12, 5), foot=(6, 3, 9), mirrored=mirror))
for i in range(6):
    angle = (i / 6.0) * math.pi * 2
    uv = atlas.box((5, 10, 3))
    rx = math.cos(angle) * 6
    rz = math.sin(angle) * 6
    bones.append(bone("tasset_%d" % i, [rx, HIP_Y + 2, rz],
                      [cube([rx - 2.5, HIP_Y - 8, rz - 1.5], [5, 10, 3], uv)],
                      parent="waist", rotation=[0, math.degrees(angle), 0]))

# --- Cape: four panels down the back, each hinged off the last -----------
prev = "chest"
cy = HIP_Y + 22
for i in range(4):
    w = 20 - i * 2
    uv = atlas.box((w, 10, 1))
    name = "cape_%d" % i
    bones.append(bone(name, [0, cy, 5],
                      [cube([-w / 2.0, cy - 10, 5], [w, 10, 1], uv)],
                      parent=prev, rotation=[10 + i * 5, 0, 0]))
    prev = name
    cy -= 10

# --- Greatsword, held point-down at his side -----------------------------
# Built along -Y from the fist so the blade hangs the way a held sword hangs.
# The first attempt ran the blade along -Z and then rotated the grip by 90
# degrees, which put sixty blocks of steel through the floor and shrank the
# King to nothing in frame - the bounding box follows the longest thing in it.
HAND_X, HAND_Y = -11, HIP_Y + 6
uv = atlas.box((4, 9, 4))
bones.append(bone("grip", [HAND_X, HAND_Y, 0],
                  [cube([HAND_X - 2, HAND_Y - 4, -2], [4, 9, 4], uv)],
                  parent="arm_r", rotation=[14, 0, -8]))
uv = atlas.box((3, 3, 3))
bones.append(bone("pommel", [HAND_X, HAND_Y + 5, 0],
                  [cube([HAND_X - 1.5, HAND_Y + 5, -1.5], [3, 3, 3], uv)],
                  parent="grip"))
uv = atlas.box((13, 2, 5))
bones.append(bone("guard", [HAND_X, HAND_Y - 4, 0],
                  [cube([HAND_X - 6.5, HAND_Y - 6, -2.5], [13, 2, 5], uv)],
                  parent="grip"))
blade_y = HAND_Y - 6
for i in range(3):
    w = 7 - i * 2
    length = 11 - i
    uv = atlas.box((w, length, 3))
    bones.append(bone("blade_%d" % i, [HAND_X, blade_y, 0],
                      [cube([HAND_X - w / 2.0, blade_y - length, -1.5],
                            [w, length, 3], uv)],
                      parent="guard" if i == 0 else "blade_%d" % (i - 1)))
    blade_y -= length

write("RP/models/entity/end_king.geo.json",
      geometry("geometry.voidbound.end_king", (512, 512), stand(bones),
               bounds=(3, 5, (0, 2, 0))))
print("end_king: %d bones, %d cubes"
      % (len(bones), sum(len(b.get("cubes", [])) for b in bones)))
