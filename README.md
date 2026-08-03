# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable auto farms for Minecraft Bedrock / Pocket Edition. Right-click
a block with the **Structure Build Tool**, pick a farm from a menu, preview
its footprint as a particle outline, then confirm to have it built instantly.

Includes nine farms, plus two standalone tools:

- **Stackable Iron Farm** — an open villager hall (beds + composters, not
  sealed pods — see below for why that matters), an open-top lit spawn
  platform that's a real water pool (not just a current over a dry floor),
  and a corner magma kill pocket. Build 1-4 levels, stacked vertically and
  deliberately close together.
- **Iron Golem Farm (Single Tier)** — the exact same researched, working
  iron-farm layout above, but registered as its own single-tier menu entry
  (20 beds, 20 composter workstations, water push, magma kill chamber,
  hopper collection) with no level slider, since that's what was actually
  asked for as a standalone farm. Pick "Stackable Iron Farm" instead if you
  want the option to merge multiple tiers into one bigger village.
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
  a legitimate way to farm them. Kill system is a 23-block fall shaft (past
  the threshold for guaranteed fall damage) into a piston crusher on a
  2-observer clock, not a "trident killer" — see the module's header
  comment for why that specific ask isn't something a static structure can
  actually automate, and what was built instead.
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

## Important: what "stackable" actually means for the iron farm

Bedrock's real requirement for iron golems to spawn at all is **20 beds and
10 villagers, with 75% of them having reached and used a workstation in the
last in-game day** — much bigger than most people assume, and far bigger
than earlier versions of this addon used (which is why golems never spawned
and "water doesn't push them" was moot — there was nothing to push). Each
level here has **20 beds + 20 composters** in two open rows of 10.

The golem population cap is **1 golem per 10 villagers in a village**. An
earlier version of this addon tried to give every floor its own
*independent* cap by spacing levels far enough apart (80+ blocks) that
Bedrock wouldn't merge them into one village. That turned out to be a
mistake, based on a mechanic I'd missed:

