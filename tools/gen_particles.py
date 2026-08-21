#!/usr/bin/env python3
"""Impact and ambient particles for the mob roster.

A swing that lands with no particle reads as a swing that missed. Each mob
gets a signature burst on impact - obsidian throws sparks, the slime throws
gobbets, the wisp throws cold motes - and the airborne ones get a slow trail
so they are visible against the sky before they are close enough to identify.

The particle atlas is a 64x64 sheet of four 16x16 cells, so each effect names
a cell rather than shipping its own texture.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "RP", "particles")

SPARK, MOTE, SHARD, SMOKE = (16, 0), (0, 0), (0, 16), (16, 16)


def burst(name, cell, colours, count=26, speed=(2.5, 5.0), gravity=-2.4,
          size=0.11, life=(0.3, 0.7), radius=0.4):
    """A one-shot puff at a point: the impact effects."""
    early, mid, late = colours
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {
                "identifier": "voidbound:" + name,
                "basic_render_parameters": {
                    "material": "particles_alpha",
                    "texture": "textures/particle/voidbound_particles",
                },
            },
            "components": {
                "minecraft:emitter_lifetime_once": {"active_time": 0.2},
                "minecraft:emitter_rate_instant": {"num_particles": count},
                "minecraft:emitter_shape_sphere": {
                    "radius": radius, "sample_surface": True,
                    "direction": "outwards"},
                "minecraft:particle_lifetime_expression": {
                    "max_lifetime": "Math.random(%s, %s)" % life},
                "minecraft:particle_initial_speed": "Math.random(%s, %s)" % speed,
                "minecraft:particle_motion_dynamic": {
                    "linear_acceleration": [0, gravity, 0],
                    "linear_drag_coefficient": 2.4},
                "minecraft:particle_appearance_billboard": {
                    "size": [size, size],
                    "facing_camera_mode": "rotate_xyz",
                    "uv": {"texture_width": 64, "texture_height": 64,
                           "uv": list(cell), "uv_size": [16, 16]}},
                "minecraft:particle_appearance_tinting": {
                    "color": {
                        "gradient": {"0.0": early, "0.4": mid, "1.0": late},
                        "interpolant": ("variable.particle_age / "
                                        "variable.particle_lifetime")}},
            },
        },
    }


def trail(name, cell, colours, rate=6, size=0.13, life=(0.8, 1.6),
          drift=0.35, rise=0.4):
    """A slow continuous trail: what an airborne mob leaves behind it."""
    early, mid, late = colours
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {
                "identifier": "voidbound:" + name,
                "basic_render_parameters": {
                    "material": "particles_alpha",
                    "texture": "textures/particle/voidbound_particles",
                },
            },
            "components": {
                "minecraft:emitter_lifetime_once": {"active_time": 1.0},
                "minecraft:emitter_rate_steady": {
                    "spawn_rate": rate, "max_particles": rate * 2},
                "minecraft:emitter_shape_sphere": {
                    "radius": 0.7, "sample_surface": False,
                    "direction": "outwards"},
                "minecraft:particle_lifetime_expression": {
                    "max_lifetime": "Math.random(%s, %s)" % life},
                "minecraft:particle_initial_speed": drift,
                "minecraft:particle_motion_dynamic": {
                    "linear_acceleration": [0, rise, 0],
                    "linear_drag_coefficient": 1.4},
                "minecraft:particle_appearance_billboard": {
                    "size": [size, size],
                    "facing_camera_mode": "rotate_xyz",
                    "uv": {"texture_width": 64, "texture_height": 64,
                           "uv": list(cell), "uv_size": [16, 16]}},
                "minecraft:particle_appearance_tinting": {
                    "color": {
                        "gradient": {"0.0": early, "0.5": mid, "1.0": late},
                        "interpolant": ("variable.particle_age / "
                                        "variable.particle_lifetime")}},
            },
        },
    }


WHITE = [1.0, 1.0, 1.0, 1.0]

EFFECTS = {
    # Impacts.
    "hit_void": burst("hit_void", MOTE,
                      (WHITE, [0.78, 0.25, 1.0, 0.95], [0.20, 0.04, 0.34, 0.0])),
    "hit_ember": burst("hit_ember", SPARK,
                       (WHITE, [1.0, 0.48, 0.18, 0.95], [0.34, 0.06, 0.04, 0.0]),
                       count=32, speed=(3.0, 6.5), gravity=-4.0, size=0.09),
    "hit_frost": burst("hit_frost", SHARD,
                       (WHITE, [0.36, 0.91, 1.0, 0.9], [0.06, 0.24, 0.40, 0.0]),
                       gravity=-1.2, life=(0.5, 1.1)),
    "hit_chitin": burst("hit_chitin", SHARD,
                        (WHITE, [0.65, 0.30, 0.86, 0.95], [0.16, 0.06, 0.26, 0.0]),
                        count=20, gravity=-5.0, size=0.10),
    "hit_slime": burst("hit_slime", MOTE,
                       ([0.85, 0.55, 1.0, 1.0], [0.55, 0.20, 0.80, 0.85],
                        [0.14, 0.05, 0.22, 0.0]),
                       count=18, speed=(1.4, 3.0), gravity=-6.0, size=0.17),
    "hit_stone": burst("hit_stone", SMOKE,
                       ([0.80, 0.76, 0.62, 1.0], [0.52, 0.44, 0.56, 0.85],
                        [0.16, 0.13, 0.22, 0.0]),
                       count=22, gravity=-5.5, size=0.13),
    # Trails.
    "trail_astral": trail("trail_astral", MOTE,
                          (WHITE, [1.0, 0.78, 0.35, 0.8], [0.30, 0.16, 0.06, 0.0]),
                          rate=5, size=0.15, rise=0.15),
    "trail_cold": trail("trail_cold", MOTE,
                        (WHITE, [0.49, 0.95, 1.0, 0.75], [0.06, 0.22, 0.34, 0.0]),
                        rate=7, size=0.11, rise=0.5),
    "trail_void": trail("trail_void", MOTE,
                        ([0.95, 0.55, 1.0, 0.9], [0.62, 0.24, 0.90, 0.7],
                         [0.12, 0.03, 0.22, 0.0]),
                        rate=6, size=0.12, rise=0.3),
}


def main():
    for name, effect in EFFECTS.items():
        with open(os.path.join(OUT, name + ".json"), "w") as handle:
            json.dump(effect, handle, indent=2)
            handle.write("\n")
    print("%d particle effects" % len(EFFECTS))


if __name__ == "__main__":
    main()
