#!/usr/bin/env python3
"""Generates the Aurora Interface texture set.

Bedrock draws almost every screen out of a small shared pool of textures in
`textures/ui/`. Replacing that pool is what makes the inventory, chests,
crafting, furnaces, the pause menu and settings all change together instead of
one screen at a time - the layout JSON barely has to be touched.

Two rendering rules matter here:

* Nine-slice textures carry an explicit `base_size` in a sidecar `.json`, so the
  PNG may be a whole-number multiple of that size and the engine scales it down.
  Those are rendered at SCALE for crisp edges on high-DPI screens.
* Textures with no sidecar are drawn at their native pixel size, because there
  is no `base_size` to tell the engine what to scale by.

Nine-slice also stretches the middle band of a texture, so all the detail lives
in the fixed border regions and every stretched band is a flat colour. That is
what keeps a panel from smearing when it is scaled up to full screen.
"""
import json
import os

from PIL import Image, ImageDraw

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "packs", "aurora_ui", "textures", "ui"
)

SCALE = 4  # supersampling factor for nine-slice textures

# --- palette ---------------------------------------------------------------
INK = (10, 12, 17, 255)          # deepest wells - slot interiors
SLATE_DEEP = (18, 21, 29, 255)   # panel body
SLATE = (26, 31, 43, 255)        # button body
SLATE_HI = (35, 42, 56, 255)     # raised / hovered surfaces
EDGE_DARK = (5, 7, 10, 255)      # outer rim
EDGE_LIGHT = (58, 69, 87, 255)   # inner top highlight
CYAN = (77, 227, 208, 255)       # primary accent
CYAN_SOFT = (77, 227, 208, 90)
CYAN_DIM = (42, 140, 134, 255)
VIOLET = (139, 107, 255, 255)
CLEAR = (0, 0, 0, 0)


