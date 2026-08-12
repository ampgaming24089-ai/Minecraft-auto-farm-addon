# Working rules for this repo

Standing instructions from the pack's owner. These apply to **every** change,
not just the one that prompted them.

## 1. Rename the pack on every single delivery

Every build that goes to a device gets a **brand-new name and a fresh set of
five UUIDs**. Not a version bump on the old name — a different name.

Why: Minecraft refuses an import that collides with a pack already installed
("Duplicate pack detected"), and it has bitten this project more than once.
A new identity every time means the owner can always import the new build
alongside whatever is already on the device and pick it out of the list.

The rule for the name: **two words, the first always `Hallowed`.** The second
word must be one that has not been used before. Used so far, oldest first:

    Hallowed Depths, Hallow Dimension, Hallow Dimension v2, Hallowed Veil,
    Hallowed Reaches, Hallowed Requiem, Hallowed Covenant, Hallowed Expanse,
    Hallowed Reliquary, Hallowed Sanctum, Hallowed Threshold,
    Hallowed Vigil, Hallowed Ossuary

The checklist for a rename (all five UUIDs are regenerated, never reused):

    BP/manifest.json   header.uuid, header.name, header.description,
                       modules[data].uuid, modules[script].uuid,
                       dependencies[0].uuid  -> the RP header
    RP/manifest.json   header.uuid, header.name, header.description,
                       modules[resources].uuid,
                       dependencies[0].uuid  -> the BP header
    both texts/en_US.lang    pack.name, pack.description
    build_addon.sh           NAME=
    README.md                the title and any prose naming the pack
    tools/validate.py        add the five retired UUIDs to RETIRED

`tools/validate.py` fails the build if any retired UUID reappears, so the
retirement list is not optional bookkeeping — it is the enforcement.

## 2. Nothing ships on a guess

Every schema shape, component name, event name and API signature is checked
against Mojang's `bedrock-samples` before it is used:

    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
        https://github.com/Mojang/bedrock-samples /workspace/mojang/bedrock-samples

`tools/validate.py` gates `./build_addon.sh` and must pass. Each check in it
exists because a real device test caught the bug it looks for; when a new bug
is found, the fix is a check that is **verified to fire on the real defect
before the defect is fixed**.

## 3. `format_version` selects a parser

A file's declared `format_version` decides which parser the engine uses, so
"valid in the newest schema" says nothing about a file declaring an older
version. Three separate regressions shipped from ignoring this. The snapshot
in `tools/schema/vanilla_components.json` records which version introduced
each component and field; use it.

## 4. Balance lives in one file

`tools/balance.py` is the single source of truth for every weapon and armour
number. Change stats there and re-run it — never hand-edit an item's damage,
protection, durability or enchantability.

## 5. The guide is generated

`tools/gen_guide.py` builds the in-game Field Guide, `docs/GUIDE.md` and
`docs/guide.html` from the pack's own data. Never hand-write a stat into the
guide; change the pack and re-run the generator.

## Build

    python3 tools/gen_assets.py     # textures, icons, particles, armour
    python3 tools/gen_entities.py   # geometry + entity textures
    python3 tools/gen_animations.py
    python3 tools/gen_sounds.py
    python3 tools/balance.py        # apply the stat table
    python3 tools/gen_guide.py      # rebuild the guide from the pack
    ./build_addon.sh                # runs validate.py first and refuses on failure
