import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, muzzle, radial_leg, stand,
                    taper_chain, write)

# End Crab: a wide, low carapace on eight radial legs, two heavy claws held
# forward, and a shell crusted with the crystal it has been scraping off the
# island all its life. Low and wide is the whole read, so the body is one
# broad shell rather than a torso.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((26, 7, 18))
bones.append(bone("shell", [0, 14, 0], [cube([-13, 11, -9], [26, 7, 18], uv)]))
# A stepped rim around the shell so it is a carapace and not a table top.
for i, (rw, rd, ry, grow) in enumerate(((24, 16, 18, 0.0), (20, 13, 20, 0.0),
                                        (14, 9, 21.5, 0.0))):
    uv = atlas.box((rw, 3, rd))
    bones.append(bone("dome_%d" % i, [0, ry, -1],
                      [cube([-rw / 2.0, ry - 1.5, -1 - rd / 2.0], [rw, 3, rd], uv)],
                      parent="shell"))
uv = atlas.box((22, 4, 14))
bones.append(bone("apron", [0, 10, 2],
                  [cube([-11, 8, -5], [22, 4, 14], uv)], parent="shell"))

# Crystal growths across the back - the crab's own reef.
for i, (gx, gz, gh, tilt) in enumerate(((-7, -4, 7, -18), (5, -6, 9, 14),
                                        (0, 2, 6, 4), (-4, 5, 5, -22),
                                        (8, 3, 6, 26), (-10, 0, 4, -34))):
    uv = atlas.box((3, gh, 3))
    bones.append(bone("crystal_%d" % i, [gx, 22, gz],
                      [cube([gx - 1.5, 22, gz - 1.5], [3, gh, 3], uv)],
                      parent="shell", rotation=[tilt * 0.4, 0, tilt]))
    uv = atlas.box((2, max(2, gh - 3), 2))
    bones.append(bone("crystal_%d_tip" % i, [gx, 22 + gh, gz],
                      [cube([gx - 1, 22 + gh - 1, gz - 1],
                            [2, max(2, gh - 3), 2], uv)],
                      parent="crystal_%d" % i, rotation=[0, 0, -tilt * 0.6]))

# Eyes on stalks, because a crab looks at you over the top of its own shell.
for side in (1, -1):
    uv = atlas.box((2, 7, 2))
    bones.append(bone("stalk_%s" % ("l" if side > 0 else "r"),
                      [side * 5, 18, -9],
                      [cube([side * 5 - 1, 18, -10], [2, 7, 2], uv)],
                      parent="shell", rotation=[-14, 0, side * 12]))
    uv = atlas.box((3, 3, 3))
    bones.append(bone("eyeball_%s" % ("l" if side > 0 else "r"),
                      [side * 5, 25, -9],
                      [cube([side * 5 - 1.5, 25, -10.5], [3, 3, 3], uv)],
                      parent="stalk_%s" % ("l" if side > 0 else "r")))

# Mouthparts. Small, but the rule is that everything gets a mouth.
bones.extend(muzzle(atlas, "face", "shell", [0, 13, -9],
                    skull=(9, 5, 4), snout=(6, 3, 3),
                    jaw_drop=20.0, teeth=3, tooth_size=(1, 2, 1),
                    nostrils=False, brow=False))

# Claws: a shoulder, a forearm, then a fixed jaw and a hinged one.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((8, 5, 5))
    bones.append(bone("arm_" + tag, [side * 12, 13, -6],
                      [cube([side * 12 if side > 0 else side * 12 - 8, 10.5, -8.5],
                            [8, 5, 5], uv, mirror=mirror)],
                      parent="shell", rotation=[0, side * 34, side * 8]))
    # The palm: a heavy swollen block. Without it the two jaws read as a pair
    # of planks nailed to a stick rather than a pincer on a hand.
    uv = atlas.box((9, 10, 11))
    bones.append(bone("fore_" + tag, [side * 20, 13, -6],
                      [cube([side * 20 - 4.5, 8, -17], [9, 10, 11], uv,
                            mirror=mirror)],
                      parent="arm_" + tag, rotation=[0, side * -26, 0]))
    # The fixed lower jaw: short, deep, and thick enough to have a bite.
    uv = atlas.box((7, 5, 10))
    bones.append(bone("claw_" + tag, [side * 20, 11, -17],
                      [cube([side * 20 - 3.5, 8.5, -27], [7, 5, 10], uv,
                            mirror=mirror)],
                      parent="fore_" + tag, rotation=[6, side * -6, 0]))
    uv = atlas.box((4, 3, 5))
    bones.append(bone("clawtip_" + tag, [side * 20, 11, -27],
                      [cube([side * 20 - 2, 9.5, -32], [4, 3, 5], uv,
                            mirror=mirror)],
                      parent="claw_" + tag, rotation=[10, 0, 0]))
    # The hinged upper jaw, held open.
    uv = atlas.box((6, 5, 9))
    bones.append(bone("nip_" + tag, [side * 20, 16, -17],
                      [cube([side * 20 - 3, 14, -26], [6, 5, 9], uv,
                            mirror=mirror)],
                      parent="fore_" + tag, rotation=[-26, side * -6, 0]))
    uv = atlas.box((4, 3, 5))
    bones.append(bone("niptip_" + tag, [side * 20, 15, -26],
                      [cube([side * 20 - 2, 14, -31], [4, 3, 5], uv,
                            mirror=mirror)],
                      parent="nip_" + tag, rotation=[-12, 0, 0]))
    # Teeth along the bite line of both jaws.
    for i in range(4):
        cz = -19 - i * 2.5
        uv = atlas.box((3, 2, 2))
        bones.append(bone("serr_%s%d" % (tag, i), [side * 20, 13.5, cz],
                          [cube([side * 20 - 1.5, 13.5, cz], [3, 2, 2], uv)],
                          parent="claw_" + tag))
        uv = atlas.box((3, 2, 2))
        bones.append(bone("serrup_%s%d" % (tag, i), [side * 20, 14, cz],
                          [cube([side * 20 - 1.5, 12, cz], [3, 2, 2], uv)],
                          parent="nip_" + tag))

# Eight legs, fanned front to back, arched high over the shell.
for side, mirror in ((1, False), (-1, True)):
    for i in range(4):
        bones.extend(radial_leg(atlas, "leg_%s%d" % ("l" if side > 0 else "r", i),
                                "shell", [side * 11, 13, -4 + i * 4],
                                femur=(9, 3, 3), tibia=(3, 15, 3),
                                tarsus=(2, 5, 2),
                                fan=30 - i * 22, lift=42 - i * 4,
                                drop=16 + i * 3, claw=56, mirrored=mirror))

write("RP/models/entity/end_crab.geo.json",
      geometry("geometry.voidbound.end_crab", (256, 256), stand(bones),
               bounds=(3, 2, (0, 0.8, 0))))
print("end_crab: %d bones" % len(bones))