def lerp(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def new(w, h, fill=CLEAR):
    return Image.new("RGBA", (w, h), fill)


def vgrad(img, box, top, bottom):
    """Vertical gradient inside box (x0, y0, x1, y1) inclusive."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    span = max(1, y1 - y0)
    for y in range(y0, y1 + 1):
        d.line([(x0, y), (x1, y)], fill=lerp(top, bottom, (y - y0) / span))


def rect(img, box, fill=None, outline=None, width=1):
    """Draw a rectangle, skipping boxes that have collapsed to nothing.

    The smallest textures here are 2x2 base units, where a scaled border can
    consume the whole tile; those inner details simply drop out rather than
    raising.
    """
    x0, y0, x1, y1 = box
    if x1 < x0 or y1 < y0:
        return
    ImageDraw.Draw(img).rectangle(box, fill=fill, outline=outline, width=width)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def draw_panel(w, h, s, border, accent=True, body=SLATE_DEEP):
    """A solid panel: dark rim, lit top edge, flat stretchable body.

    `border` is the nine-slice size in base units; the fixed border band is
    border*s pixels, and everything inside it stays flat so the middle can
    stretch cleanly.
    """
    img = new(w, h, body)
    b = max(1, border * s)

    # Top band gets a soft lift so panels read as lit from above; it lives
    # entirely inside the fixed border region.
    vgrad(img, (0, 0, w - 1, b - 1), SLATE_HI, body)
    # Bottom band settles back down into shadow.
    vgrad(img, (0, h - b, w - 1, h - 1), body, (12, 14, 20, 255))

    rect(img, (0, 0, w - 1, h - 1), outline=EDGE_DARK, width=max(1, s))
    rect(img, (s, s, w - 1 - s, h - 1 - s), outline=EDGE_LIGHT, width=max(1, s // 2))
    if accent and w > 4 * s:
        # A single cyan hairline under the top rim - the signature of the set.
        y = s + max(1, s // 2)
        rect(img, (2 * s, y, w - 1 - 2 * s, y + max(0, s // 2 - 1)), fill=CYAN_DIM)
    return img


def draw_window(w, h, ns, s):
    """A titled window: header band across the fixed top border, body below.

    Used for the `dialog_background_hollow_*` family, whose nine-slice splits
    are asymmetric (a tall fixed header, a tall fixed body, and only a couple of
    stretchable pixels between them).
    """
    left, top, right, bottom = [v * s for v in ns]
    img = new(w, h, SLATE_DEEP)

    vgrad(img, (0, 0, w - 1, max(0, top - 1)), (30, 36, 49, 255), SLATE_DEEP)
    if top > 2 * s and w > 4 * s:
        # Divider closing off the header.
        rect(img, (0, top - s, w - 1, top - 1), fill=EDGE_DARK)
        rect(img, (2 * s, top - 2 * s, w - 1 - 2 * s, top - s - 1), fill=CYAN_DIM)

    vgrad(img, (0, max(top, h - max(1, bottom // 3)), w - 1, h - 1), SLATE_DEEP, (12, 14, 20, 255))
    rect(img, (0, 0, w - 1, h - 1), outline=EDGE_DARK, width=max(1, s))
    rect(img, (s, s, w - 1 - s, h - 1 - s), outline=EDGE_LIGHT, width=max(1, s // 2))
    return img


def draw_well(w, h, s, border=1, glow=None, fill=INK):
    """An inset slot: dark interior, shadowed top-left, lit bottom-right.

    `border` is the nine-slice size in base units, so `b` is the band the engine
    keeps fixed. Every bit of shading has to fit inside that band - anything
    drawn past it lands in the stretched centre and smears across the slot.
    """
    img = new(w, h, fill)
    b = max(1, border * s)
    r = max(1, b // 2)
    rect(img, (0, 0, w - 1, h - 1), outline=(3, 4, 6, 255), width=r)
    if b > r:
        # Inner shadow along top/left sells the recess.
        rect(img, (r, r, w - 1 - r, b - 1), fill=(2, 3, 5, 200))
        rect(img, (r, r, b - 1, h - 1 - r), fill=(2, 3, 5, 200))
        # Faint lift along bottom/right.
        rect(img, (r, h - b, w - 1 - r, h - 1 - r), fill=(44, 53, 68, 160))
        rect(img, (w - b, r, w - 1 - r, h - 1 - r), fill=(44, 53, 68, 160))
    if glow:
        rect(img, (0, 0, w - 1, h - 1), outline=glow, width=r)
    return img


def draw_button(w, h, s, body, top_edge, rim, accent=None):
    """A flat button face: rim, lit top edge, optional accent along the bottom.

    Buttons are nine-sliced at 1 base unit, so the rim and both edge lines share
    the same `s`-pixel band and the body stays flat for stretching.
    """
    img = new(w, h, body)
    b = max(1, s)
    r = max(1, b // 2)
    rect(img, (0, 0, w - 1, h - 1), outline=rim, width=r)
    if b > r:
        rect(img, (r, r, w - 1 - r, b - 1), fill=top_edge)
        if accent:
            rect(img, (r, h - b, w - 1 - r, h - 1 - r), fill=accent)
    return img


def draw_frame(w, h, s, color, thickness=1, inner=None):
    """A hollow frame - selection borders and slot highlights."""
    img = new(w, h)
    t = max(1, thickness * s)
    rect(img, (0, 0, w - 1, h - 1), outline=color, width=t)
    if inner:
        rect(img, (t, t, w - 1 - t, h - 1 - t), outline=inner, width=max(1, t // 2))
    return img


# ---------------------------------------------------------------------------
# Texture registry
# ---------------------------------------------------------------------------
# name -> (base_size, nineslice or None, builder)
# nineslice None means "no sidecar json"; the texture renders at native size.

def build_registry():
    reg = {}

    def ns(name, base, nineslice, fn):
        reg[name] = (base, nineslice, fn)

    def native(name, base, fn):
        reg[name] = (base, None, fn)

    # --- panels ---
    for name in ("dialog_background_opaque", "background_panel", "recipe_back_panel",
                 "header_bar_2"):
        ns(name, (16, 16), 4, lambda w, h, s: draw_panel(w, h, s, 4))
    ns("greyBorder", (16, 16), 4, lambda w, h, s: draw_frame(w, h, s, EDGE_LIGHT, 1))
    ns("tooltip_default_background", (9, 9), 4,
       lambda w, h, s: draw_panel(w, h, s, 4, accent=False, body=(14, 17, 24, 245)))
    ns("tooltip_notification_default_background", (9, 9), 4,
       lambda w, h, s: draw_panel(w, h, s, 4, accent=False, body=(16, 22, 30, 245)))
    ns("panel_outline", (4, 4), 1, lambda w, h, s: draw_frame(w, h, s, EDGE_LIGHT, 1))
    ns("default_indent", (5, 5), 1, lambda w, h, s: draw_well(w, h, s, 1))
    ns("edit_box_indent", (5, 5), 1, lambda w, h, s: draw_well(w, h, s, 1))
    # Single-line frame: at a 1-unit slice there is no room for an inner ring
    # without it landing in the stretched band.
    ns("focus_border_white", (5, 5), 1, lambda w, h, s: draw_frame(w, h, s, CYAN, 1))
    ns("square_image_border_white", (5, 5), 1,
       lambda w, h, s: draw_frame(w, h, s, EDGE_LIGHT, 1))
    ns("control", (2, 2), 1, lambda w, h, s: draw_button(w, h, s, SLATE, EDGE_LIGHT, EDGE_DARK))

    # --- hollow dialog family (asymmetric nine-slice windows) ---
    hollow = {
        "dialog_background_hollow_1": ((18, 101), [8, 23, 8, 76]),
        "dialog_background_hollow_2": ((18, 67), [8, 23, 8, 42]),
        "dialog_background_hollow_3": ((18, 33), [8, 23, 8, 8]),
        "dialog_background_hollow_5": ((18, 61), [8, 17, 8, 42]),
        "dialog_background_hollow_6": ((18, 128), [8, 23, 8, 104]),
        "dialog_background_hollow_7": ((18, 76), [8, 66, 8, 8]),
    }
    for name, (base, slices) in hollow.items():
        reg[name] = (base, slices,
                     (lambda sl: lambda w, h, s: draw_window(w, h, sl, s))(slices))
    ns("dialog_background_hollow_4", (18, 18), 8, lambda w, h, s: draw_panel(w, h, s, 8))
    ns("dialog_background_hollow_8", (42, 42), [8, 8, 33, 33],
       lambda w, h, s: draw_panel(w, h, s, 8))

    # --- buttons ---
    ns("button_borderless_light", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, SLATE, EDGE_LIGHT, EDGE_DARK))
    ns("button_borderless_lighthover", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, SLATE_HI, CYAN_DIM, CYAN, accent=CYAN_DIM))
    ns("button_borderless_lightpressed", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, (14, 17, 24, 255), EDGE_DARK, CYAN_DIM))
    ns("button_borderless_lightpressednohover", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, (14, 17, 24, 255), EDGE_DARK, EDGE_LIGHT))
    ns("button_borderless_dark", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, SLATE_DEEP, EDGE_LIGHT, EDGE_DARK))
    ns("button_borderless_darkhover", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, SLATE, CYAN_DIM, CYAN, accent=CYAN_DIM))
    ns("button_borderless_darkpressed", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, (12, 14, 20, 255), EDGE_DARK, CYAN_DIM))
    ns("button_borderless_darkpressednohover", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, (12, 14, 20, 255), EDGE_DARK, EDGE_LIGHT))
    ns("button_border_light", (4, 4), 1, lambda w, h, s: draw_frame(w, h, s, EDGE_LIGHT, 1))
    ns("button_border_dark", (4, 4), 1, lambda w, h, s: draw_frame(w, h, s, EDGE_DARK, 1))
    ns("disabledButtonNoBorder", (4, 4), 1,
       lambda w, h, s: draw_button(w, h, s, (20, 23, 30, 255), (30, 35, 45, 255),
                                   (12, 14, 20, 255)))

    # --- slots and cells ---
    ns("item_cell", (16, 16), 1, lambda w, h, s: draw_well(w, h, s, 1))
    ns("cell_image", (5, 5), 1, lambda w, h, s: draw_well(w, h, s, 1))
    ns("cell_image_normal", (5, 5), 1, lambda w, h, s: draw_well(w, h, s, 1))
    ns("slots_bg", (32, 32), 1, lambda w, h, s: draw_well(w, h, s, 1, fill=(13, 16, 22, 255)))
    ns("pocket_ui_highlight_slot", (24, 24), 4,
       lambda w, h, s: draw_frame(w, h, s, CYAN_SOFT, 2))
    ns("pocket_ui_highlight_selected_slot", (16, 16), 5,
       lambda w, h, s: draw_frame(w, h, s, CYAN, 2, inner=CYAN_SOFT))
    ns("highlight_slot", (1, 1), 1, lambda w, h, s: new(w, h, (77, 227, 208, 64)))

    # Native-size slots (no sidecar in vanilla, so no base_size to scale by).
    for name in ("slot_enabled", "slot_disabled", "slot_enabled_hover", "slot_disabled_hover"):
        hover = name.endswith("hover")
        disabled = "disabled" in name
        native(name, (18, 18), (lambda hv, ds: lambda w, h, s: draw_well(
            w, h, 1, 2,
            glow=CYAN if hv else None,
            fill=(16, 18, 24, 255) if ds else INK))(hover, disabled))
    for name in ("slot_enabled_pocket", "slot_disabled_pocket",
                 "slot_enabled_hover_pocket", "slot_disabled_hover_pocket"):
        hover = "hover" in name
        disabled = "disabled" in name
        native(name, (28, 28), (lambda hv, ds: lambda w, h, s: draw_well(
            w, h, 1, 2,
            glow=CYAN if hv else None,
            fill=(16, 18, 24, 255) if ds else INK))(hover, disabled))

    # --- hotbar ---
    for i in range(9):
        native(f"hotbar_{i}", (20, 22), lambda w, h, s: draw_well(w, h, 1, 2))
    ns("hotbar_start_cap", (1, 22), [1, 1, 1, 1], lambda w, h, s: new(w, h, EDGE_DARK))
    ns("hotbar_end_cap", (1, 22), [1, 1, 1, 1], lambda w, h, s: new(w, h, EDGE_DARK))
    native("selected_hotbar_slot", (24, 24),
           lambda w, h, s: draw_frame(w, h, 1, CYAN, 2, inner=CYAN_SOFT))

    # --- dividers ---
    ns("divider3", (1, 1), 1, lambda w, h, s: new(w, h, (58, 69, 87, 190)))
    ns("dialog_divider", (3, 1), [1, 0, 1, 0], lambda w, h, s: new(w, h, (58, 69, 87, 190)))

    return reg


def main():
    os.makedirs(OUT, exist_ok=True)
    reg = build_registry()
    for name, (base, nineslice, fn) in sorted(reg.items()):
        s = SCALE if nineslice is not None else 1
        w, h = base[0] * s, base[1] * s
        img = fn(w, h, s)
        img.save(os.path.join(OUT, name + ".png"))
        if nineslice is not None:
            with open(os.path.join(OUT, name + ".json"), "w") as f:
                json.dump({"nineslice_size": nineslice, "base_size": list(base)}, f, indent=2)
                f.write("\n")
    print(f"wrote {len(reg)} ui textures to packs/aurora_ui/textures/ui")


if __name__ == "__main__":
    main()
