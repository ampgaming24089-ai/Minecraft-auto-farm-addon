#!/usr/bin/env python3
"""Generates the Aurora Visuals shader layer.

Bedrock's Vibrant Visuals renderer is driven by JSON, not GLSL: `lighting/`,
`atmospherics/`, `color_grading/`, `water/` and `shadows/` files describe the
sun, sky scattering, tone mapping and water surface, and the engine compiles
them into its deferred pipeline. Vanilla ships a default of each plus a set of
per-climate variants, and every client biome points at one of them by
identifier.

This script emits an Aurora-styled replacement for each of those identifiers, so
enabling the pack restyles every biome in the game rather than just the default.
Overriding is by identifier, so the file names here mirror vanilla's only to
keep the folder readable.

Times are normalized 0..1 where 0.0 is noon and 0.5 is midnight; sunset lands
near 0.25 and sunrise near 0.75.
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs", "aurora_visuals")

# Vanilla ships these at differing schema versions; matching them keeps us on
# field sets the shipped client is known to parse.
FV_LIGHTING = "1.21.80"
FV_ATMOS = "1.21.40"
FV_GRADING = "1.21.90"
FV_WATER = "1.21.120"
FV_SHADOWS = "1.21.80"


def k(d):
    """Format a keyframe dict with vanilla's zero-padded time keys."""
    return {f"{float(t):.6f}": v for t, v in sorted(d.items(), key=lambda kv: float(kv[0]))}


def tint(color_keys, mul, gain=1.0):
    """Multiply every colour in a keyframe set by a per-channel factor."""
    out = {}
    for t, c in color_keys.items():
        out[t] = [max(0, min(255, int(round(c[i] * mul[i] * gain)))) for i in range(3)]
    return out


def scale(value_keys, mul):
    return {t: round(v * mul, 4) for t, v in value_keys.items()}


# --------------------------------------------------------------------------
# Overworld master curves
# --------------------------------------------------------------------------

# A brighter noon than vanilla (130 vs 100) with a longer, softer golden hour:
# the fall-off is stretched between 0.18 and 0.29 instead of dropping off a
# cliff, which is what gives the long warm evenings.
SUN_ILLUMINANCE = k({
    0.0: 130.0, 0.05: 129.0, 0.18: 96.0, 0.23: 44.0, 0.27: 7.0,
    0.288: 0.6, 0.2925: 0.0,
    0.709: 0.0, 0.716: 0.6, 0.735: 9.0, 0.775: 46.0, 0.85: 101.0,
    0.95: 129.0, 1.0: 130.0,
})

SUN_COLOR = k({
    0.0: [255, 246, 232], 0.15: [255, 238, 214], 0.20: [255, 206, 150],
    0.235: [255, 158, 74], 0.265: [255, 108, 42], 0.292: [255, 88, 46],
    0.50: [255, 105, 0],
    0.712: [255, 96, 60], 0.745: [255, 140, 70], 0.79: [255, 190, 128],
    0.86: [255, 232, 208], 1.0: [255, 246, 232],
})

# Vanilla peaks the moon at 0.4. Aurora runs it to 0.9 so nights are readable
# and directional (real moon shadows) without washing out to daylight.
MOON_ILLUMINANCE = k({
    0.0: 0.0, 0.20: 0.0, 0.228: 0.55, 0.30: 0.9, 0.50: 0.95, 0.70: 0.9,
    0.732: 0.55, 0.755: 0.0, 1.0: 0.0,
})

MOON_COLOR = k({0.0: [150, 178, 255], 0.5: [162, 190, 255], 1.0: [150, 178, 255]})

# Kept low so the directional light does the shaping; tinted by time of day so
# shadows go blue at night and warm at dusk instead of flat grey.
AMBIENT_ILLUMINANCE = k({
    0.0: 0.030, 0.25: 0.020, 0.50: 0.012, 0.75: 0.020, 1.0: 0.030,
})
AMBIENT_COLOR = k({
    0.0: [190, 212, 255], 0.26: [255, 190, 150], 0.50: [110, 140, 220],
    0.76: [255, 180, 150], 1.0: [190, 212, 255],
})

SKY_INTENSITY = 1.15
FLASH = {"illuminance": 14.0, "color": [200, 220, 255]}


