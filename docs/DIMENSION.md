# The Hollow Veil dimension — how it actually works

**This changed after real device testing.** The first version of this addon
shipped a static `BP/dimensions/hollow_veil.json` file with a hand-written
`generator`/`biome_source` block. That format doesn't exist: the in-game
error was `DimensionLegacyParser ... components: missing required field`,
and even the corrected schema (`components.minecraft:generation.generator_type`)
turned out to be a dead end — cross-checking against Mojang's own
`bedrock-samples` and Microsoft's official `custom_dimensions` sample
(https://github.com/microsoft/minecraft-samples/tree/main/custom_dimensions)
showed that **custom dimensions are registered entirely through the Script
API now**, not a data file:

```js
system.beforeEvents.startup.subscribe((ev) => {
  ev.dimensionRegistry.registerCustomDimension("hollowveil:hollow_veil");
});
```

See `BP/scripts/main.js`. This is confirmed present in the **stable**
`@minecraft/server` 2.8.0/2.9.0 bindings (not just beta), which is why the
manifest depends on `@minecraft/server` 2.8.0 / `@minecraft/server-ui`
2.0.0, matching the official sample. `min_engine_version` is `1.26.30`,
one patch above what the dimension API alone needs, because the Veil
Dragon's rideable-flight components (see README's "Known limitations")
ship at that version. No experimental world toggle is required for either.

## The big consequence: it's a void, not a generated world

A script-registered custom dimension starts completely empty - no terrain,
no biome, nothing. There's no world generator to hook `spawn_rules`,
`features`/`feature_rules`, or a custom biome into, so several systems from
the first version had to move from "data the engine generates for you" to
"things the addon builds/does explicitly":

| System | Old (broken) approach | Current approach |
|---|---|---|
| Terrain | `generator: flat` in the dimension JSON | `BP/scripts/world/build.js` raises a real island (bedrock/stone/bonestone layers, ore scatter) with `/fill` the first time any player steps through the portal |
| Mob spawning | `spawn_rules/*.json` gated on `has_biome_tag: hollow_veil` | `BP/scripts/mobs/spawner.js` periodically spawns from a weighted table near players in the dimension. The `spawn_rules` files are still shipped (harmless) in case a future engine version does assign custom dimensions a real biome |
| Ritual altars / ore veins | `BP/features` + `BP/feature_rules` world-gen scatter | Placed directly during the same island build pass in `build.js` |
| Fog / water color | `BP/biomes/hollow_veil.json` + `biomes_client.json` keyed to that biome | `biomes_client.json` now keys off `minecraft:the_void` (the closest guess for whatever biome a script-registered dimension reports) - see `docs/SHADER.md` for the honest caveat on this one guess |

Everything else (entities, items, loot, trading, the portal frame detector,
boss chambers) was already built on long-stable APIs and needed no
architecture change - just the schema-level fixes described in the item/
entity JSON files themselves (see git history for the full list of
corrections made from the first real in-game test).
