# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable auto farms for Minecraft Bedrock / Pocket Edition. Right-click
a block with the **Structure Build Tool**, pick a farm from a menu, preview
its footprint as a particle outline, then confirm to have it built instantly.

Includes eight farms, plus two standalone tools:

- **Iron Golem Farm** — rebuilt from scratch as a single, tried-and-true
  one-tier design (no stacking, no level slider — one clean build). An
  open villager hall (beds + composters, not sealed pods — see below for
  why that matters) fills exactly 20 beds + 20 composter workstations with
  20 villagers, spawned as plain adults so none of them can turn out to be
  nitwits (see below for why that's true "by construction," not a runtime
  check). An open-top lit spawn platform is a real water pool (not just a
  current over a dry floor) pushing golems down an 8-block shaft onto a
  checkerboard of lit campfires — real, item-safe damage over time,
  finishing off what the fall softened — into a hopper floor.
- **Auto Crop Farm** — a pinwheel layout: 4 farmer villagers, each with
  their own composter-on-water plot, arranged around ONE caged collector
  villager at the center, with rail and parked hopper minecarts in the pit
  catching whatever food gets tossed in. Build 1-4 of these as fully
  separate, independent farms on the ground, 10 blocks apart from each
  other.
- **Giant Crop Farm** — a single 19x19 field (the actual, real limit of how
  far a Bedrock farmer villager searches for farmland — 9 blocks in every
  direction from itself), worked by exactly ONE villager, whose inventory
  is pre-filled with junk on spawn so it can never pick its own harvest
  back up — every crop it cuts falls to a full hopper floor underneath
  instead. A beehive + flowers sit inside the same fully sealed glass dome
  as the crops, so bees pollinate (a real, if modest, growth-stage boost on
  wheat/carrots/potatoes/beetroot) without ever having an unobstructed exit
  to escape through. Build 1-4 of these.