def lighting(identifier, sun_mul=1.0, sun_tint=(1, 1, 1), moon_mul=1.0,
             moon_tint=(1, 1, 1), amb_mul=1.0, amb_tint=(1, 1, 1),
             sky=SKY_INTENSITY, desaturation=0.0):
    return {
        "format_version": FV_LIGHTING,
        "minecraft:lighting_settings": {
            "description": {"identifier": identifier},
            "directional_lights": {
                "orbital": {
                    "sun": {
                        "illuminance": scale(SUN_ILLUMINANCE, sun_mul),
                        "color": tint(SUN_COLOR, sun_tint),
                    },
                    "moon": {
                        "illuminance": scale(MOON_ILLUMINANCE, moon_mul),
                        "color": tint(MOON_COLOR, moon_tint),
                    },
                    "orbital_offset_degrees": 0.0,
                },
                "flash": FLASH,
            },
            "emissive": {"desaturation": desaturation},
            "ambient": {
                "illuminance": scale(AMBIENT_ILLUMINANCE, amb_mul),
                "color": tint(AMBIENT_COLOR, amb_tint),
            },
            "sky": {"intensity": sky},
        },
    }


def flat_lighting(identifier, sun_lux, sun_color, amb_lux, amb_color,
                  flash=None, desaturation=0.0, sky=1.0):
    """Lighting for dimensions with no day/night cycle (Nether, End)."""
    const = lambda v: k({0.0: v, 1.0: v})  # noqa: E731
    body = {
        "description": {"identifier": identifier},
        "directional_lights": {
            "orbital": {
                "sun": {"illuminance": const(sun_lux), "color": const(sun_color)},
                "moon": {"illuminance": const(sun_lux), "color": const(sun_color)},
                "orbital_offset_degrees": 0.0,
            },
        },
        "emissive": {"desaturation": desaturation},
        "ambient": {"illuminance": amb_lux, "color": amb_color},
        "sky": {"intensity": sky},
    }
    if flash:
        body["directional_lights"]["flash"] = flash
    return {"format_version": FV_LIGHTING, "minecraft:lighting_settings": body}


# --------------------------------------------------------------------------
# Atmospherics
# --------------------------------------------------------------------------

ZENITH = k({
    0.0: [58, 104, 180], 0.16: [52, 96, 176], 0.22: [46, 78, 152],
    0.28: [30, 44, 96], 0.36: [14, 19, 42], 0.50: [11, 15, 34],
    0.64: [14, 19, 42], 0.72: [30, 44, 96], 0.78: [46, 78, 152],
    0.86: [54, 99, 178], 1.0: [58, 104, 180],
})

HORIZON = k({
    0.0: [176, 205, 236], 0.16: [196, 210, 226], 0.20: [244, 196, 152],
    0.235: [255, 158, 96], 0.262: [246, 112, 84], 0.29: [176, 84, 106],
    0.34: [92, 70, 126], 0.40: [42, 54, 96], 0.50: [28, 38, 74],
    0.60: [42, 54, 96], 0.665: [96, 74, 132], 0.706: [186, 96, 122],
    0.738: [252, 130, 96], 0.772: [255, 178, 122], 0.812: [238, 208, 180],
    0.86: [196, 212, 230], 1.0: [176, 205, 236],
})

RAYLEIGH = k({
    0.0: 14.0, 0.14: 12.0, 0.25: 6.5, 0.33: 5.0, 0.50: 4.5, 0.64: 5.0,
    0.717: 6.5, 0.93: 12.0, 1.0: 14.0,
})

# Mie is the forward-scattered haze that makes a low sun bloom. Vanilla tops
# out at 0.75; Aurora more than doubles it, but only inside the golden hours.
SUN_MIE = k({
    0.0: 0.0, 0.16: 0.10, 0.215: 1.15, 0.25: 1.60, 0.285: 0.85, 0.32: 0.0,
    0.60: 0.0, 0.70: 0.70, 0.748: 1.60, 0.79: 1.05, 0.85: 0.10, 1.0: 0.0,
})
MOON_MIE = k({0.0: 0.0, 0.22: 0.0, 0.30: 0.28, 0.50: 0.32, 0.70: 0.28, 0.76: 0.0, 1.0: 0.0})
SUN_GLARE = k({
    0.0: 0.0, 0.17: 0.01, 0.22: 0.10, 0.25: 0.145, 0.29: 0.07, 0.33: 0.0,
    0.62: 0.0, 0.71: 0.06, 0.748: 0.145, 0.79: 0.09, 0.84: 0.01, 1.0: 0.0,
})

