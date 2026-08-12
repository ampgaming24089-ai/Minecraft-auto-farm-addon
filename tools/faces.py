"""
Faces and body markings for the Hollow Veil creatures.

The complaint that started this file was "characters are bland with no unique
designs, they just look like soulless blobs". Two flat glowing dots on the
front of a head box is not a face - it is a domino. A Minecraft mob reads as a
*creature* because of a handful of specific pixels: a recessed socket with a
bright pupil in it, a brow line that gives the eyes an expression, a jaw or
snout that says which end is the front, and something on the chest so the body
is not a blank slab.

Everything here paints into the box-UV atlas cell that boxuv.py already
allocated for a cube, so faces land exactly on the front face of the head and
markings land exactly on the chest, at any cube size, with no per-mob
hand-tuning.

Each creature picks a FACE style and a CHEST marking. The styles are written
to look different from each other at a glance - a hellhound's fanged snout
should not be a recoloured wraith - and to stay legible at the 6-10 pixels a
mob head actually occupies on screen.
"""

# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------
def shade(color, amount):
    """Lighten (positive) or darken (negative) an RGBA colour, keeping alpha."""
    r, g, b = color[:3]
    a = color[3] if len(color) > 3 else 255
    return (
        max(0, min(255, r + amount)),
        max(0, min(255, g + amount)),
        max(0, min(255, b + amount)),
        a,
    )


def mix(a, b, t):
    """Blend two RGBA colours; t=0 is all `a`, t=1 is all `b`."""
    return tuple(
        int(round(a[i] * (1 - t) + b[i] * t)) if i < 3 else (a[3] if len(a) > 3 else 255)
        for i in range(3)
    ) + ((a[3] if len(a) > 3 else 255),)


def _fill(draw, x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=color)


def _dot(draw, x, y, color):
    draw.point((x, y), fill=color)


# --------------------------------------------------------------------------
# face layout
# --------------------------------------------------------------------------
def _round(v):
    """Half-up rounding. Python rounds halves to even, which quietly turned
    a 10px face's 2.5px eye into 2px and made big heads look beady."""
    return int(v + 0.5)


