# ETERNAL END — Claude Implementation Pack

## Purpose
This package is the single source of truth for implementing the 20 custom mobs for a Minecraft Bedrock End-dimension addon.

IMPORTANT: The PNGs in `references/` are **visual design references**, not UV-ready Minecraft texture atlases. Do not treat their pixels as final UV coordinates. Build each mob as a normal Bedrock geometry + texture asset, using the design reference to reproduce the appearance.

## Non-negotiable implementation rules
1. Target Minecraft Bedrock Edition behavior/resource packs.
2. Keep every mob as its own namespaced entity. Never reuse another mob's identifier.
3. Use the exact IDs in `specs/mobs.json`.
4. Use one geometry file, one texture file, one client entity file, one behavior entity file, and one animation/controller set per mob where needed.
5. All texture paths must be lowercase and match the filenames exactly.
6. Do not put multiple mobs into one texture unless explicitly specified.
7. Preserve the visual identity from the corresponding PNG reference.
8. Bosses must have noticeably larger scale, health, damage, unique attacks, and boss-style presentation.
9. Passive mobs must be tamable where specified and must provide meat drops as specified.
10. Hostile mobs must have clear attack AI and must spawn in the End according to their spawn settings.
11. The addon must load without missing-resource errors. Validate every identifier and every referenced file.
12. If a feature cannot be implemented exactly, choose the closest Bedrock-native implementation rather than silently omitting it.

## Recommended texture strategy
Use 64x64 or 128x128 PNG textures for normal mobs and 128x128 or 256x256 for large bosses. Keep UV islands aligned to the geometry. Use nearest-neighbor/pixel-art treatment; do not blur or smooth the textures.

## Naming convention
Resource pack:
  textures/entity/eternal_end/<mob_id>.png
  models/entity/<mob_id>.geo.json
  entity/<mob_id>.entity.json

Behavior pack:
  entities/<mob_id>.json

Namespace:
  eternal_end:<mob_id>

## Build order
1. Create folder structure.
2. Create geometry.
3. Create final UV texture from the visual reference.
4. Create client entity and material/texture bindings.
5. Create behavior entity and AI.
6. Add animations/controllers.
7. Add loot tables.
8. Add spawn rules.
9. Run pack validation and test every entity in-game.
10. Only after all 20 entities load, add advanced effects/particles.

## Important correction
The original concept sheet accidentally contained an extra Ender Ghost. The official 20-mob roster for this package is the 3 bosses + 12 hostile mobs + 5 passive/tamable mobs listed in `mobs.json`. Ender Ghost is NOT part of the official 20.