HORIZON_BLEND = {
    "min": k({0.0: 0.0, 1.0: 0.0}),
    "start": k({0.0: 0.85, 0.25: 0.52, 0.30: 0.26, 0.75: 0.26, 0.83: 0.52, 1.0: 0.85}),
    "mie_start": k({0.0: 0.48, 0.10: 0.48, 0.20: 1.0, 0.30: 0.85, 0.50: 0.5,
                    0.70: 0.85, 0.80: 1.0, 0.90: 0.48, 1.0: 0.48}),
    "max": k({0.0: 0.27, 1.0: 0.27}),
}


def atmospherics(identifier, zen_tint=(1, 1, 1), hor_tint=(1, 1, 1),
                 rayleigh_mul=1.0, mie_mul=1.0, glare_mul=1.0):
    return {
        "format_version": FV_ATMOS,
        "minecraft:atmosphere_settings": {
            "description": {"identifier": identifier},
            "horizon_blend_stops": HORIZON_BLEND,
            "rayleigh_strength": scale(RAYLEIGH, rayleigh_mul),
            "sun_mie_strength": scale(SUN_MIE, mie_mul),
            "moon_mie_strength": scale(MOON_MIE, mie_mul),
            "sun_glare_shape": scale(SUN_GLARE, glare_mul),
            "sky_zenith_color": tint(ZENITH, zen_tint),
            "sky_horizon_color": tint(HORIZON, hor_tint),
        },
    }


def flat_atmospherics(identifier, zenith, horizon, rayleigh, mie=0.0,
                      glare=0.0, blend=None):
    """Atmospherics for skies with no day cycle."""
    const = lambda v: k({0.0: v, 1.0: v})  # noqa: E731
    return {
        "format_version": FV_ATMOS,
        "minecraft:atmosphere_settings": {
            "description": {"identifier": identifier},
            "sky_zenith_color": const(zenith),
            "sky_horizon_color": const(horizon),
            "horizon_blend_stops": blend or {
                "min": 0.0, "start": 0.85, "mie_start": 0.5, "max": 1.0},
            "rayleigh_strength": const(rayleigh),
            "sun_mie_strength": const(mie),
            "moon_mie_strength": const(0.0),
            "sun_glare_shape": const(glare),
        },
    }


# --------------------------------------------------------------------------
# Colour grading
# --------------------------------------------------------------------------

def grading(identifier, contrast=1.22, saturation=1.14, temperature=6350,
            gain=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0),
            shadow_sat=0.92, shadow_gain=(0.96, 0.98, 1.05),
            highlight_gain=(1.03, 1.01, 0.98), operator="hable"):
    return {
        "format_version": FV_GRADING,
        "minecraft:color_grading_settings": {
            "description": {"identifier": identifier},
            "color_grading": {
                "midtones": {
                    "contrast": [contrast] * 3,
                    "gain": list(gain),
                    "gamma": [2.2, 2.2, 2.2],
                    "offset": list(offset),
                    "saturation": [saturation] * 3,
                },
                # Cool, slightly desaturated shadows against warm highlights is
                # the classic teal/orange split that reads as "cinematic".
                "shadows": {
                    "enabled": True,
                    "shadowsMax": 0.36,
                    "contrast": [1.05, 1.05, 1.05],
                    "gain": list(shadow_gain),
                    "gamma": [2.2, 2.2, 2.2],
                    "offset": [-0.004, -0.002, 0.008],
                    "saturation": [shadow_sat] * 3,
                },
                "highlights": {
                    "enabled": True,
                    "highlightsMin": 1.05,
                    "contrast": [1.0, 1.0, 1.0],
                    "gain": list(highlight_gain),
                    "gamma": [2.2, 2.2, 2.2],
                    "offset": [0.0, 0.0, 0.0],
                    "saturation": [0.95, 0.95, 0.95],
                },
                "temperature": {
                    "enabled": True,
                    "temperature": temperature,
                    "type": "color_temperature",
                },
            },
            "tone_mapping": {"operator": operator},
        },
    }


# --------------------------------------------------------------------------
# Per-biome looks
# --------------------------------------------------------------------------

