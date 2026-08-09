# The Hollow Veil dimension — setup notes

`BP/dimensions/hollow_veil.json` uses Bedrock's **data-driven custom
dimension** feature (flat-type generator, fixed single biome
`hollowveil:hollow_veil`, defined in `BP/biomes/hollow_veil.json`). This is
one of the newer parts of the Bedrock creator API and, unlike entities/items/
recipes, its exact JSON shape has moved between Minecraft versions and is
still gated behind an experimental toggle.

**Before creating a world with this addon**, enable these two world
experimental toggles (Create New World → Experiments):

- **Upcoming Creator Features** (covers custom dimensions/biomes)
- **Beta APIs** — only if your game version still gates the stable
  `@minecraft/server`/`@minecraft/server-ui` modules behind it; recent
  versions don't require this anymore.

If the dimension fails to generate on your specific game version, the
`generator` block in `hollow_veil.json` (`type`, `height_range`,
`biome_source`/`biome_source_options` keys) is the most likely thing that
drifted — cross-check it against the current Minecraft Creator docs'
"Custom Dimensions" page and adjust; nothing else in the addon depends on
the exact generator schema, so a fix there is isolated.

Everything built *on top of* the dimension (the portal, the boss chambers,
Hollow Hamlet, mob spawning) is implemented with long-stable APIs
(spawn rules, loot tables, the Script API's `system.runInterval`/
`dimension.runCommandAsync`) and does not depend on this part.
