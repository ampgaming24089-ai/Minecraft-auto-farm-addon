# Prompting for this project

You asked for your prompt to be fixed so it produces better art and correct
functions. Here is the rewrite, and why each part of it earns its place.

## The original

> Update the end dimension in Minecraft bedrock version 26.44 since Minecraft
> won't, make it better than the eternal end dimension add on and fully
> complete with no issues!

Three things in it work against you:

1. **"Better than \<other add-on\>"** is not a spec. Nobody building from it
   knows whether you want more biomes, better visuals, harder mobs or more
   loot, so they guess — and guess wrong roughly three times out of four.
2. **"No issues"** cannot be delivered by asserting it. What actually produces
   working JSON is naming the version you target and demanding the work be
   checked against that version's schemas.
3. **No art direction at all.** Ask for textures with no palette, no mood and
   no format and you get generic purple noise, because there is nothing to
   aim at.

## The rewrite

> Build a Minecraft Bedrock add-on that overhauls the End, targeting Bedrock
> 26.4 (internal 1.26.40) and the stable `@minecraft/server` 2.9.0 script API.
>
> **Scope, in priority order:**
> 1. Visual overhaul via Vibrant Visuals — lighting, atmospherics, colour
>    grading and volumetric fog, bound to `minecraft:the_end` through a client
>    biome file, not through global JSON.
> 2. Explorable content in the outer islands — procedural structures with
>    loot that scales with distance from the origin.
> 3. New blocks, ore and flora that fit the End's material language.
> 4. Two new mobs, one passive and one hostile.
>
> **Art direction:** cold and luminous. Six anchor colours: pale end stone
> `#DCE0A8`, deep void `#2A1140`, lit violet `#C77BFF`, teal `#1E8C7E`,
> lit teal `#5FE8D2`, and a near-black `#0E0920` for the sky. Every texture
> is 16×16 with a matching `_mer` map so it lights correctly under Vibrant
> Visuals. Generate the textures from a committed script so I can retune the
> palette in one place — do not commit hand-drawn PNGs I cannot edit.
>
> **Correctness bar:** no experimental toggles. Validate every JSON file
> against `@minecraft/bedrock-schemas` for the target version, check every
> `minecraft:` identifier against `@minecraft/vanilla-data` (Bedrock's ids
> differ from Java's), type-check the scripts against the real
> `@minecraft/server` types, and run the generation logic under Node against a
> stub of the API. Ship those checks as scripts in the repo.
>
> **Tell me plainly what you could not verify** — anything that needs the game
> running to confirm.

## Why each part changes the output

**Name the version twice.** "26.44" alone is ambiguous — Minecraft's 2026
year-based scheme means the marketing number and the internal number differ,
and `min_engine_version` wants the internal one. Giving both removes the guess.

**Rank the scope.** A priority order means partial delivery is still coherent.
An unranked list of four things delivered at 60% each is four broken features.

**Give the palette as hex.** This is the single biggest lever on art quality.
Six named colours turn "make it look End-ish" into a constraint that can be
satisfied and checked. Naming `_mer` maps matters just as much: without them
nothing glows correctly under Vibrant Visuals, and that is most of what makes
a modern End pack look modern.

**Ask for generated art, not PNGs.** Committed pixel art is a dead end — you
cannot retune it without redrawing it. A generator means changing one palette
entry retints the whole pack.

**Name the checking tools.** "No issues" is a wish. "Validate against
`@minecraft/bedrock-schemas`, check ids against `@minecraft/vanilla-data`" is
an instruction with a pass/fail outcome. Those two packages exist and are
published by Mojang; asking for them by name is what turns silent in-game
failures into build errors. The id check in this repo is what caught
`minecraft:end_stone_bricks` — a block that does not exist in Bedrock, where
it is called `minecraft:end_bricks`.

**Ask what could not be verified.** Without this you get confident claims
about untested behaviour. With it you get a list of what to watch on first
load, which is far more useful.

## Reusable skeleton

For the next add-on, fill in the blanks:

```
Build a Minecraft Bedrock add-on that <goal>, targeting Bedrock <marketing
version> (internal <1.x.y>) and the stable @minecraft/server <version> API.

Scope, in priority order:
1. <most important thing>
2. <next>
3. <next>

Art direction: <mood in three words>. Anchor colours: <hex list>. Every
texture <size> with a matching _mer map. Generate art from a committed script.

Correctness bar: no experimental toggles. Validate JSON against
@minecraft/bedrock-schemas, check identifiers against @minecraft/vanilla-data,
type-check scripts against the real @minecraft/server types, and ship the
checks in the repo.

Tell me plainly what you could not verify without running the game.
```