LIGHTING_LOOKS = {
    "global.json": ("minecraft:default_lighting", {}),
    "warmish_lighting.json": ("minecraft:warmish_lighting", dict(
        sun_mul=1.02, sun_tint=(1.0, 0.995, 0.97))),
    "coolish_lighting.json": ("minecraft:coolish_lighting", dict(
        sun_tint=(0.98, 0.995, 1.03), amb_tint=(0.96, 1.0, 1.06))),
    "cold_lighting.json": ("minecraft:cold_lighting", dict(
        sun_mul=0.94, sun_tint=(0.95, 0.985, 1.06), moon_mul=1.1,
        amb_tint=(0.92, 0.98, 1.10))),
    "ice_plains_spikes_lighting.json": ("minecraft:ice_plains_spikes_lighting", dict(
        sun_mul=1.10, sun_tint=(0.94, 0.98, 1.09), moon_mul=1.25,
        amb_mul=1.25, amb_tint=(0.90, 0.97, 1.14), sky=1.30)),
    "hot_lighting.json": ("minecraft:hot_lighting", dict(
        sun_mul=1.12, sun_tint=(1.0, 0.975, 0.92), amb_tint=(1.03, 1.0, 0.95))),
    "desert_lighting.json": ("minecraft:desert_lighting", dict(
        sun_mul=1.24, sun_tint=(1.0, 0.965, 0.88), amb_mul=1.30,
        amb_tint=(1.08, 1.0, 0.88), sky=1.05)),
    "mesa_lighting.json": ("minecraft:mesa_lighting", dict(
        sun_mul=1.16, sun_tint=(1.0, 0.94, 0.82), amb_mul=1.20,
        amb_tint=(1.10, 0.97, 0.84), sky=1.02)),
    "swampland_lighting.json": ("minecraft:swampland_lighting", dict(
        sun_mul=0.82, sun_tint=(0.96, 1.0, 0.90), amb_mul=1.05,
        amb_tint=(0.92, 1.02, 0.90), sky=0.92)),
    "mangrove_swamp_lighting.json": ("minecraft:mangrove_swamp_lighting", dict(
        sun_mul=0.88, sun_tint=(1.0, 0.98, 0.88), amb_mul=1.05,
        amb_tint=(0.95, 1.02, 0.94), sky=0.95)),
    "roofed_forest_lighting.json": ("minecraft:roofed_forest_lighting", dict(
        sun_mul=0.74, sun_tint=(0.95, 1.0, 0.93), amb_mul=0.85,
        amb_tint=(0.90, 1.0, 0.92), sky=0.85)),
    "pale_garden_lighting.json": ("minecraft:pale_garden_lighting", dict(
        sun_mul=0.70, sun_tint=(0.97, 1.0, 1.02), moon_mul=1.15, amb_mul=0.90,
        amb_tint=(0.97, 1.0, 1.03), sky=0.80, desaturation=0.35)),
    "mushroom_island_lighting.json": ("minecraft:mushroom_island_lighting", dict(
        sun_mul=0.96, sun_tint=(1.0, 0.96, 1.04), moon_mul=1.2, amb_mul=1.15,
        amb_tint=(1.06, 0.94, 1.10), sky=1.05)),
}

FLAT_LIGHTING = {
    "nether_lighting.json": dict(
        identifier="minecraft:nether_lighting", sun_lux=100.0,
        sun_color=[255, 176, 132], amb_lux=0.55, amb_color=[255, 138, 96],
        desaturation=0.0, sky=0.9),
    "end_lighting.json": dict(
        identifier="minecraft:end_lighting", sun_lux=100.0,
        sun_color=[214, 200, 255], amb_lux=0.14, amb_color=[150, 130, 210],
        flash={"illuminance": 4.0, "color": [228, 93, 255]}, sky=1.0),
}

