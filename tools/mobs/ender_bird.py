import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, muzzle, stand, taper_chain,
                    wing, write)

# Ender Bird: a long-necked flier built like a heron crossed with a crow. It
# spends most of its time in the air, so the wings are framed properly - a
# spar, ribs and feather panels - rather than being two flat plates, and the
# legs fold up under it.
atlas = UVAtlas(256, 256, padding=1)
bones = []

BODY_Y = 30

uv = atlas.box((10, 11, 18))
bones.append(bone("body", [0, BODY_Y, 0],
                  [cube([-5, BODY_Y - 5, -9], [10, 11, 18], uv)]))
uv = atlas.box((11, 9, 10))
bones.append(bone("breast", [0, BODY_Y - 1, -8],
                  [cube([-5.5, BODY_Y - 6, -16], [11, 9, 10], uv)], parent="body"))
# Coverts: a layer of shorter feathers over the shoulder of each wing.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((7, 4, 13))
    bones.append(bone("covert_" + tag, [side * 5, BODY_Y + 4, -4],
                      [cube([side * 5 - 3.5, BODY_Y + 2, -10], [7, 4, 13], uv,
                            mirror=mirror)], parent="body",
                      rotation=[0, 0, side * 16]))

# Neck: a real chain, so it can curve and strike.
neck, neck_tip = taper_chain(atlas, "neck", "breast", [0, BODY_Y + 4, -14], 5,
                             (6, 6, 5), -4.0, shrink=0.9, drop=3.2)
bones.extend(neck)

bones.extend(muzzle(atlas, "head", neck_tip, [0, BODY_Y + 20, -22],
                    skull=(6, 6, 7), snout=(4, 4, 12),
                    jaw_drop=13.0, teeth=3, tooth_size=(1, 2, 1),
                    nostrils=True, brow=True))
# A crest of three quills off the back of the skull.
for i in range(3):
    uv = atlas.box((2, 9 - i * 2, 2))
    bones.append(bone("quill_%d" % i, [0, BODY_Y + 24, -18],
                      [cube([-1, BODY_Y + 24, -18 + i * 2], [2, 9 - i * 2, 2], uv)],
                      parent="head", rotation=[40 + i * 14, 0, (i - 1) * 16]))

# Wings, spread. `wing()` gives a spar, ribs and membrane; the primaries go on
# top of that as separate feathers so the trailing edge is not a straight cut.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(wing(atlas, "wing_" + tag, "body", [side * 5, BODY_Y + 4, -4],
                      span=26, chord=15, ribs=4, sweep=-14.0, thickness=1,
                      droop=8.0, mirrored=mirror))
    for i in range(5):
        length = 17 - i * 2
        uv = atlas.box((3, 2, length))
        px = side * (10 + i * 4)
        bones.append(bone("primary_%s%d" % (tag, i), [px, BODY_Y + 4, 4],
                          [cube([px - 1.5, BODY_Y + 3, 4], [3, 2, length], uv,
                                mirror=mirror)], parent="wing_" + tag,
                          rotation=[6 + i * 3, side * (-6 - i * 4), 0]))

# Tail: a fan of five feathers on their own bones.
for i in range(5):
    t = i - 2
    length = 18 - abs(t) * 3
    uv = atlas.box((3, 2, length))
    bones.append(bone("tailfeather_%d" % i, [t * 2.4, BODY_Y - 1, 9],
                      [cube([t * 2.4 - 1.5, BODY_Y - 2, 9], [3, 2, length], uv)],
                      parent="body", rotation=[8, t * 9, 0]))

# Legs, folded up the way a heron carries them, ending in a grasping foot.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((3, 10, 3))
    bones.append(bone("thigh_" + tag, [side * 3, BODY_Y - 5, 2],
                      [cube([side * 3 - 1.5, BODY_Y - 15, 0.5], [3, 10, 3], uv,
                            mirror=mirror)], parent="body",
                      rotation=[24, 0, side * 6]))
    uv = atlas.box((2, 12, 2))
    bones.append(bone("shank_" + tag, [side * 3, BODY_Y - 15, 2],
                      [cube([side * 3 - 1, BODY_Y - 27, 1], [2, 12, 2], uv,
                            mirror=mirror)], parent="thigh_" + tag,
                      rotation=[-46, 0, 0]))
    for i in range(3):
        uv = atlas.box((1, 2, 5))
        tx = side * 3 + (i - 1) * 1.6
        bones.append(bone("talon_%s%d" % (tag, i), [tx, BODY_Y - 27, 2],
                          [cube([tx - 0.5, BODY_Y - 28, -3], [1, 2, 5], uv)],
                          parent="shank_" + tag,
                          rotation=[10, (i - 1) * 26, 0]))
    uv = atlas.box((1, 2, 4))
    bones.append(bone("spur_" + tag, [side * 3, BODY_Y - 27, 2],
                      [cube([side * 3 - 0.5, BODY_Y - 28, 2], [1, 2, 4], uv)],
                      parent="shank_" + tag, rotation=[-14, 0, 0]))

write("RP/models/entity/ender_bird.geo.json",
      geometry("geometry.voidbound.ender_bird", (256, 256), bones,
               bounds=(3, 3, (0, 1.4, 0))))
print("ender_bird: %d bones" % len(bones))