**A village only spawns golems while a player is standing inside its
"activation region"** — the village's bounds expanded outward by roughly
32-48 blocks depending on your simulation distance setting. The distance
needed to keep two villages from merging is *larger* than that (~64+ blocks
beyond each village's own bounds). Since the separation-to-avoid-merging is
always bigger than the activation range, **there is no single spot you can
stand that keeps two truly separate villages both active at once** — you'd
only ever activate whichever one you're currently near, and the others sit
idle. That's true whether the farms are stacked vertically or spread out
horizontally on the ground — spreading them out doesn't fix it, it just
changes which axis the wasted distance is on.

So this farm does the opposite: **levels are built close together on
purpose so they merge into one combined village.** More levels = more total
villagers = a higher population cap, and because it's one village with one
activation region, every floor can spawn golems simultaneously from a
single AFK spot at the base:

- **4 levels = 80 villagers in one village = a population cap of 8**
  concurrent golems, all reachable from one spot.
- **Height is back to normal** — a 4-level build is about 45 blocks tall,
  not 250.
- **Collection is shared again** — one external hopper shaft down to one
  base chest, since the levels are close enough together that this is
  fast, not the minutes-long chain a spread-out design would need.
- **1-3 levels may not reliably spawn golems at all** if you don't fill
  every level's beds. This farm is only guaranteed to work with every
  built level fully populated (20/20 beds per level).
- **Build it away from any existing village** (100+ blocks is a commonly
  cited safe distance) — a nearby real village can merge with yours and
  throw off the cap.

Two more fixes worth calling out explicitly, both found from real in-game
testing feedback:

- **The water current wasn't pushing golems anywhere.** The earlier design
  ringed all 4 edges of the spawn platform with water flowing inward. That
  looks reasonable on paper, but water only flows about 7 blocks from a
  source before stopping, and two currents flowing head-on into each other
  from opposite edges create a dead/ambiguous push exactly where they
  meet — which was exactly the center drain, the one place the push needed
  to be strongest. The fix drops the north/south edges entirely and only
  uses a full-depth water column on the west wall (flowing east) and one on
  the east wall (flowing west). Every tile on the platform now has exactly
  one clear push direction toward the drain, never two fighting each other.
- **No more roof.** Each level used to be a fully sealed box. That's gone —
  every level is now open at the top. An enclosed room's darkness used to
  be what (accidentally) kept hostile mobs out; with the roof gone, that
  job is done instead by lighting the place heavily (sea lanterns lining
  both walls at hall height and platform height on every level), which
  keeps light levels high enough that nothing hostile spawns despite the
  open top.

Both the iron farm's platform and the crop farm's layout were rebuilt again
after that to match specific, widely-used reference designs the actual
builder shared screenshots of, rather than my own from-scratch layouts:

- **Iron farm platform is now a real pool, and the kill point moved to a
  corner.** The push mechanism is unchanged (it's the fix above — a source
  column on 2 adjacent walls only, everything else left for the game's own
  fluid physics to fill in, so it still has a real single-direction push
  instead of a hand-placed pool of uniform source blocks, which would have
  no push at all). What changed is the shape: instead of a thin current
  across a mostly-dry floor draining to a center hole, the whole platform
  fills in as a pool draining to a 2-wide hole in the SE corner.
- **Kill pocket is magma again, not lava.** A version of this pocket briefly
  used lava (matching a reference design's material list), but it leaked —
  lava spread out across the surrounding hall floor in testing instead of
  staying in the intended pocket. I traced through the containment logic
  and couldn't find where it actually escapes on paper, which means either
  there's a subtlety in how Bedrock's fluid placement behaves that I don't
  have full visibility into, or it was stale lava left over from an earlier
  rebuild at the same spot — I can't say for certain which. Rather than
  keep guessing at a fluid, it's magma now: a solid block, not a fluid, so
  it's physically incapable of spreading or leaking no matter what the real
  cause was. Same real damage-over-time, zero loot loss, zero leak risk.
- **No more zombie cage.** Earlier versions caged a zombie near the
  villagers on the theory that a nearby threat raises golem-spawn urgency.
  That's a real mechanic — on Java, where 3 panicking villagers can
  emergency-summon a golem. That panic mechanic doesn't exist on Bedrock at
  all; Bedrock's golem spawning is purely population/bed/workstation-based
  (see above), so the zombie was doing nothing except taking up space and
  materials. Removed.
- **Crop farm is a pinwheel now, not paired plots.** 4 farmer quadrants
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

**Iron Farm** — Two open rows of 10 beds facing 10 composters each (20 of
each per level) let villagers freely path between sleeping and working,
which is what actually keeps them counted as valid village members
(sealing them in isolated pods, an earlier design, silently broke this).
Levels are spaced close together (12 blocks) on purpose so every built
level merges into one combined village instead of staying separate — see
"what stackable actually means" above for why deliberately merging beats
trying to keep floors independent. No zombie cage — that's a Java-only
mechanic (see above). Golems spawn in the open-top, heavily-lit water pool
above each level (inside the village bounds); a source column on the west
wall (flows east) and one on the north wall (flows south) push everything
toward a 2-wide drain in the SE corner, and the rest of the pool fills in
from those two sources via the game's own fluid physics (a hand-filled
pool of uniform source blocks would have no current — see the
water-current notes above). Golems fall down the corner shaft onto a magma
kill pocket and take real damage over time until they die; one hopper tile
in the pocket is a direct catch point for the drops, feeding the shared
collection shaft.

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
fall down the same shaft and die the same way. A real "auto trident
killer" (a Channeling trident thrown during an actual thunderstorm) only
works while it's storming and needs a Channeling trident to begin with —
not something a static structure can keep running unattended, and not
something this addon should hand you out of nowhere either. Instead, the
kill system is the other real, always-on mechanic: a 23-block fall shaft
(past the threshold for guaranteed lethal fall damage on most mobs) into a
landing tile where a piston, driven by a 2-observer clock (two observers
facing each other perpetually retrigger one another — the standard minimal
redstone clock, no external power needed), repeatedly shoves a block in to
suffocate whatever the fall didn't already kill. A hopper floor under the
chamber catches every drop.

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
  game; a 4-level farm can take a while. If you wander far enough that
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
  above). Clearance needed: the iron farm is roughly 45 blocks tall at 4
  levels (15x15 footprint); the crop and mob farms are only ~5-7 blocks
  tall each but stretch to ~120 blocks wide at 4 units (23x23 and 15x15
  footprints per unit, 10 blocks apart) since they're built side by side on
  the ground rather than stacked.
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
    farms/ironFarm.js           Stackable iron farm layout + mechanics
    farms/ironGolemFarm.js       Single-tier wrapper around ironFarm.js
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
returning `{ placements, spawns, fills? }` in local space (see `ironFarm.js`
for a fully worked example of vertical stacking, or `cropFarm.js`/
`mobFarm.js` for side-by-side ground units). Register it in `FARMS` in
`scripts/main.js` and it shows up in the menu automatically.

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
  exactly this many (see `ironGolemFarm.js`/`pillagerOutpostFarm.js` for
  farms meant to go in one specific spot rather than being repeated).
- A `spawns` entry can include an `inventory` array of
  `{slot, itemId, amount}` to pre-fill that specific entity's own carry
  slots right after it spawns (see `giantCropFarm.js`'s farmer villager).