ATMOS_LOOKS = {
    "atmospherics.json": ("minecraft:default_atmospherics", {}),
    "warmish_atmospherics.json": ("minecraft:warmish_atmospherics", dict(
        hor_tint=(1.02, 1.0, 0.97))),
    "hot_atmospherics.json": ("minecraft:hot_atmospherics", dict(
        zen_tint=(1.0, 0.98, 0.95), hor_tint=(1.05, 1.0, 0.92),
        rayleigh_mul=0.85, mie_mul=1.15)),
    "desert_atmospherics.json": ("minecraft:desert_atmospherics", dict(
        zen_tint=(1.02, 0.98, 0.90), hor_tint=(1.08, 1.0, 0.84),
        rayleigh_mul=0.68, mie_mul=1.35, glare_mul=1.2)),
    "mesa_atmospherics.json": ("minecraft:mesa_atmospherics", dict(
        zen_tint=(1.05, 0.96, 0.86), hor_tint=(1.12, 0.96, 0.80),
        rayleigh_mul=0.72, mie_mul=1.40, glare_mul=1.15)),
    "ice_plains_spikes_atmospherics.json": ("minecraft:ice_plains_spikes_atmospherics", dict(
        zen_tint=(0.92, 0.98, 1.12), hor_tint=(0.94, 0.99, 1.10),
        rayleigh_mul=1.30, mie_mul=0.85)),
    "swampland_atmospherics.json": ("minecraft:swampland_atmospherics", dict(
        zen_tint=(0.94, 1.0, 0.92), hor_tint=(0.95, 1.0, 0.90),
        rayleigh_mul=1.10, mie_mul=1.10)),
    "mangrove_swamp_atmospherics.json": ("minecraft:mangrove_swamp_atmospherics", dict(
        zen_tint=(0.96, 1.0, 0.94), hor_tint=(1.02, 0.99, 0.90),
        rayleigh_mul=1.05, mie_mul=1.20)),
    "roofed_forest_atmospherics.json": ("minecraft:roofed_forest_atmospherics", dict(
        zen_tint=(0.90, 0.97, 0.93), hor_tint=(0.90, 0.97, 0.92),
        rayleigh_mul=1.15, mie_mul=0.95)),
    "pale_garden_atmospherics.json": ("minecraft:pale_garden_atmospherics", dict(
        zen_tint=(0.94, 0.97, 1.0), hor_tint=(0.95, 0.97, 1.0),
        rayleigh_mul=1.20, mie_mul=0.70, glare_mul=0.6)),
    "mushroom_island_atmospherics.json": ("minecraft:mushroom_island_atmospherics", dict(
        zen_tint=(1.04, 0.94, 1.10), hor_tint=(1.08, 0.94, 1.08),
        rayleigh_mul=1.05, mie_mul=1.25)),
}

FLAT_ATMOS = {
    "hell_atmospherics.json": dict(
        identifier="minecraft:hell_atmospherics", zenith=[74, 14, 12],
        horizon=[122, 28, 16], rayleigh=0.35, mie=0.55, glare=0.05,
        blend={"min": 0.0, "start": 0.80, "mie_start": 0.5, "max": 1.0}),
    "crimson_forest_atmospherics.json": dict(
        identifier="minecraft:crimson_forest_atmospherics", zenith=[86, 16, 20],
        horizon=[140, 34, 30], rayleigh=0.40, mie=0.60, glare=0.05,
        blend={"min": 0.0, "start": 0.80, "mie_start": 0.5, "max": 1.0}),
    "warped_forest_atmospherics.json": dict(
        identifier="minecraft:warped_forest_atmospherics", zenith=[10, 52, 60],
        horizon=[18, 88, 92], rayleigh=0.45, mie=0.50, glare=0.05,
        blend={"min": 0.0, "start": 0.80, "mie_start": 0.5, "max": 1.0}),
    "soulsand_valley_atmospherics.json": dict(
        identifier="minecraft:soulsand_valley_atmospherics", zenith=[14, 42, 56],
        horizon=[28, 76, 92], rayleigh=0.50, mie=0.45, glare=0.04,
        blend={"min": 0.0, "start": 0.80, "mie_start": 0.5, "max": 1.0}),
    "basalt_deltas_atmospherics.json": dict(
        identifier="minecraft:basalt_deltas_atmospherics", zenith=[34, 30, 32],
        horizon=[62, 54, 56], rayleigh=0.30, mie=0.40, glare=0.03,
        blend={"min": 0.0, "start": 0.80, "mie_start": 0.5, "max": 1.0}),
    "end_atmospherics.json": dict(
        identifier="minecraft:end_atmospherics", zenith=[30, 22, 52],
        horizon=[6, 4, 14], rayleigh=46.0, mie=0.0, glare=0.0,
        blend={"min": 0.0, "start": 1.0, "mie_start": 0.5, "max": 0.25}),
}

