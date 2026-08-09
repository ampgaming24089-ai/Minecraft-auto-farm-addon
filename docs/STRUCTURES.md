# Boss Chambers: how they're built

Bedrock add-ons can't ship hand-authored `.mcstructure` NBT files without an
in-game Structure Block export pass, so instead of a placeholder chamber this
addon **builds each boss chamber procedurally at runtime** via the Script API
(`/fill`/`/setblock` executed through `dimension.runCommandAsync`, see
`BP/scripts/bosses/chambers.js`). This is a legitimate, common technique for
data/script-only Bedrock add-ons and has three advantages over shipping a
static structure:

1. No missing-structure crashes — the chamber is code, not an asset that can
   go missing or desync from the manifest.
2. The chamber can react to the terrain it's placed in (it flattens/clears
   its own footprint first).
3. It's trivial to reskin — change the palette table at the top of
   `chambers.js` and every future chamber uses it.

## How a chamber gets triggered

1. World generation scatters a single **Ritual Altar** block
   (`hollowveil:ritual_altar`) per boss inside its themed sub-biome pocket
   (see `BP/features/*` + `BP/feature_rules/*`).
2. The player crafts that boss's **Sigil** (e.g. `hollowveil:sigil_hollow_king`)
   from materials found in the dimension and right-clicks it on the altar.
3. `scripts/bosses/chambers.js` clears/builds a themed room around the altar
   (Sunken Crypt / Widow's Hollow / Cinder Bastion — see `docs/STORY.md`),
   seals the entrance behind the player, and spawns the boss at the center.
4. On boss death the seal is removed, the loot chest unlocks, and the altar
   goes on a cooldown (`BOSS_COOLDOWN_TICKS` in `chambers.js`) before it can
   be used again, so the fight is repeatable without being spammable.

## Replacing a chamber with a hand-built one (optional, recommended for a
   visual upgrade)

If you want a bespoke, hand-decorated room instead of the procedural one:

1. Build the room in-game, capture it with a Structure Block
   (`Save` mode), and export it — this produces a `.mcstructure` file.
2. Drop it in `BP/structures/hollowveil/<boss>.mcstructure`.
3. In `chambers.js`, replace the relevant `buildX()` function's fill calls
   with `dimension.runCommandAsync("structure load hollowveil:<boss> x y z")`.

No other system needs to change — sigils, altars, spawning and cooldown all
stay the same.