- **One-Tick Kelp Farm** — real observer+piston auto-harvest lanes (an
  observer's redstone pulse is exactly 1 tick, hence the name) that pop
  every newly-grown kelp segment the instant it appears, with a hopper
  directly under each lane catching the drop — no bonemeal dispenser
  (kelp/bamboo bonemeal boosting is real, but not how any actual standing
  kelp farm design works; more parallel lanes wins). Build 1-4 of these.
- **Passive Mob Farm** — a lit, open grass platform where cows/pigs/sheep/
  chickens spawn and graze, a water funnel pushes them into a fall + magma
  kill zone, and an auto-smoker cooks the drops before a hopper stores them
  in a chest. Build 1-4 of these too, same ground-level layout as the crop
  farm.
- **AFK Fish Farm** — a real, physical roofed/lit/rain-proof pool + dock +
  chest. Bedrock has no supported way to auto-reel a real fishing rod, so
  this half is genuinely AFK-*friendly*, not AFK-*automatic* — pair it with
  the Auto Fishing Rod tool below for the fully hands-off part. Build 1-4
  pools.
- **Pillager Outpost Farm (Ominous Bottle Farm)** — build this directly
  above/beside the tower of an EXISTING pillager outpost (Script API can't
  search the world for structures, so, like every farm here, you position
  it yourself). Pillager Captains — identifiable by the Ominous Banner they
  carry — have a real chance to drop an Ominous Bottle on death, so this is
  a legitimate way to farm them. You do the killing yourself, in a real
  6x6 bottom chamber reached by a safe ladder shaft + door: a 12-block
  fall (~9 damage) softens whatever drops without being outright lethal,
  so there's always something left to finish by hand — which also gets
  you real player-kill loot bonuses (Looting, kill-gated drops) an
  automated kill never would. A full hopper floor collects it either way.
- **Librarian Trading Hall** — 5-librarian-stall sections (bed + lectern
  each, bookshelf decor, fence front you can trade across), 1-4 sections
  (up to 20 librarians). Paired with the **Villager Manager Wand** (see
  below) for fast trade-reroll/replace — see that tool's entry for the one
  part of the original ask (fully automatic Mending detection) that isn't
  actually possible with Script API today, and why.

Two standalone tools (craftable, also in the Creative inventory):

- **Auto Fishing Rod** — right-click to toggle. While active and you're
  standing near open water, it rolls the real vanilla fishing-loot odds
  (85% fish / 10% junk / 5% treasure) on a randomized 5-30s timer and gives
  you the result directly — a clearly-scripted convenience item, not a
  recreation of the real bobber/reel cycle (there's no stable API hook for
  that). Right-click again to stop.
- **Villager Manager Wand** — right-click any villager for a menu to either
  reroll its trades (breaks/replaces the nearest lectern — the real
  mechanic, but only works before you've made a first trade with that
  villager) or replace it outright with a fresh, unemployed one. Script API
  has no way to read a villager's offered trades before you commit to one,
  so you still have to glance at the trade screen yourself — this just
  makes acting on it near-instant instead of manual block-breaking.

## Iron Golem Farm: rebuilt as a single tried-and-true tier

This farm was rebuilt from scratch (the old multi-tier stacking version and
its separate single-tier wrapper are both gone — `ironFarm.js` is a fresh
file). It's deliberately just ONE tier, ONE menu entry, no level slider —
that's what was asked for, and it also sidesteps a real complication the
old stacked version had to work around (merging multiple tiers into one
combined village to share a population cap, only active near the player).
One tier keeps that entirely out of the picture.

The numbers are still the real, researched ones: Bedrock's actual
requirement for golems to spawn at all is **20 beds and 10 villagers, with
75% of them having reached and used a workstation in the last in-game
day** — much bigger than most people assume. This farm fills every one of
those 20 slots: **20 beds + 20 composter workstations + 20 villagers**, in
two open rows of 10 so villagers can freely path between bed and
workstation (sealing them into isolated pods silently breaks this).

**No nitwits, and here's exactly why that's true:** in Bedrock, a villager
only has a chance (10%) to become a nitwit at the moment a bred baby grows
into an adult. That growth step never happens here — every villager is
spawned directly as a plain adult (same as a spawn egg), so it never goes
through the roll that could make it one. There's no documented, stable way
for Script API to read a villager's profession afterward to double-check,
so this is a guarantee "by construction," not a runtime check — worth
being upfront about rather than claiming a verification step that doesn't
actually exist.

**Water push**: a source column on the west wall (flowing east) and one on
the north wall (flowing south) converge on a 2-wide SE corner drain. Two
currents on OPPOSITE walls flowing head-on into each other create a
dead/ambiguous push exactly where they'd meet; two currents on ADJACENT
walls only ever combine, never cancel — that's why the drain is a corner,
not the center, and why it's 2 walls with real source blocks (not a
hand-filled pool of uniform sources, which would have no current at all).

**Kill chamber: campfires, not lava/magma.** A lit campfire deals real,
verified damage over time (~2 damage/second) and — unlike lava or fire —
does not destroy item drops and doesn't set the mob on fire either. Iron
golems have 100 HP, so an 8-block fall first (real fall-damage math, not
enough alone to kill something with that much health, but a meaningful
head start) softens them before they land on a floor checkerboarded
between lit campfires and hoppers. That checkerboard matters: a campfire
is solid on top, so a hopper placed directly UNDER one can never reach
items resting on it (they sit a full block above the hopper's suction
range) — interleaving hopper tiles at the same layer, right next to every
campfire, is what actually lets the drops get collected.

**No roof.** The hall and platform are open at the top; an enclosed room's
darkness used to be what (accidentally) kept hostile mobs out, so it's lit
heavily instead (sea lanterns at hall height and platform height) to keep
light levels high enough that nothing hostile spawns despite the open top.

**No zombie cage.** A caged zombie near the villagers (on the theory that a
nearby threat raises golem-spawn urgency) is a real mechanic — on Java,
where 3 panicking villagers can emergency-summon a golem. That panic
mechanic doesn't exist on Bedrock at all; Bedrock's golem spawning is
purely population/bed/workstation-based (see above), so a caged zombie
does nothing here except take up space.

**Build it away from any existing village** (100+ blocks is a commonly
cited safe distance) — a nearby real village can merge with yours and
throw off the population cap / golem count.

The crop farm's pinwheel layout and the mob farm's water push were also
matched to specific, widely-used reference designs rather than invented
from scratch:

- **Crop farm is a pinwheel**, 4 farmer quadrants
  around one central collector pit, with a short (1-block-high) wall around
  the pit — low enough for a farmer standing outside to reach over and
  share food, tall enough that the caged collector can't walk out. A hopper
  sits under every pit tile, rail on top, and a parked hopper minecart on
  the 8 tiles around the collector — matching the reference design's
  screenshot, which clearly shows rail and parked minecarts in the pit (an
  earlier pass here mistakenly replaced that with a bare hopper floor).
- **Mob farm's water wasn't actually pushing anything.** It still had the
  original west+east opposing-current pattern (two currents flowing
  head-on into each other cancel out right where they'd meet) even after
  that exact bug was found and fixed on the iron farm — the fix was never
  carried over to this file. Now uses the same west+north
  adjacent-walls-converge-on-a-corner pattern as the iron farm, with the
  drain and fall shaft moved to match.

## Achievement compatibility (read this first)

This took three tries to get right, so here's the real story:

1. **First version** used the Script API with no `metadata.product_type`
   field. Activating it immediately showed Minecraft's "You can't earn
   achievements" dialog — *"An external behavior pack was activated."*
2. **Second version** removed the Script API entirely and rebuilt
   everything as data-driven items triggering `.mcfunction` files via each
   item's `minecraft:on_use` component. This turned out to be a dead end:
   `run_command` (the action that actually invokes the function) requires
   the **Holiday Creator Features** experimental toggle to work at all —
   without it, the item silently does nothing, which is exactly what
   happened when tested. And experimental toggles disable achievements
   independently of everything else, so this path could never have worked
   for the stated goal even if the wiring had been correct.
3. **This version** goes back to the Script API (which doesn't need any
   experimental toggle — stable, non-beta `@minecraft/server` module
   versions like the ones this addon depends on never require Beta APIs or
   Holiday Creator Features) and adds the piece that was actually missing
   from the start:
   ```json
   "metadata": {
     "product_type": "addon"
   }
   ```
   in **both** `BP/manifest.json` and `RP/manifest.json`. Without this
   field, Bedrock treats any custom pack as a potential "cheat world" and
   blocks achievements regardless of what it contains — this is documented
   community knowledge and matches how other achievement-friendly
   community addons (e.g. Force Creative-style packs, which do far more
   invasive things than this one) stay compatible.

So: Script API + `product_type: addon`, no experiments, no cheats. This is
the version to test.

## Install

1. Run `./build_addon.sh` (requires `zip`) to produce `dist/AutoFarmAddon.mcaddon`,
   or zip the `BP/` and `RP/` folders together yourself.
2. Send that `.mcaddon` file to your device and open it — Minecraft will
   import both packs.
3. In your world settings, add **both** **Groundwork Farms [Behavior]**
   *and* **Groundwork Farms [Resources]** — under their respective
   Behavior Packs / Resource Packs tabs. Adding only one is a common
   mistake and shows up as items with no icon and a raw
   `item.autofarm:...name` name instead of proper text/art, since that
   text and icon live in the resource pack.
4. Leave everything under **Experiments** off, and leave cheats off.
   Nothing here needs them.

## Using it in-game

1. Craft a **Structure Build Tool**: iron ingot / emerald / iron ingot on
   the top row, stick in the bottom-middle row (see `BP/recipes/build_tool.json`,
   or check the recipe book). It's also in the Creative inventory under
   Equipment.
2. Stand where you want the farm's front-left corner and right-click the
   ground with the tool.
3. Pick a farm from the menu.
4. Pick how many to build (1-4 — stacked levels for the iron farm, or
   separate ground-level units 10 blocks apart for the crop and mob farms).
   The single-tier Iron Golem Farm and the Pillager Outpost Farm skip this
   step — they always build exactly one, since they're meant to go in one
   specific spot.
5. If enabled, a particle box appears showing exactly where the structure
   will go. Confirm to build it instantly, or cancel — nothing is placed
   until you confirm.

The farm is built facing away from the direction you were looking when you
clicked, snapped to the nearest cardinal direction.

Craft the **Auto Fishing Rod** (clock / fishing rod / redstone, top to
bottom) and the **Villager Manager Wand** (book / emerald / stick, top to
bottom) the same way — both also show up in the Creative inventory. Neither
needs the build tool; use them directly.

## How the mechanics actually work

Nothing here is scripted loot or fake spawns — every drop comes from real
vanilla AI and physics:

**Iron Golem Farm** — Two open rows of 10 beds facing 10 composters each
(20 of each, 20 villagers spawned as plain adults so none can roll a
nitwit) let villagers freely path between sleeping and working, which is
what actually keeps them counted as valid village members (sealing them in
isolated pods, an earlier design, silently broke this). No zombie cage —
that's a Java-only mechanic (see above). Golems spawn in the open-top,
heavily-lit water pool above the hall; a source column on the west wall
(flows east) and one on the north wall (flows south) push everything
toward a 2-wide drain in the SE corner, and the rest of the pool fills in
from those two sources via the game's own fluid physics (a hand-filled
pool of uniform source blocks would have no current — see the
water-current notes above). Golems fall 8 blocks onto a checkerboard of
lit campfires and hoppers — real, item-safe damage over time (campfires
don't destroy drops, unlike lava/fire) finishes off what the fall
softened, and the interleaved hopper tiles catch every drop.

**Crop Farm** — A pinwheel: 4 farmer villagers, each in their own 9x9
quadrant (farmers won't work land more than ~4 blocks from their
composter, so a composter centered in each quadrant covers the whole
thing), arranged around a single collector villager caged in a small pit
at the center. Each quadrant's center tile is a water source with a
composter placed directly on top of it — hydrates the whole quadrant and
serves as that farmer's job site in one tile — with glowstone above for
light. The collector's pit has a 1-block-high stone brick wall: tall
enough that the collector can't walk out, short enough that a farmer
standing right outside can reach over and share surplus food with it. A
hopper sits under all 9 pit tiles, with rail and a parked hopper minecart
on the 8 tiles around the collector's own spot — that share attempt drops
food onto whichever minecart is nearest, and the hopper below drains it
out to the shared collection chest. This is a documented, real Bedrock
design (matching a specific, widely-used reference tutorial), not an
invented one — but it's still real (and therefore somewhat unpredictable)
villager AI, so give it real time before judging it broken. Like the mob
farm, this one isn't stacked — each of the 1-4 you build is a complete,
independent 4-farmer pinwheel on the ground, 10 blocks from the next one.

**Passive Mob Farm** — An open, heavily-lit grass platform where cows,
pigs, sheep, and chickens naturally spawn and graze over time (no
breeding required, though feeding them speeds it up) inside a 2-block-high
fence barrier that keeps them from wandering off the edge early. The same
west+north adjacent-walls water convergence as the iron farm pushes grown
animals into a 2-wide SE corner drain, which drops them 14 blocks — far
enough to kill cows/pigs/sheep outright with fall damage alone. Chickens
take no fall damage in vanilla, so the landing zone is also lined with
magma blocks (safe for item drops, and — being a solid block rather than a
fluid — physically unable to spread past where it's placed) as a
guaranteed finisher. A hopper tile in the landing zone directly catches
drops and feeds a smoker's input slot from directly above — standard
vanilla hopper-into-furnace behavior, no scripting needed for the cooking
itself. The smoker's fuel slot is pre-loaded with a stack of coal at build
time (good for 512 smelts), and a second hopper underneath automatically
pulls the cooked output into the final chest.

All three original farms funnel their output into one shared external
hopper chain ending in a double chest — not buried, so it's immediately
visible without digging, and there's only ever one chest to check per farm
type regardless of how many levels/units you built.

**Giant Crop Farm** — A single villager can only search for farmland up to
9 blocks away on X and Z (a real, checked Bedrock limit), so the field is
sized to exactly that: 19x19. Hydration for a field that size needs more
than one water source (farmland only stays tilled within 4 blocks of
water), so a 3x3 grid of 9 water tiles spaced 5 apart replaces farmland on
those cells and together covers the whole field with no dry spots. The
center one doubles as the farmer's composter job site. Collection doesn't
use a second "beggar" villager like the Auto Crop Farm above — with only
one villager there's nobody for it to throw surplus food to, so instead the
farmer spawns with all 8 of its carry slots already full of a junk item
(dirt). A villager that can't pick anything up leaves everything it
harvests sitting on the ground, which a two-layer hopper floor (every row
feeds west to that row's x=0 tile, which feeds down into a spine that
carries everything north to one corner chest) then collects in full. A
beehive sits on a small pillar with a few flowers nearby, entirely inside
the same sealed glass dome as the field — bees pollinating wheat, carrots,
potatoes, or beetroot really does advance that crop's growth stage, and a
bee can only ever exit a hive from its front, so facing the hive into a
dome with no player-sized opening anywhere means the bees are genuinely
contained, not just decorated. There's deliberately no door: you never need
to walk in, since collection is fully external.

**One-Tick Kelp Farm** — Each lane is a hand-verified redstone circuit, not
a guess: an observer can only ever detect a change in the one block cell
it's aimed at, and a piston can only ever push into a cell it's physically
touching, so for both of them to act on the SAME growth cell they have to
sit on two different faces of it — which means they can never be directly
touching each other. A short, flat redstone-dust relay (running through a
dedicated corridor column that never crosses the kelp/piston/observer
cells) connects the observer's back face to the piston's side face. The
observer's pulse is exactly 1 redstone tick, so the instant kelp grows into
the watched cell, the piston pops it before a second segment can ever form.
No water current is needed for collection — kelp isn't a solid block, so a
popped item just falls straight through the (permanent) base kelp block
below it into a hopper serving as that lane's own floor tile. No bonemeal
dispenser: it's real that bonemeal grows kelp, but no actual working kelp
farm design dispenses it automatically to an open column, and running more
lanes produces more per hour than a bonemeal clock would anyway.

**Passive Mob Farm** — An open, heavily-lit grass platform where cows,
pigs, sheep, and chickens naturally spawn and graze over time (no
breeding required, though feeding them speeds it up) inside a 2-block-high
fence barrier that keeps them from wandering off the edge early. The same
west+north adjacent-walls water convergence as the iron farm pushes grown
animals into a 2-wide SE corner drain, which drops them 14 blocks — far
enough to kill cows/pigs/sheep outright with fall damage alone. Chickens
take no fall damage in vanilla, so the landing zone is also lined with
magma blocks (safe for item drops, and — being a solid block rather than a
fluid — physically unable to spread past where it's placed) as a
guaranteed finisher. A hopper tile in the landing zone directly catches
drops and feeds a smoker's input slot from directly above — standard
vanilla hopper-into-furnace behavior, no scripting needed for the cooking
itself. The smoker's fuel slot is pre-loaded with a stack of coal at build
time (good for 512 smelts), and a second hopper underneath automatically
pulls the cooked output into the final chest.

**AFK Fish Farm** — A roofed 5x5 pool blocks rain and the lit interior
keeps hostiles from spawning on the dock, but the fishing itself is real,
manual, player-driven fishing — Bedrock has no supported way to script the
actual cast/bob/reel cycle unattended. For the actually-hands-off half, use
the **Auto Fishing Rod**: right-click to toggle, and while it's on and
you're near open water it rolls the real vanilla fishing loot odds (85%
fish, 10% junk, 5% treasure — the verified real split; the specific
junk/treasure items are a representative subset, not an exact reproduction
of every sub-weight) on a randomized 5-30s timer, giving you the item and
a burst of XP directly. This is clearly a scripted stand-in, documented as
such rather than presented as real fishing.

**Pillager Outpost Farm** — Position this yourself, directly above or
beside an outpost's tower — outposts spawn pillagers (including Captains,
who carry the Ominous Banner and have a real chance to drop an Ominous
Bottle when killed) on the highest opaque block with open space above it,
within the structure's own bounds, so building a new "highest point" there
is what redirects those spawns onto the platform. The platform is
deliberately left unlit (every other farm here lights its platform
heavily) — ordinary hostile mobs can spawn here too, but that's fine, they
fall down the same shaft into the same chamber. A real "auto trident
killer" (a Channeling trident thrown during an actual thunderstorm) only
works while it's storming and needs a Channeling trident to begin with —
not something a static structure can keep running unattended, and not
something this addon should hand you out of nowhere either. Instead, YOU
do the killing: a 12-block fall shaft (real fall-damage math — about 9
damage, enough to soften most outpost mobs without being lethal on its
own) drops everything into a real 6x6, 2-tall bottom chamber, reached by
an enclosed ladder shaft and a proper 2-tall door so you can walk down and
finish the fight yourself — which also means the kill is credited to you,
qualifying for player-kill-only loot bonuses (Looting, certain gated
drops) that an automated kill never would. The whole chamber floor is a
two-layer hopper grid, so whatever you kill still gets collected
automatically even though the kill itself isn't.

**Librarian Trading Hall** — 5-stall sections, each an unemployed villager
next to a lectern (ordinary profession-claiming — no scripting needed for
that part) inside a small cell: fence on the front so the villager can't
walk out but you can still reach over to trade, bookshelves on the back
wall for theme (bookshelves boost an enchanting TABLE's level cap when
placed near one — they do nothing to villager trades, so don't expect
different offers from them). See "Checking for Mending" below for the
Villager Manager Wand this is meant to be used with.

## Checking for Mending (and the trading hall's real limits)

Requested: an automatic check that keeps re-rolling a librarian until it
offers Mending or another good enchantment, replacing the villager if not.
Here's exactly what's real and what isn't, checked rather than assumed:

- **Real and used here:** breaking and replacing a librarian's claimed
  lectern re-rolls its enchanted-book trade — but only for trades it
  hasn't sold yet. The instant you complete a first trade with a villager,
  its entire trade list (including any other, still-unsold slots) locks
  permanently. The Villager Manager Wand automates the break/replace itself
  so re-rolling is a menu tap instead of manual block-breaking.
- **Not currently possible:** having the addon silently read a villager's
  offered trade and decide FOR you whether it's Mending before you commit.
  `@minecraft/server` does not expose a stable way to inspect a villager's
  current (unclaimed) trade offers — there's no documented API for it. This
  isn't a corner that got cut; it's a real platform limit, and pretending
  otherwise would mean the addon claiming to do something it can't
  actually do. You still open the trade screen and look, same as always —
  the wand just makes acting on what you see fast.

For when you do look — the researched, correct (Bedrock and Java match
here) max level for every enchantment, so you know what you're actually
holding out for:

| Enchantment | Max level | Enchantment | Max level |
|---|---|---|---|
| Protection | IV | Sharpness | V |
| Fire Protection | IV | Smite | V |
| Feather Falling | IV | Bane of Arthropods | V |
| Blast Protection | IV | Knockback | II |
| Projectile Protection | IV | Fire Aspect | II |
| Thorns | III | Looting | III |
| Respiration | III | Sweeping Edge | III |
| Aqua Affinity | I | Efficiency | V |
| Depth Strider | III | Silk Touch | I |
| Frost Walker | II | Unbreaking | III |
| Curse of Binding | I | Fortune | III |
| Curse of Vanishing | I | Power | V |
| Soul Speed | III | Punch | II |
| Swift Sneak | III | Flame | I |
| Mending | I | Infinity | I |
| Multishot | I | Luck of the Sea | III |
| Quick Charge | III | Lure | III |
| Piercing | IV | Loyalty | III |
| Density | V | Impaling | V |
| Breach | IV | Riptide | III |
| Wind Burst | III | Channeling | I |

For a librarian trading hall specifically, the enchantments most worth
holding out for on a book (roughly in priority order for survival play):
**Mending** first — it's the one the request called out by name, and it's
the only way to repair gear without XP-hungry anvil combining. After that:
**Unbreaking III**, **Efficiency V**, **Fortune III**/**Looting III**
depending on what you're using the tool/weapon for, **Sharpness V** or
**Power V**, and **Silk Touch** if you specifically need it (mutually
exclusive with Fortune on the same tool). Curses (Binding, Vanishing) are
generally the ones to reroll away from unless you're deliberately trying to
put one on a mob-drop item.

## Known limitations / tuning tips

- **Three real bugs found and fixed via testing + the in-game content
  log** (Settings → Creator → Content Log), not guesswork:
  1. `@minecraft/server` removed the `itemUseOn` event entirely in its
     2.0.0 release, and the manifest still pointed at the old 1.x module
     line — the script's event handler likely never loaded at all.
     Updated `BP/manifest.json` to `@minecraft/server` 2.0.0 /
     `@minecraft/server-ui` 2.1.0, and switched
     `scripts/main.js` from `world.afterEvents.itemUseOn` to
     `world.afterEvents.playerInteractWithBlock` (the documented
     replacement).
  2. **The actual cause of the persistent blank icon**, found via the
     content log's exact error text: `menu_category -> group: string
     must be prefixed with a namespace`. `BP/items/structure_tool.json`
     had `"group": "itemGroup.name.tool"` with no namespace, which made
     the *entire item* fail to parse — so no icon fix could ever have
     worked, because the item using that icon never successfully loaded
     in the first place. Fixed to `"minecraft:itemGroup.name.tool"`.
  3. The tool's icon points at a texture this pack ships itself
     (`RP/textures/items/build_tool_icon.png`) rather than trying to
     reference a vanilla texture by path without shipping it — that
     approach produced the same "missing icon" error reliably in
     testing, so item icons apparently require the file to be physically
     present in the resource pack that declares the shortname.
- **Bed and hopper orientation** are set programmatically and rotated to
  match the direction you built in; if a state value mapping doesn't match
  your game version exactly, the bed/hopper still functions — worst case
  it's a purely cosmetic mismatch you can fix by breaking and replacing
  that one block.
- **Crop farm collection is still the least deterministic mechanic here.**
  Each farmer quadrant has its own dedicated composter, but the actual
  food-sharing-into-the-pit behavior is real, somewhat unpredictable
  vanilla AI. Give it real in-game time before concluding it isn't working.
- **Stay near the build site until you see "Build Complete!"** on screen.
  Building spreads block placement across many ticks to avoid freezing the
  game; a large farm (the Giant Crop Farm's hundreds of hoppers, or 4 units
  of any ground farm) can take a while. If you wander far enough that
  chunks unload mid-build, later placements (including villager spawns,
  which happen last) can silently fail, leaving an incomplete structure. If
  that happens, just build again while staying put.
- **On leaves and golem spawning**: leaves aren't part of the vanilla iron
  golem spawn algorithm as far as I'm aware — spawning depends on village
  size/bed count, golem population cap, and a valid flat surface, not
  nearby foliage. If you have a specific source suggesting otherwise I'm
  happy to look into it, but I didn't want to add block placements based
  on a mechanic I can't verify is real.
- **Building 4 of the crop or mob farm** means the farthest unit's items
  travel through a long shared hopper chain (up to ~120 blocks) to reach
  the one collection chest. This is normal vanilla hopper transfer speed,
  not a bug — expect a real but bounded delay (each hop is 8 game ticks),
  not data loss (hoppers buffer 5 stacks each). If you'd rather have faster,
  fully independent collection per unit at the cost of more chests to
  check, that's a one-line change in the farm's `plan()` — see "Adding your
  own farm" below.
- **Passive Mob Farm fall shaft goes ~15 blocks below where you build.** If
  you build on ground very close to the world's minimum build height, the
  kill zone/smoker/chest can clip below it. Build on typical Overworld
  terrain and this isn't a concern.
- **Testing methodology**: every farm change is run through a mock-runtime
  harness (stub `@minecraft/server` modules) across all 4 facings and every
  level count, checking for invalid coordinates/ids, accidental overlaps
  between separately-authored pieces, and — since a real bug slipped
  through here once (a lava kill pocket that leaked, root cause never
  fully confirmed) — a flood-fill check that every water/lava placement's
  reachable open area stays within a sane size, catching containment
  mistakes before they ship instead of after. This doesn't replace actually
  testing in-game (it can't verify real Bedrock physics, villager AI, or
  anything that depends on the live game), but it does catch a real class
  of authoring mistakes automatically.
- **Build site**: the tool clears a generous interior volume before
  building, but doesn't touch anything outside the farm's own footprint.
  Build on relatively flat ground, away from any existing village (see
  above). Clearance needed: the iron farm is a single ~9-block-tall,
  15x15 build (plus the 8-block kill shaft below); the crop and mob farms
  are only ~5-7 blocks tall each but stretch to ~120 blocks wide at 4
  units (23x23 and 15x15 footprints per unit, 10 blocks apart) since
  they're built side by side on the ground rather than stacked; the
  Pillager Outpost Farm digs its ladder shaft + chamber roughly 20 blocks
  below wherever you build it, so make sure there's clearance underneath.
- Module/engine versions in `BP/manifest.json` are set to reasonably recent
  values; if your Minecraft version is newer, update them per Mojang's
  Script API changelog.
- If a beacon/tool shows up with no icon and a raw translation key as its
  name, the resource pack isn't active for that world — see step 3 under
  Install.

## Project layout

```
BP/                      Behavior pack
  manifest.json            Includes metadata.product_type: "addon"
  items/structure_tool.json, auto_fishing_rod.json, villager_wand.json
  recipes/build_tool.json, auto_fishing_rod.json, villager_wand.json
  scripts/
    main.js               Item-use handler, menus, build orchestration, farm registry
    lib/geometry.js         Facing + rotation math
    lib/builder.js            Block/entity placement generators (system.runJob-safe)
    lib/outline.js             Particle bounding-box preview
    lib/autoFishingRod.js      Auto Fishing Rod toggle + loot-roll loop
    lib/villagerManager.js     Villager Manager Wand (reroll/replace)
    farms/ironFarm.js           Single-tier iron golem farm (campfire kill)
    farms/cropFarm.js            4-farmer pinwheel crop farm
    farms/giantCropFarm.js        19x19 single-villager crop farm + bees
    farms/kelpFarm.js              One-tick observer/piston kelp farm
    farms/mobFarm.js                Passive mob farm layout + mechanics
    farms/fishFarm.js                AFK fish pool structure
    farms/pillagerOutpostFarm.js      Ominous bottle / outpost kill farm
    farms/tradingHall.js              Librarian trading hall stalls
RP/                      Resource pack (icons, item texture, lang)
  manifest.json             Includes metadata.product_type: "addon"
test/                    Mock-runtime validation harness (Node, not the game)
  mock/minecraft-server.js, minecraft-server-ui.js   Minimal @minecraft/* stubs
  validate_farms.mjs      Runs plan() for every farm across all facings/levels
build_addon.sh            Packages BP/ + RP/ into dist/AutoFarmAddon.mcaddon
```

Run `./test/run.sh` any time after editing a farm module — it stubs
`@minecraft/server(-ui)` into a (gitignored) `node_modules/` and runs every
farm's `plan()` across all facings/levels, catching import errors, thrown
exceptions, and malformed coordinates/ids before you ever load the pack
in-game. It cannot verify real vanilla block states, redstone timing, or
villager AI — only actual in-game testing can do that.

## Adding your own farm

Each farm module exports an object with `id`, `name`, `shortDescription`,
`size`, `levelSpacing`, `maxLevels`, and a `plan({ levels, facing })` method
returning `{ placements, spawns, fills? }` in local space (see `cropFarm.js`/
`mobFarm.js` for side-by-side ground units, or `ironFarm.js`/
`pillagerOutpostFarm.js` for a single fixed-position build via
`fixedLevels`). Register it in `FARMS` in `scripts/main.js` and it shows up
in the menu automatically.

A few optional properties change how the generic build flow treats a farm:

- `stackAxis: "x"` (or `"z"`) — repeat levels sideways in local space
  instead of stacking them in `y`. Defaults to `"y"` if omitted.
- `levelLabel` — override the slider's label text in the level-count menu
  (defaults to `"Stack height (levels)"`).
- `unitNoun` — override the word used for "N of these" in menus/messages
  (defaults to `"Level"`).
- `fills` — a list of `{x, y, z, slot, itemId, amount}` to pre-load into an
  already-placed container's inventory slot after building (e.g. fuel into
  a smoker), applied after `placements` but before `spawns`.
- `fixedLevels` — skip the level-count menu entirely and always build
  exactly this many (see `ironFarm.js`/`pillagerOutpostFarm.js` for farms
  meant to go in one specific spot rather than being repeated).
- A `spawns` entry can include an `inventory` array of
  `{slot, itemId, amount}` to pre-fill that specific entity's own carry
  slots right after it spawns (see `giantCropFarm.js`'s farmer villager).