class Layout:
    """Where the features go on a face of any size.

    Derived from vanilla proportions rather than invented: on a zombie's 8x8
    face the eyes are 2x2, one pixel in from each side, three rows down, with
    a two-pixel gap between them, and the mouth sits two rows off the bottom.
    Every ratio here reproduces that at 8x8 and scales sensibly either way,
    with minimums so a 5px face still gets separated eyes instead of one
    merged smear - which is exactly how the small-headed mobs used to look.
    """

    def __init__(self, rect):
        self.x, self.y, self.w, self.h = rect
        w, h = self.w, self.h

        self.eye_w = max(1, _round(w * 0.25))
        self.eye_h = max(1, _round(h * 0.22))
        self.brow_y = self.y + max(1, _round(h * 0.20)) - 1
        self.eye_y = self.brow_y + 1

        inset = max(1, _round(w * 0.13))
        self.left_x = self.x + inset
        self.right_x = self.x + w - inset - self.eye_w
        # Never let the two eyes touch: a single wide bar reads as a visor,
        # not as a pair of eyes.
        if self.right_x - (self.left_x + self.eye_w) < 1:
            self.eye_w = max(1, (w - 3) // 2)
            self.left_x = self.x + 1
            self.right_x = self.x + w - 1 - self.eye_w

        self.mouth_y = self.y + h - max(2, _round(h * 0.25))
        self.mid_x = self.x + w // 2
        self.mid_y = self.y + h // 2

    @property
    def eye_gap(self):
        return self.right_x - (self.left_x + self.eye_w)

    def pair(self, ew, eh, y=None):
        """Two eye rects of the requested size that are guaranteed not to
        touch, shrinking them if the face is too narrow to hold both."""
        ew = max(1, min(ew, (self.w - 3) // 2))
        eh = max(1, min(eh, self.h - 2))
        y = self.eye_y if y is None else y
        lx = self.x + 1
        rx = self.x + self.w - 1 - ew
        return [(lx, y, ew, eh), (rx, y, ew, eh)]

    def both_eyes(self):
        """(x, y, w, h) for the left and right eye in turn."""
        yield self.left_x, self.eye_y, self.eye_w, self.eye_h
        yield self.right_x, self.eye_y, self.eye_w, self.eye_h


# --------------------------------------------------------------------------
# eye primitives
# --------------------------------------------------------------------------
def _socket(draw, x, y, w, h, dark):
    """A recessed hole. Every eye style starts from one of these: the sunken
    shadow is what makes a bright pupil read as being *inside* a head rather
    than painted on top of it."""
    _fill(draw, x, y, w, h, dark)


def _glow_eye(draw, x, y, w, h, glow, dark):
    """Socket + glow + a single hot pixel. The hot pixel is the whole trick:
    one pixel brighter than the glow reads as a highlight and gives the eye
    a direction, so the mob looks like it is looking at you."""
    _socket(draw, x, y, w, h, dark)
    if w >= 2 and h >= 2:
        _fill(draw, x, y, w, h - 1, glow)
        _dot(draw, x, y, shade(glow, 60))
    else:
        _fill(draw, x, y, w, h, glow)


def _slit_eye(draw, x, y, w, h, glow, dark):
    """A reptile eye: bright sclera with a vertical pupil down the middle."""
    _socket(draw, x, y, w, h, dark)
    _fill(draw, x, y, w, h, glow)
    _fill(draw, x + w // 2, y, max(1, w // 3), h, shade(dark, -20))


def _compound_eye(draw, x, y, w, h, glow, dark):
    """Insect eye: a checker of two glow values, which at mob scale reads as
    a faceted dome rather than a flat blob."""
    _socket(draw, x, y, w, h, dark)
    hot, cool = glow, mix(glow, dark, 0.45)
    for px in range(w):
        for py in range(h):
            _dot(draw, x + px, y + py, hot if (px + py) % 2 == 0 else cool)


def _bead_eye(draw, x, y, w, h, glow, dark):
    """Small animal eye: mostly pupil with a rim of glow around it."""
    _socket(draw, x, y, w, h, dark)
    _fill(draw, x, y, w, h, glow)
    if w >= 3 and h >= 3:
        _fill(draw, x + 1, y + 1, w - 2, h - 2, shade(dark, -15))
        _dot(draw, x + 1, y + 1, shade(glow, 70))


# --------------------------------------------------------------------------
# face styles
# --------------------------------------------------------------------------
# Every style takes the same arguments so they are interchangeable:
#   draw       - PIL ImageDraw on the atlas
#   rect       - (x, y, w, h) of the head cube's FRONT face in the atlas
#   base       - the head's base colour, so shadows stay in the same family
#   glow       - the creature's eye colour from EYE_GLOW
# Styles must tolerate small faces: a 4x4 front face still has to look like
# something, so each one guards on size before adding the finer marks.


def face_hollow(draw, rect, base, glow):
    """Empty burning sockets under a heavy brow, no mouth. The Veil's ghosts:
    wraiths, banshees, shades, the Hollow King."""
    L = Layout(rect)
    dark = shade(base, -85)
    _fill(draw, L.left_x, L.brow_y, L.right_x + L.eye_w - L.left_x, 1, shade(base, -50))
    for ex, ey, ew, eh in L.both_eyes():
        _socket(draw, ex, ey, ew, eh + 1, dark)
        _glow_eye(draw, ex, ey, ew, eh, glow, dark)
    # A hollow throat: darkness where a jaw should be, no mouth drawn.
    if L.h >= 7:
        tw = max(1, L.w // 3)
        _fill(draw, L.mid_x - tw // 2, L.mouth_y, tw, L.y + L.h - L.mouth_y - 1, dark)
        _fill(draw, L.mid_x - tw // 2, L.mouth_y, tw, 1, shade(dark, -20))


def face_skull(draw, rect, base, glow):
    """Bone: deep sockets with an ember in each, a nasal notch, teeth."""
    L = Layout(rect)
    dark = shade(base, -95)
    bone = shade(base, 45)

    for ex, ey, ew, eh in L.both_eyes():
        _socket(draw, ex, ey, ew, eh + 1, dark)
        _dot(draw, ex + ew // 2, ey + eh // 2, glow)
    _fill(draw, L.left_x, L.brow_y, L.right_x + L.eye_w - L.left_x, 1, shade(base, -40))

    if L.h >= 6:
        _fill(draw, L.mid_x, L.eye_y + L.eye_h, 1, max(1, L.h // 6), dark)   # nose
    if L.h >= 6 and L.w >= 5:
        _fill(draw, L.x + 1, L.mouth_y, L.w - 2, max(1, L.h // 6), bone)
        for tx in range(L.x + 2, L.x + L.w - 1, 2):
            _fill(draw, tx, L.mouth_y, 1, max(1, L.h // 6), dark)


def face_beast(draw, rect, base, glow):
    """A snout jutting into the lower half, down-slanted eyes, fangs."""
    L = Layout(rect)
    dark = shade(base, -85)
    muzzle = shade(base, -30)

    for ex, ey, ew, eh in L.both_eyes():
        _glow_eye(draw, ex, ey, ew, eh, glow, dark)
    # Down-slant: one shadowed pixel at each eye's inner corner is the whole
    # difference between an angry animal and a startled one.
    _fill(draw, L.left_x + L.eye_w, L.eye_y, 1, 1, shade(base, -55))
    _fill(draw, L.right_x - 1, L.eye_y, 1, 1, shade(base, -55))
    _fill(draw, L.left_x, L.brow_y, L.eye_w + 1, 1, shade(base, -55))
    _fill(draw, L.right_x - 1, L.brow_y, L.eye_w + 1, 1, shade(base, -55))

    if L.h >= 6:
        mw = max(3, L.w // 2)
        mx = L.mid_x - mw // 2
        my = L.mouth_y - 1
        _fill(draw, mx, my, mw, L.y + L.h - my, muzzle)
        _fill(draw, mx + 1, my, 1, 1, dark)                       # nostrils
        _fill(draw, mx + mw - 2, my, 1, 1, dark)
        _fill(draw, mx, L.y + L.h - 2, mw, 1, dark)               # mouth line
        for fx in (mx + 1, mx + mw - 2):                          # fangs
            _fill(draw, fx, L.y + L.h - 2, 1, 1, shade(base, 70))


def face_draconic(draw, rect, base, glow):
    """Slit pupils under a brow that runs out into horn roots, nostrils high
    on the snout, tusks at the corners of the mouth."""
    L = Layout(rect)
    dark = shade(base, -90)

    _fill(draw, L.x + 1, L.brow_y, L.w - 2, 1, shade(base, -60))
    _fill(draw, L.x, L.brow_y - 1, 2, 1, shade(base, -60))        # horn roots
    _fill(draw, L.x + L.w - 2, L.brow_y - 1, 2, 1, shade(base, -60))

    for ex, ey, ew, eh in L.both_eyes():
        _slit_eye(draw, ex, ey, max(2, ew), eh, glow, dark)

    if L.h >= 7:
        ny = L.mouth_y - 1
        _fill(draw, L.mid_x - 1, ny, 1, 1, dark)                  # nostrils
        _fill(draw, L.mid_x + 1, ny, 1, 1, dark)
        _fill(draw, L.x + 2, L.y + L.h - 2, L.w - 4, 1, dark)     # mouth seam
        for fx in (L.x + 2, L.x + L.w - 3):
            _fill(draw, fx, L.y + L.h - 3, 1, 2, shade(base, 90))  # tusks


def face_imp(draw, rect, base, glow):
    """Oversized round eyes with tiny pupils and a wide grin. Imps and whelps
    are the comic relief of the roster and should look it."""
    L = Layout(rect)
    dark = shade(base, -80)

    for ex, ey, ew, eh in L.pair(_round(L.w * 0.3), _round(L.h * 0.3)):
        _bead_eye(draw, ex, ey, ew, eh, glow, dark)

    if L.h >= 6 and L.w >= 5:
        gy = L.mouth_y
        _fill(draw, L.x + 2, gy, L.w - 4, 1, dark)                # grin
        _fill(draw, L.x + 1, gy - 1, 1, 1, dark)                  # upturned ends
        _fill(draw, L.x + L.w - 2, gy - 1, 1, 1, dark)
        for tx in range(L.x + 3, L.x + L.w - 3, 2):
            _fill(draw, tx, gy, 1, 1, shade(base, 95))            # teeth


def face_insect(draw, rect, base, glow):
    """Two big faceted eyes and a pair of mandibles. Marrow crawlers."""
    L = Layout(rect)
    dark = shade(base, -80)

    for ex, ey, ew, eh in L.pair(_round(L.w * 0.3), _round(L.h * 0.35), L.y + 1):
        _compound_eye(draw, ex, ey, ew, eh, glow, dark)

    if L.h >= 5:
        _fill(draw, L.mid_x - 1, L.mouth_y, 1, 2, shade(base, -45))   # mandibles
        _fill(draw, L.mid_x + 1, L.mouth_y, 1, 2, shade(base, -45))
        _fill(draw, L.mid_x, L.mouth_y - 1, 1, 1, dark)


def face_amphibian(draw, rect, base, glow):
    """Eyes bulging off the top edge, mouth the full width of the face."""
    L = Layout(rect)
    dark = shade(base, -70)

    for ex, ey, ew, eh in L.pair(_round(L.w * 0.25), _round(L.h * 0.3), L.y):
        _bead_eye(draw, ex, ey, ew, eh, glow, dark)

    _fill(draw, L.x + 1, L.mouth_y, L.w - 2, 1, dark)             # wide mouth
    _fill(draw, L.x, L.mouth_y - 1, 1, 1, dark)                   # corners
    _fill(draw, L.x + L.w - 1, L.mouth_y - 1, 1, 1, dark)
    if L.h >= 5:
        _fill(draw, L.mid_x - 1, L.mid_y, 1, 1, shade(base, 30))  # nostrils
        _fill(draw, L.mid_x + 1, L.mid_y, 1, 1, shade(base, 30))


def face_visor(draw, rect, base, glow):
    """No face: a helm with one lit slit, a nasal bar and rivets. Constructs
    should look manufactured, not alive."""
    L = Layout(rect)
    dark = shade(base, -90)
    metal = shade(base, 45)

    sy = L.eye_y
    sh = max(1, L.eye_h)
    _fill(draw, L.x + 1, sy - 1, L.w - 2, 1, dark)                # helm brow
    _fill(draw, L.x + 1, sy, L.w - 2, sh, dark)                   # visor recess
    _fill(draw, L.x + 2, sy, L.w - 4, sh, glow)                   # lit slit
    _fill(draw, L.mid_x, sy, 1, sh, dark)                         # nasal bar

    for rx in (L.x + 1, L.x + L.w - 2):
        _fill(draw, rx, L.y + 1, 1, 1, metal)
        _fill(draw, rx, L.y + L.h - 2, 1, 1, metal)
    if L.h >= 7:
        _fill(draw, L.x + 2, L.mouth_y, L.w - 4, 1, shade(base, -35))
        for bx in range(L.x + 3, L.x + L.w - 3, 2):               # breathing slots
            _fill(draw, bx, L.mouth_y, 1, 1, dark)


def face_hooded(draw, rect, base, glow):
    """A shadowed hood with two pinpricks and a hint of a chin. The Occultist
    is a person hiding, not a monster."""
    L = Layout(rect)
    dark = shade(base, -100)

    _fill(draw, L.x + 1, L.brow_y, L.w - 2, max(2, L.h // 2), dark)
    for ex, ey, ew, eh in L.both_eyes():
        _fill(draw, ex + ew // 2, ey + 1, 1, 1, glow)
    if L.h >= 7:
        _fill(draw, L.x + L.w // 3, L.y + L.h - 2, max(1, L.w // 3), 1, shade(base, 25))


def face_wisp(draw, rect, base, glow):
    """No anatomy: a bright core in a halo that falls off to the edges."""
    L = Layout(rect)
    halo = mix(base, glow, 0.5)
    _fill(draw, L.x + 1, L.y + 1, L.w - 2, L.h - 2, halo)
    cw = max(1, L.w // 3)
    ch = max(1, L.h // 3)
    _fill(draw, L.mid_x - cw // 2, L.mid_y - ch // 2, cw, ch, glow)
    _dot(draw, L.mid_x, L.mid_y, shade(glow, 80))


def face_bat(draw, rect, base, glow):
    """Small bright eyes set wide, a nose leaf between them."""
    L = Layout(rect)
    dark = shade(base, -75)
    for ex, ey, ew, eh in L.both_eyes():
        _bead_eye(draw, ex, ey, ew, eh, glow, dark)
    _fill(draw, L.mid_x, L.eye_y, 1, max(2, L.h // 3), shade(base, -40))
    if L.h >= 5:
        _fill(draw, L.mid_x - 1, L.mouth_y, 3, 1, dark)


FACE_STYLES = {
    "hollow": face_hollow,
    "skull": face_skull,
    "beast": face_beast,
    "draconic": face_draconic,
    "imp": face_imp,
    "insect": face_insect,
    "amphibian": face_amphibian,
    "visor": face_visor,
    "hooded": face_hooded,
    "wisp": face_wisp,
    "bat": face_bat,
}


# Which face each creature wears. Chosen so no two neighbours in a biome share
# one: standing in the Ashlands you should be able to tell an imp from a whelp
# from a hellhound by the head alone.
FACE_OF = {
    "wraith": "hollow",
    "banshee": "hollow",
    "poltergeist": "hollow",
    "shade": "hollow",
    "hollow_king": "hollow",
    "weeping_widow": "hollow",
    "fallen_knight": "skull",
    "bonehide_elk": "skull",
    "city_wraithguard": "visor",
    "bastion_sentinel": "visor",
    "hellhound": "beast",
    "imp": "imp",
    "ashen_whelp": "imp",
    "malacoda": "draconic",
    "veil_dragon": "draconic",
    "marrow_crawler": "insect",
    "glimmershroom_toad": "amphibian",
    "occultist": "hooded",
    "soul_wisp": "wisp",
    "ashwing_bat": "bat",
}


# --------------------------------------------------------------------------
# chest markings
# --------------------------------------------------------------------------
# The body is the largest surface on a mob and was the flattest. Each marking
# is drawn onto the torso's front face and is deliberately simple - a shape
# you can still identify when the mob is ten blocks away and half in fog.


def chest_ribs(draw, rect, base, glow):
    """Ribs arching off a spine. Bone creatures and anything starved."""
    x, y, w, h = rect
    dark = shade(base, -55)
    light = shade(base, 40)
    _fill(draw, x + w // 2, y + 1, 1, h - 2, light)                  # sternum
    for i, ry in enumerate(range(y + 2, y + h - 1, 2)):
        inset = 1 + i // 2
        _fill(draw, x + inset, ry, w - 2 * inset, 1, dark)


def chest_sigil(draw, rect, base, glow):
    """A burning brand: a diamond outline with a lit core. Marks the things
    the Veil has claimed."""
    x, y, w, h = rect
    dark = shade(base, -50)
    cx, cy = x + w // 2, y + h // 2
    r = max(1, min(w, h) // 3)
    for i in range(-r, r + 1):
        _dot(draw, cx + i, cy - (r - abs(i)), dark)
        _dot(draw, cx + i, cy + (r - abs(i)), dark)
    _fill(draw, cx - max(0, r // 3), cy - max(0, r // 3),
          max(1, r), max(1, r), glow)


def chest_plate(draw, rect, base, glow):
    """Banded armour with a centre seam and shoulder straps."""
    x, y, w, h = rect
    dark = shade(base, -45)
    light = shade(base, 45)
    _fill(draw, x + w // 2, y, 1, h, dark)                           # centre seam
    for by in range(y + 2, y + h - 1, 3):
        _fill(draw, x + 1, by, w - 2, 1, dark)
        _fill(draw, x + 1, by + 1, w - 2, 1, light)
    _fill(draw, x + 1, y, 1, max(2, h // 3), light)                  # straps
    _fill(draw, x + w - 2, y, 1, max(2, h // 3), light)


def chest_wrap(draw, rect, base, glow):
    """Bandage or robe wrapping: diagonal folds crossing the body."""
    x, y, w, h = rect
    dark = shade(base, -40)
    for i in range(h):
        px = x + ((i * 2) % max(1, w - 1))
        _dot(draw, px, y + i, dark)
        if px + 1 < x + w:
            _dot(draw, px + 1, y + i, shade(base, 25))


def chest_scales(draw, rect, base, glow):
    """Overlapping belly scutes, brighter down the centre line."""
    x, y, w, h = rect
    dark = shade(base, -40)
    light = shade(base, 35)
    for row, ry in enumerate(range(y + 1, y + h - 1, 2)):
        _fill(draw, x + 1, ry, w - 2, 1, light if row % 2 else dark)


def chest_core(draw, rect, base, glow):
    """A lit core behind a cracked shell - for constructs and elementals."""
    x, y, w, h = rect
    dark = shade(base, -60)
    cx, cy = x + w // 2, y + h // 2
    _fill(draw, cx - 1, cy - 1, 3, 3, glow)
    _dot(draw, cx, cy, shade(glow, 60))
    for dxy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):                 # cracks
        _dot(draw, cx + dxy[0], cy + dxy[1], dark)


def chest_none(draw, rect, base, glow):
    return


CHEST_STYLES = {
    "ribs": chest_ribs,
    "sigil": chest_sigil,
    "plate": chest_plate,
    "wrap": chest_wrap,
    "scales": chest_scales,
    "core": chest_core,
    "none": chest_none,
}


CHEST_OF = {
    "wraith": "wrap",
    "banshee": "wrap",
    "poltergeist": "wrap",
    "shade": "sigil",
    "hollow_king": "sigil",
    "weeping_widow": "wrap",
    "fallen_knight": "plate",
    "city_wraithguard": "plate",
    "bastion_sentinel": "core",
    "bonehide_elk": "ribs",
    "marrow_crawler": "ribs",
    "hellhound": "ribs",
    "imp": "scales",
    "ashen_whelp": "scales",
    "malacoda": "sigil",
    "veil_dragon": "scales",
    "glimmershroom_toad": "scales",
    "occultist": "wrap",
    "soul_wisp": "core",
    "ashwing_bat": "none",
}


def paint_face(draw, rect, base, glow, style):
    """Entry point used by gen_entities. Unknown styles fall back to the
    hollow face rather than leaving a blank head."""
    fn = FACE_STYLES.get(style, face_hollow)
    x, y, w, h = rect
    if w < 3 or h < 3:
        return                      # too small for anything but a smear
    fn(draw, rect, base, glow)


def paint_chest(draw, rect, base, glow, style):
    fn = CHEST_STYLES.get(style, chest_none)
    x, y, w, h = rect
    if w < 4 or h < 4:
        return
    fn(draw, rect, base, glow)


# --------------------------------------------------------------------------
# the rest of the creature
# --------------------------------------------------------------------------
# A face only ever fixed the view from directly in front. Walk behind a mob
# and it was still a plain box, and its arms and legs were plain the whole
# time. These paint the other five faces of the head and a marking on each
# limb, keyed off the same style the face uses so a creature reads as one
# design from every angle.


def head_back(draw, rect, base, glow, style):
    """The back of the skull. Hair, sutures, manes, carapace - whatever the
    front of the face implies is behind it."""
    x, y, w, h = rect
    dark = shade(base, -60)
    light = shade(base, 35)

    if style in ("hollow", "hooded"):
        # a hood drawn closed with laces
        _fill(draw, x + w // 2, y, 1, h, dark)
        for ly in range(y + 1, y + h - 1, 2):
            _fill(draw, x + w // 2 - 1, ly, 3, 1, light)
    elif style == "skull":
        # cranial sutures
        _fill(draw, x + w // 2, y, 1, h, dark)
        for sy in range(y + 2, y + h - 1, 3):
            _fill(draw, x + 1, sy, w - 2, 1, dark)
    elif style == "beast":
        # a mane running down the centre
        _fill(draw, x + w // 2 - 1, y, 3, h, dark)
        for my in range(y, y + h, 2):
            _fill(draw, x + w // 2, my, 1, 1, light)
    elif style == "draconic":
        # a row of spine plates
        for sy in range(y, y + h, 2):
            _fill(draw, x + w // 2 - 1, sy, 3, 1, light)
            _dot(draw, x + w // 2, sy, glow)
    elif style == "imp":
        _fill(draw, x + 1, y, 2, 2, dark)          # horn roots
        _fill(draw, x + w - 3, y, 2, 2, dark)
        _fill(draw, x + 2, y + h // 2, w - 4, 1, light)
    elif style == "insect":
        for sy in range(y, y + h, 2):              # segmented carapace
            _fill(draw, x + 1, sy, w - 2, 1, dark)
    elif style == "amphibian":
        for i in range(3):                          # mottling
            _fill(draw, x + 1 + (i * 2) % max(1, w - 2), y + 1 + i, 2, 1, dark)
    elif style == "visor":
        _fill(draw, x + 1, y + 1, w - 2, 1, light)  # helm seam
        _fill(draw, x + w // 2, y, 1, h, dark)      # crest slot
        for rx in (x + 1, x + w - 2):
            _dot(draw, rx, y + h - 2, light)
    elif style == "wisp":
        _fill(draw, x + 1, y + 1, w - 2, h - 2, mix(base, glow, 0.35))
    else:                                           # bat and anything new
        for i in range(0, h, 2):
            _fill(draw, x + 1, y + i, w - 2, 1, dark)


def head_side(draw, rect, base, glow, style, flip=False):
    """Cheeks, ears, gills. Read most often, since players circle mobs."""
    x, y, w, h = rect
    dark = shade(base, -65)
    light = shade(base, 30)

    if style in ("hollow", "hooded"):
        _fill(draw, x + 1, y + h // 3, w - 2, 1, dark)          # hood edge
    elif style == "skull":
        _fill(draw, x + 1, y + h // 3, max(1, w // 2), 2, dark)  # temple hollow
        _fill(draw, x + 1, y + h - 3, w - 2, 1, shade(base, 40))  # jaw line
    elif style == "beast":
        _fill(draw, x + w // 4, y + 1, 2, 2, dark)               # ear base
        _fill(draw, x + 1, y + h - 3, w - 2, 1, dark)            # jaw
    elif style == "draconic":
        _fill(draw, x + 1, y + 1, 2, 1, light)                   # horn
        _fill(draw, x + w // 3, y + h // 2, 2, 1, glow)          # ear frill
    elif style == "imp":
        _fill(draw, x, y + h // 3, 2, 2, dark)                   # pointed ear
    elif style == "insect":
        for sy in range(y + 1, y + h - 1, 2):
            _dot(draw, x + w // 2, sy, dark)                     # spiracles
    elif style == "amphibian":
        _fill(draw, x + 1, y + h // 2, w - 2, 1, light)          # gill line
    elif style == "visor":
        _fill(draw, x + 1, y + h // 3, w - 2, 1, dark)           # cheek plate
        _dot(draw, x + w // 2, y + h - 3, light)                 # bolt
    elif style == "wisp":
        _fill(draw, x + 1, y + 1, w - 2, h - 2, mix(base, glow, 0.3))
    else:
        _fill(draw, x + 1, y + h // 2, w - 2, 1, dark)


def head_top(draw, rect, base, glow, style):
    """Crowns, scutes, horn beds - the view when a mob is below you, which in
    a dimension full of pits and cliffs happens more than you would think."""
    x, y, w, h = rect
    dark = shade(base, -55)
    light = shade(base, 40)

    if style == "draconic":
        _fill(draw, x + w // 2 - 1, y, 3, h, light)
        for sy in range(y, y + h, 2):
            _dot(draw, x + w // 2, sy, glow)
    elif style == "skull":
        _fill(draw, x + w // 2, y, 1, h, dark)
    elif style in ("imp", "beast"):
        _fill(draw, x + 1, y + 1, 2, 2, dark)
        _fill(draw, x + w - 3, y + 1, 2, 2, dark)
    elif style == "visor":
        _fill(draw, x + 1, y + 1, w - 2, 1, light)
        _fill(draw, x + w // 2, y, 1, h, dark)
    elif style == "wisp":
        _fill(draw, x + 1, y + 1, w - 2, h - 2, glow)
    else:
        for i in range(0, w, 3):
            _dot(draw, x + i, y + h // 2, dark)


# Limb markings: a cuff near the end of each limb plus a stripe up its length.
# Cheap, and it is what stops arms and legs reading as bare dowels.
def limb_marking(draw, rect, base, glow, style):
    x, y, w, h = rect
    dark = shade(base, -55)
    light = shade(base, 35)
    if h >= 5:
        cuff = y + h - 2
        _fill(draw, x, cuff, w, 1, dark)
        if style in ("visor", "skull", "beast"):
            _fill(draw, x, cuff - 1, w, 1, light)
        elif style in ("draconic", "imp"):
            for cx in range(x, x + w, 2):
                _dot(draw, cx, cuff, glow)
    if h >= 7 and w >= 2:
        _fill(draw, x + w // 2, y + 1, 1, h - 4, light if style != "hollow" else dark)