GRADING_LOOKS = {
    "color_grading.json": ("minecraft:default_color_grading", {}),
    "warmish_color_grading.json": ("minecraft:warmish_color_grading", dict(
        temperature=6200, saturation=1.16)),
    "coolish_color_grading.json": ("minecraft:coolish_color_grading", dict(
        temperature=6800, saturation=1.12)),
    "cold_color_grading.json": ("minecraft:cold_color_grading", dict(
        temperature=7400, saturation=1.08, contrast=1.24)),
    "ice_plains_spikes_color_grading.json": ("minecraft:ice_plains_spikes_color_grading", dict(
        temperature=7900, saturation=1.05, contrast=1.28,
        highlight_gain=(0.99, 1.01, 1.05))),
    "hot_color_grading.json": ("minecraft:hot_color_grading", dict(
        temperature=5900, saturation=1.18)),
    "desert_color_grading.json": ("minecraft:desert_color_grading", dict(
        temperature=5500, saturation=1.12, contrast=1.26,
        highlight_gain=(1.05, 1.01, 0.94))),
    "mesa_color_grading.json": ("minecraft:mesa_color_grading", dict(
        temperature=5200, saturation=1.22, contrast=1.26,
        highlight_gain=(1.07, 1.0, 0.92))),
    "swampland_color_grading.json": ("minecraft:swampland_color_grading", dict(
        temperature=6900, saturation=1.06, contrast=1.18,
        gain=(0.97, 1.02, 0.97))),
    "mangrove_swamp_color_grading.json": ("minecraft:mangrove_swamp_color_grading", dict(
        temperature=6300, saturation=1.14, gain=(1.0, 1.01, 0.97))),
    "roofed_forest_color_grading.json": ("minecraft:roofed_forest_color_grading", dict(
        temperature=6700, saturation=1.10, contrast=1.28,
        gain=(0.96, 1.0, 0.96))),
    "pale_garden_color_grading.json": ("minecraft:pale_garden_color_grading", dict(
        temperature=7200, saturation=0.55, contrast=1.30,
        shadow_sat=0.55, highlight_gain=(1.0, 1.0, 1.02))),
    "mushroom_island_color_grading.json": ("minecraft:mushroom_island_color_grading", dict(
        temperature=6600, saturation=1.30, gain=(1.03, 0.98, 1.05))),
    "lush_caves_color_grading.json": ("minecraft:lush_caves_color_grading", dict(
        temperature=5000, saturation=1.24, contrast=1.30,
        gain=(0.99, 1.03, 0.99))),
}


def water():
    return {
        "format_version": FV_WATER,
        "minecraft:water_settings": {
            "description": {"identifier": "minecraft:default_water"},
            # Real water gets its colour from what is dissolved in it. A little
            # chlorophyll and CDOM turns flat blue into a deep teal that darkens
            # convincingly with depth.
            "particle_concentrations": {
                "chlorophyll": 0.55,
                "suspended_sediment": 0.35,
                "cdom": 0.5,
            },
            "waves": {
                "enabled": True,
                "depth": 1.0,
                "direction_increment": 80.0,
                "frequency": 1.0,
                "frequency_scaling": 1.2,
                "mix": 0.28,
                "octaves": 28,
                "pull": 0.38,
                "sampleWidth": 0.02,
                "shape": 1.5,
                "speed": 1.6,
                "speed_scaling": 1.03,
            },
            "caustics": {
                "enabled": True,
                "frame_length": 0.07,
                "power": 2,
                "scale": 0.55,
            },
            "biome_water_color_contribution": 0.35,
        },
    }


def shadows():
    return {
        "format_version": FV_SHADOWS,
        "minecraft:shadow_settings": {
            "shadow_style": "soft_shadows",
            "texel_size": 16,
        },
    }


def write(rel, data):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return rel


def main():
    written = []
    for name, (ident, kw) in LIGHTING_LOOKS.items():
        written.append(write(f"lighting/{name}", lighting(ident, **kw)))
    for name, kw in FLAT_LIGHTING.items():
        written.append(write(f"lighting/{name}", flat_lighting(**kw)))

    for name, (ident, kw) in ATMOS_LOOKS.items():
        written.append(write(f"atmospherics/{name}", atmospherics(ident, **kw)))
    for name, kw in FLAT_ATMOS.items():
        written.append(write(f"atmospherics/{name}", flat_atmospherics(**kw)))

    for name, (ident, kw) in GRADING_LOOKS.items():
        written.append(write(f"color_grading/{name}", grading(ident, **kw)))

    written.append(write("water/water.json", water()))
    written.append(write("shadows/global.json", shadows()))

    print(f"wrote {len(written)} visual files")
    for w in written:
        print("  ", w)


if __name__ == "__main__":
    main()
