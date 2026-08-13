#!/usr/bin/env python3
"""Validates the Aurora packs against the vanilla resource pack.

Overriding in Bedrock is absolute: an animation identifier defined here fully
replaces the vanilla one, and a texture path fully replaces the vanilla file. So
the two ways to break something silently are:

* declaring an identifier or texture vanilla does not have (a dead override that
  simply never applies), and
* dropping a bone the vanilla animation used (that motion is now gone).

Both are checked here, along with strict JSON parsing and range checks on the
Vibrant Visuals settings.

Point VANILLA at a checkout of https://github.com/Mojang/bedrock-samples, or set
the BEDROCK_SAMPLES environment variable. Without it, the vanilla cross-checks
are skipped and only the self-contained checks run.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PACKS = os.path.join(ROOT, "packs")
VANILLA = os.environ.get("BEDROCK_SAMPLES", "")

errors = []
warnings = []
checked = 0


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load_jsonc(path):
    """Vanilla files carry comments and trailing commas; ours must not."""
    try:
        import json5
        return json5.load(open(path))
    except ImportError:
        return json.load(open(path))


def all_json_files():
    for dirpath, _, names in os.walk(PACKS):
        for n in names:
            if n.endswith(".json"):
                yield os.path.join(dirpath, n)


# ---------------------------------------------------------------------------
# 1. Every file we ship must be strict, comment-free JSON.
# ---------------------------------------------------------------------------
def check_strict_json():
    global checked
    for path in all_json_files():
        rel = os.path.relpath(path, ROOT)
        try:
            json.load(open(path))
            checked += 1
        except Exception as e:
            err(f"{rel}: invalid JSON - {e}")


# ---------------------------------------------------------------------------
# 2. Manifests
# ---------------------------------------------------------------------------
def check_manifests():
    seen = {}
    for pack in sorted(os.listdir(PACKS)):
        mpath = os.path.join(PACKS, pack, "manifest.json")
        if not os.path.exists(mpath):
            err(f"packs/{pack}: no manifest.json")
            continue
        m = json.load(open(mpath))
        uuids = [m["header"]["uuid"]] + [mod["uuid"] for mod in m["modules"]]
        for u in uuids:
            if u in seen:
                err(f"packs/{pack}: UUID {u} already used by {seen[u]}")
            seen[u] = pack
        if m["header"]["min_engine_version"] < [1, 21, 120]:
            err(f"packs/{pack}: min_engine_version below 1.21.120")
        if not os.path.exists(os.path.join(PACKS, pack, "pack_icon.png")):
            err(f"packs/{pack}: missing pack_icon.png")


# ---------------------------------------------------------------------------
# 3. Vibrant Visuals ranges
# ---------------------------------------------------------------------------
GRADING_RANGES = {
    "contrast": (0.0, 4.0), "gain": (0.0, 10.0), "gamma": (0.0, 4.0),
    "offset": (-1.0, 1.0), "saturation": (0.0, 10.0),
}


def check_visuals():
    vis = os.path.join(PACKS, "aurora_visuals")
    if not os.path.isdir(vis):
        return

    for name in os.listdir(os.path.join(vis, "color_grading")):
        path = os.path.join(vis, "color_grading", name)
        cg = json.load(open(path))["minecraft:color_grading_settings"]
        for section, body in cg.get("color_grading", {}).items():
            if section == "temperature":
                t = body.get("temperature")
                if t is not None and not (1000.0 <= t <= 15000.0):
                    err(f"color_grading/{name}: temperature {t} out of range")
                continue
            for field, (lo, hi) in GRADING_RANGES.items():
                if field not in body:
                    continue
                for v in body[field]:
                    if not (lo <= v <= hi):
                        err(f"color_grading/{name}: {section}.{field} {v} out of [{lo},{hi}]")
        if "shadows" in cg.get("color_grading", {}):
            sm = cg["color_grading"]["shadows"].get("shadowsMax")
            if sm is not None and not (0.1 <= sm <= 1.0):
                err(f"color_grading/{name}: shadowsMax {sm} out of range")
        if "highlights" in cg.get("color_grading", {}):
            hm = cg["color_grading"]["highlights"].get("highlightsMin")
            if hm is not None and not (1.0 <= hm <= 4.0):
                err(f"color_grading/{name}: highlightsMin {hm} out of range")
        op = cg.get("tone_mapping", {}).get("operator")
        if op and op not in ("reinhard", "reinhard_luma", "reinhard_luminance",
                             "hable", "aces", "generic"):
            err(f"color_grading/{name}: unknown tone mapping operator {op!r}")

    wpath = os.path.join(vis, "water", "water.json")
    if os.path.exists(wpath):
        w = json.load(open(wpath))["minecraft:water_settings"]
        limits = {"cdom": (0.0, 15.0), "chlorophyll": (0.0, 10.0),
                  "suspended_sediment": (0.0, 300.0)}
        for field, (lo, hi) in limits.items():
            v = w.get("particle_concentrations", {}).get(field)
            if v is not None and not (lo <= v <= hi):
                err(f"water/water.json: {field} {v} out of [{lo},{hi}]")
        waves = w.get("waves", {})
        wave_limits = {"depth": (0.0, 3.0), "direction_increment": (0.0, 360.0),
                       "frequency": (0.01, 3.0), "frequency_scaling": (0.0, 2.0),
                       "mix": (0.0, 1.0), "octaves": (1, 30), "pull": (-1.0, 1.0),
                       "sampleWidth": (0.01, 1.0), "shape": (1.0, 10.0),
                       "speed": (0.01, 10.0), "speed_scaling": (0.0, 2.0)}
        for field, (lo, hi) in wave_limits.items():
            v = waves.get(field)
            if v is not None and not (lo <= v <= hi):
                err(f"water/water.json: waves.{field} {v} out of [{lo},{hi}]")
        caustics = w.get("caustics", {})
        if "power" in caustics and not (1 <= caustics["power"] <= 6):
            err(f"water/water.json: caustics.power out of [1,6]")
        if "frame_length" in caustics and not (0.01 <= caustics["frame_length"] <= 5.0):
            err(f"water/water.json: caustics.frame_length out of [0.01,5.0]")

    spath = os.path.join(vis, "shadows", "global.json")
    if os.path.exists(spath):
        s = json.load(open(spath))["minecraft:shadow_settings"]
        if s.get("shadow_style") not in ("blocky_shadows", "soft_shadows"):
            err("shadows/global.json: invalid shadow_style")


# ---------------------------------------------------------------------------
# 4. Cross-checks against the vanilla pack
# ---------------------------------------------------------------------------
def vanilla_animations():
    """identifier -> set of bones, across the whole vanilla animations folder."""
    out = {}
    adir = os.path.join(VANILLA, "resource_pack", "animations")
    for name in os.listdir(adir):
        if not name.endswith(".json"):
            continue
        try:
            d = load_jsonc(os.path.join(adir, name))
        except Exception:
            continue
        for ident, body in (d.get("animations") or {}).items():
            out[ident] = set((body.get("bones") or {}).keys())
    return out


def check_against_vanilla():
    if not VANILLA or not os.path.isdir(os.path.join(VANILLA, "resource_pack")):
        warn("vanilla pack not found - skipping override cross-checks "
             "(set BEDROCK_SAMPLES to a bedrock-samples checkout)")
        return

    # --- animations ---
    van = vanilla_animations()
    adir = os.path.join(PACKS, "aurora_animations", "animations")
    if os.path.isdir(adir):
        for name in sorted(os.listdir(adir)):
            d = json.load(open(os.path.join(adir, name)))
            for ident, body in d["animations"].items():
                if ident not in van:
                    err(f"animations/{name}: '{ident}' is not a vanilla "
                        f"animation - this override will never apply")
                    continue
                mine = set((body.get("bones") or {}).keys())
                dropped = van[ident] - mine
                if dropped:
                    err(f"animations/{name}: '{ident}' drops vanilla bone(s) "
                        f"{sorted(dropped)} - that motion would be lost")

    # --- ui textures ---
    vtex = os.path.join(VANILLA, "resource_pack", "textures", "ui")
    mtex = os.path.join(PACKS, "aurora_ui", "textures", "ui")
    if os.path.isdir(mtex) and os.path.isdir(vtex):
        vanilla_pngs = {f[:-4] for f in os.listdir(vtex) if f.endswith(".png")}
        for f in sorted(os.listdir(mtex)):
            if not f.endswith(".png"):
                continue
            stem = f[:-4]
            if stem not in vanilla_pngs:
                err(f"textures/ui/{f}: no vanilla texture with this name")
                continue
            vj = os.path.exists(os.path.join(vtex, stem + ".json"))
            mj = os.path.exists(os.path.join(mtex, stem + ".json"))
            if vj != mj:
                err(f"textures/ui/{stem}: sidecar json mismatch "
                    f"(vanilla={vj}, ours={mj})")

    # --- ui variables ---
    gv = os.path.join(PACKS, "aurora_ui", "ui", "_global_variables.json")
    vgv = os.path.join(VANILLA, "resource_pack", "ui", "_global_variables.json")
    if os.path.exists(gv) and os.path.exists(vgv):
        vanilla_vars = load_jsonc(vgv)
        for k in json.load(open(gv)):
            if k not in vanilla_vars:
                err(f"ui/_global_variables.json: '{k}' is not a vanilla variable")

    # --- visual settings identifiers ---
    folders = [("lighting", "minecraft:lighting_settings"),
               ("atmospherics", "minecraft:atmosphere_settings"),
               ("color_grading", "minecraft:color_grading_settings"),
               ("water", "minecraft:water_settings")]
    for folder, key in folders:
        vdir = os.path.join(VANILLA, "resource_pack", folder)
        mdir = os.path.join(PACKS, "aurora_visuals", folder)
        if not (os.path.isdir(vdir) and os.path.isdir(mdir)):
            continue
        vids = set()
        for n in os.listdir(vdir):
            if n.endswith(".json"):
                vids.add(load_jsonc(os.path.join(vdir, n))[key]["description"]["identifier"])
        mids = set()
        for n in os.listdir(mdir):
            if n.endswith(".json"):
                mids.add(json.load(open(os.path.join(mdir, n)))[key]["description"]["identifier"])
        for extra in sorted(mids - vids):
            err(f"{folder}: '{extra}' is not a vanilla identifier")
        for missing in sorted(vids - mids):
            warn(f"{folder}: vanilla '{missing}' left unstyled")


def main():
    check_strict_json()
    check_manifests()
    check_visuals()
    check_against_vanilla()

    for w in warnings:
        print(f"  warn: {w}")
    for e in errors:
        print(f" ERROR: {e}")
    print(f"\n{checked} JSON files parsed, {len(errors)} error(s), "
          f"{len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
