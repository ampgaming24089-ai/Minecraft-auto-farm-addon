/**
 * Run the pack's pure logic outside Minecraft.
 *
 *   npm install --no-save @minecraft/vanilla-data
 *   node tools/smoketest.mjs
 *
 * Most of what can go wrong in a generated structure - a blueprint that emits
 * nothing, coordinates that run away, a block id that does not exist, a chest
 * placed outside the structure - is ordinary code that happens to import
 * @minecraft/server. This stands up a stub of that module, runs the siting,
 * blueprint, and loot code against it for a few hundred seeds, and asserts the
 * output is sane, so those failures surface here instead of in a world.
 */

import {
  mkdtempSync, mkdirSync, writeFileSync, cpSync, rmSync,
  existsSync, readdirSync, readFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const require = createRequire(import.meta.url);

let vanilla;
try {
  vanilla = require("@minecraft/vanilla-data");
} catch {
  console.error("@minecraft/vanilla-data is not installed.\n  npm install --no-save @minecraft/vanilla-data");
  process.exit(2);
}

const KNOWN_IDS = new Set();
for (const [name, table] of Object.entries(vanilla)) {
  if (!name.startsWith("Minecraft") || typeof table !== "object") continue;
  for (const value of Object.values(table)) if (typeof value === "string") KNOWN_IDS.add(value);
}
// Pack-defined ids are read from the pack rather than listed here, so adding
// a block never silently breaks this test's idea of what exists.
for (const folder of ["blocks", "items"]) {
  const dir = join(ROOT, "BP", folder);
  if (!existsSync(dir)) continue;
  for (const name of readdirSync(dir)) {
    if (!name.endsWith(".json")) continue;
    const data = JSON.parse(readFileSync(join(dir, name), "utf8"));
    const id = (data["minecraft:block"] ?? data["minecraft:item"])?.description?.identifier;
    if (id) KNOWN_IDS.add(id);
  }
}

// ---------------------------------------------------------------------------
// Stub workspace
// ---------------------------------------------------------------------------

const workspace = mkdtempSync(join(tmpdir(), "voidbound-smoke-"));
const stubDir = join(workspace, "node_modules", "@minecraft", "server");
mkdirSync(stubDir, { recursive: true });
writeFileSync(
  join(stubDir, "package.json"),
  JSON.stringify({ name: "@minecraft/server", version: "0.0.0-stub", type: "module", main: "index.js" })
);
writeFileSync(
  join(stubDir, "index.js"),
  `
const KNOWN = new Set(${JSON.stringify([...KNOWN_IDS])});
export class BlockPermutation {
  constructor(type, states) { this.type = { id: type }; this.states = states; }
  static resolve(type, states) {
    if (!KNOWN.has(type)) throw new Error("unknown block id: " + type);
    return new BlockPermutation(type, states);
  }
}
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!KNOWN.has(typeId)) throw new Error("unknown item id: " + typeId);
    if (!Number.isInteger(amount) || amount < 1 || amount > 64) {
      throw new Error("bad stack size for " + typeId + ": " + amount);
    }
    this.typeId = typeId; this.amount = amount;
  }
}
export const EntityDamageCause = new Proxy({}, { get: (_t, name) => String(name) });
export const EquipmentSlot = new Proxy({}, { get: (_t, name) => String(name) });
export const dimensionStub = {
  id: "minecraft:the_end",
  getPlayers: () => [],
  getEntities: () => [],
  spawnParticle: () => {},
  spawnEntity: () => {},
  isChunkLoaded: () => false,
  getTopmostBlock: () => undefined,
  getBlock: () => undefined,
};
export const world = {
  seed: "1234567890",
  getAllPlayers: () => [],
  getDimension: () => dimensionStub,
  sendMessage: () => {},
  getDynamicProperty: () => undefined,
  setDynamicProperty: () => {},
  afterEvents: new Proxy({}, { get: () => ({ subscribe() {}, unsubscribe() {} }) }),
  beforeEvents: new Proxy({}, { get: () => ({ subscribe() {}, unsubscribe() {} }) }),
};
export const system = {
  currentTick: 0,
  runInterval: () => 0,
  runTimeout: () => 0,
  runJob: () => 0,
  run: () => 0,
  clearRun: () => {},
};
`
);

// The UI module is only ever constructed inside an interaction, so a stub that
// records nothing is enough to prove the import resolves.
const uiStubDir = join(workspace, "node_modules", "@minecraft", "server-ui");
mkdirSync(uiStubDir, { recursive: true });
writeFileSync(
  join(uiStubDir, "package.json"),
  JSON.stringify({ name: "@minecraft/server-ui", version: "0.0.0-stub", type: "module", main: "index.js" })
);
writeFileSync(
  join(uiStubDir, "index.js"),
  `
class Form {
  title() { return this; }
  body() { return this; }
  button() { return this; }
  show() { return Promise.resolve({ canceled: true }); }
}
export class ActionFormData extends Form {}
export class MessageFormData extends Form {}
export class ModalFormData extends Form {}
`
);
cpSync(join(ROOT, "BP", "scripts"), join(workspace, "scripts"), { recursive: true });

const load = (relPath) => import(pathToFileURL(join(workspace, "scripts", relPath)).href);

// ---------------------------------------------------------------------------
// Assertions
// ---------------------------------------------------------------------------

let checks = 0;
const failures = [];

function check(label, condition, detail = "") {
  checks += 1;
  if (!condition) failures.push(`${label}${detail ? ` - ${detail}` : ""}`);
}

try {
  const { Rng, hash } = await load("lib/rng.js");
  const { siteInCell, sitesNear, CELL_SIZE } = await load("world/sites.js");
  const { STRUCTURES } = await load("structures/index.js");
  const { rollChest } = await load("content/loot.js");
  const { bearingFrom } = await load("content/riftCompass.js");
  const { rotate } = await load("lib/vec.js");

  // --- randomness is reproducible -----------------------------------------
  const first = Array.from({ length: 8 }, (_, i) => new Rng(hash(1, i)).next());
  const second = Array.from({ length: 8 }, (_, i) => new Rng(hash(1, i)).next());
  check("rng is deterministic", first.every((v, i) => v === second[i]));
  check("rng stays in range", first.every((v) => v >= 0 && v < 1));

  // --- siting --------------------------------------------------------------
  let siteCount = 0;
  const seen = new Set();
  for (let cx = -14; cx <= 14; cx++) {
    for (let cz = -14; cz <= 14; cz++) {
      const site = siteInCell(cx, cz);
      const repeat = siteInCell(cx, cz);
      if (!site) {
        check("empty cells stay empty", repeat === undefined, `${cx},${cz}`);
        continue;
      }
      siteCount += 1;
      check("siting is deterministic", repeat && repeat.x === site.x && repeat.z === site.z, site.key);
      check("site keys are unique", !seen.has(site.key), site.key);
      seen.add(site.key);
      check(
        "site sits inside its own cell",
        Math.floor(site.x / CELL_SIZE) === cx && Math.floor(site.z / CELL_SIZE) === cz,
        site.key
      );
      check(
        "site clears the central island",
        Math.hypot(site.x, site.z) >= 1100,
        `${site.key} at ${Math.round(Math.hypot(site.x, site.z))}`
      );
      check("site has a blueprint", typeof site.blueprint?.build === "function", site.key);
    }
  }
  check("cells actually produce sites", siteCount > 100, `only ${siteCount}`);

  const near = sitesNear(20000, 20000, 2);
  check("sitesNear returns something", near.length > 0);
  const distances = near.map((s) => Math.hypot(s.x - 20000, s.z - 20000));
  check(
    "sitesNear is sorted by distance",
    distances.every((d, i) => i === 0 || d >= distances[i - 1])
  );

  // --- blueprints ----------------------------------------------------------
  for (const { blueprint } of STRUCTURES) {
    let minPlacements = Infinity;
    let maxPlacements = 0;
    for (let seed = 1; seed <= 200; seed++) {
      const rng = new Rng(hash(seed, 77));
      let plan;
      try {
        plan = blueprint.build(rng);
      } catch (error) {
        failures.push(`${blueprint.id} threw on seed ${seed}: ${error.message}`);
        checks += 1;
        continue;
      }
      checks += 1;

      const placements = plan.placements;
      check(`${blueprint.id} returns placements`, Array.isArray(placements) && placements.length > 0, `seed ${seed}`);
      if (!Array.isArray(placements) || placements.length === 0) continue;
      minPlacements = Math.min(minPlacements, placements.length);
      maxPlacements = Math.max(maxPlacements, placements.length);

      let bad = null;
      for (const p of placements) {
        if (
          !Number.isInteger(p.x) || !Number.isInteger(p.y) || !Number.isInteger(p.z) ||
          typeof p.id !== "string"
        ) {
          bad = `non-integer or untyped placement ${JSON.stringify(p)}`;
          break;
        }
        if (Math.abs(p.x) > 64 || Math.abs(p.z) > 64 || p.y < -24 || p.y > 96) {
          bad = `placement out of bounds ${JSON.stringify(p)}`;
          break;
        }
        if (!KNOWN_IDS.has(p.id)) {
          bad = `unknown block id ${p.id}`;
          break;
        }
      }
      check(`${blueprint.id} placements are sane`, bad === null, `seed ${seed}: ${bad ?? ""}`);

      // Checked separately so an early exit above cannot skew the count.
      const occupied = new Set(placements.map((p) => `${p.x},${p.y},${p.z}`));
      check(
        `${blueprint.id} has no duplicate coordinates`,
        occupied.size === placements.length,
        `seed ${seed}: ${placements.length - occupied.size} duplicate(s)`
      );

      for (const chest of plan.chests ?? []) {
        const key = `${chest.x},${chest.y},${chest.z}`;
        const placed = placements.find((p) => `${p.x},${p.y},${p.z}` === key);
        check(
          `${blueprint.id} chest sits on a container`,
          placed !== undefined && /chest|barrel/.test(placed.id),
          `seed ${seed}: ${key} holds ${placed?.id ?? "nothing"}`
        );
        // Rotation must keep the chest attached to the structure.
        for (const facing of ["north", "east", "south", "west"]) {
          const spun = rotate(chest, facing);
          check(
            `${blueprint.id} chest survives rotation`,
            Number.isInteger(spun.x) && Number.isInteger(spun.z),
            facing
          );
        }
      }
    }
    check(
      `${blueprint.id} stays a reasonable size`,
      minPlacements > 40 && maxPlacements < 40000,
      `${minPlacements}..${maxPlacements} blocks`
    );
  }

  // --- loot ----------------------------------------------------------------
  for (let seed = 1; seed <= 120; seed++) {
    const rng = new Rng(hash(seed, 991));
    const distance = seed * 400;
    const items = rollChest(rng, distance);
    checks += 1;
    const slots = new Set(items.map((entry) => entry.slot));
    check("chest slots are unique", slots.size === items.length, `seed ${seed}`);
    check(
      "chest slots are in range",
      items.every((entry) => entry.slot >= 0 && entry.slot < 27),
      `seed ${seed}`
    );
    check("chest is not empty", items.length > 0, `seed ${seed}`);
  }

  // --- biomes --------------------------------------------------------------
  // The whole illusion rests on biomeAt being a pure function of the seed: if
  // it drifts, two players on one world stand in different biomes, the fog
  // disagrees with the ground, and the painter repaints the same patch twice.
  {
    const { biomeAt, BIOMES, BIOME_CELL, borderProximity } = await load("world/biomes.js");

    check("biomeAt is deterministic", (() => {
      for (let i = 0; i < 400; i++) {
        const x = (i * 977) % 40000 - 20000;
        const z = (i * 1483) % 40000 - 20000;
        if (biomeAt(x, z).id !== biomeAt(x, z).id) return false;
      }
      return true;
    })());

    check("biomeAt always returns a table entry", (() => {
      for (let i = 0; i < 2000; i++) {
        const x = (i * 613) % 60000 - 30000;
        const z = (i * 8117) % 60000 - 30000;
        const biome = biomeAt(x, z);
        if (!biome || BIOMES[biome.id] !== biome) return false;
      }
      return true;
    })());

    // Vanilla's island, the pillars and the gateway have to stay untouched,
    // and the Barrens are the biome that paints nothing.
    check("the origin stays vanilla", (() => {
      for (let a = 0; a < 32; a++) {
        const angle = (a / 32) * Math.PI * 2;
        for (const r of [0, 200, 500, 850]) {
          const biome = biomeAt(Math.cos(angle) * r, Math.sin(angle) * r);
          if (biome.id !== "barrens" || biome.surface !== undefined) return false;
        }
      }
      return true;
    })());

    // Every biome must be reachable, or a whole set of art ships unseen.
    {
      const seen = new Set();
      for (let i = 0; i < 20000; i++) {
        seen.add(biomeAt((i * 1301) % 90000 - 45000, (i * 7919) % 90000 - 45000).id);
      }
      for (const id of Object.keys(BIOMES)) {
        check(`biome ${id} actually occurs`, seen.has(id));
      }
    }

    // Regions have to be big enough to stand in. Walking a straight line, a
    // biome that changes every few steps is a patchwork, not a place.
    {
      let runs = 0;
      let previous;
      for (let x = 2000; x < 42000; x += 16) {
        const id = biomeAt(x, 3000).id;
        if (id !== previous) runs += 1;
        previous = id;
      }
      const averageRun = 40000 / Math.max(1, runs);
      check("biome runs are region-sized", averageRun > BIOME_CELL * 0.4,
        `average run ${Math.round(averageRun)} blocks over 40k`);
    }

    // Borders must not be straight: a warp that fails silently gives square
    // biomes, which look exactly as generated as they are.
    {
      let straight = 0;
      let checked = 0;
      for (let z = 4000; z < 20000; z += 64) {
        let edgeX;
        let previous = biomeAt(4000, z).id;
        for (let x = 4000; x < 12000; x += 16) {
          const id = biomeAt(x, z).id;
          if (id !== previous) { edgeX = x; break; }
          previous = id;
        }
        if (edgeX === undefined) continue;
        checked += 1;
        // A square grid would put every border on a multiple of the cell size.
        if (Math.abs(edgeX % BIOME_CELL) < 32) straight += 1;
      }
      check("biome borders are warped, not gridded",
        checked > 8 && straight / checked < 0.3, `${straight}/${checked} on the grid`);
    }

    check("borderProximity flags a border", (() => {
      // Somewhere inside a region it should read 1; the sweep below must find
      // at least one spot where it reads 0, or the fade never fires.
      let sawEdge = false;
      let sawInside = false;
      for (let i = 0; i < 3000; i++) {
        const value = borderProximity((i * 613) % 40000 - 20000, (i * 1471) % 40000 - 20000);
        if (value === 0) sawEdge = true;
        if (value === 1) sawInside = true;
      }
      return sawEdge && sawInside;
    })());

    // Every id the table names has to exist, or the painter places nothing
    // and the fog push silently fails.
    for (const biome of Object.values(BIOMES)) {
      for (const id of [biome.surface, biome.filler].filter(Boolean)) {
        check(`${biome.id} surface ${id} exists`, KNOWN_IDS.has(id));
      }
      for (const entry of biome.flora ?? []) {
        check(`${biome.id} flora ${entry.id} exists`, KNOWN_IDS.has(entry.id));
        check(`${biome.id} flora ${entry.id} has weight`, entry.weight > 0);
      }
      // A biome that paints ground but hangs nothing leaves its islands
      // stopping dead at the bottom face, which is the thing this was for.
      if (biome.surface) {
        check(`${biome.id} hangs something underneath`, typeof biome.hanging === "string");
        if (biome.hanging) check(`${biome.id} hanging ${biome.hanging} exists`, KNOWN_IDS.has(biome.hanging));
      }
      check(`${biome.id} has a name`, typeof biome.name === "string" && biome.name.length > 0);
      check(`${biome.id} has a colour code`, /^§[0-9a-fk-or]$/.test(biome.colour));
      if (biome.particle) {
        check(`${biome.id} sets particleLift`, typeof biome.particleLift === "number");
      }
    }
  }

  // --- trees ---------------------------------------------------------------
  {
    const { TREES } = await load("world/trees.js");
    const { BIOMES } = await load("world/biomes.js");

    // A biome naming a species that does not exist grows nothing at all, and
    // silently: the painter's try/catch swallows it and the ground still gets
    // painted, so the region just never has any trees.
    for (const biome of Object.values(BIOMES)) {
      if (!biome.tree) continue;
      check(`biome ${biome.id} names a real tree species`,
        Boolean(TREES[biome.tree]), biome.tree);
      check(`biome ${biome.id} plants at a sane rate`,
        biome.treeChance > 0 && biome.treeChance < 0.2, `${biome.treeChance}`);
    }

    // Colour alone does not distinguish a species - a violet canopy and a
    // green one are the same tree tinted. The crowns have to be different
    // shapes, so assert the shapes are actually distinct.
    const crowns = new Set(Object.values(TREES).map((tree) => tree.canopy));
    check("every species has a distinct crown", crowns.size === Object.keys(TREES).length,
      `${crowns.size} of ${Object.keys(TREES).length}`);

    for (const [key, tree] of Object.entries(TREES)) {
      check(`${key} names its own log and leaves`,
        tree.log.includes(key) && tree.leaves.includes(key));
      check(`${key} has a sane height range`,
        tree.height[0] >= 3 && tree.height[1] <= 16 && tree.height[0] < tree.height[1],
        `${tree.height}`);
    }
  }

  // --- sky islands -----------------------------------------------------------
  // These hang in air a player will fly through, so the two things that matter
  // are that siting is stable and that nothing lands on vanilla's island.
  {
    const { islandInCell, islandsNear, shape } = await load("world/skyIslands.js");

    check("island siting is deterministic", (() => {
      for (let i = -200; i < 200; i++) {
        const a = islandInCell(i, i * 3);
        const b = islandInCell(i, i * 3);
        if (JSON.stringify(a) !== JSON.stringify(b)) return false;
      }
      return true;
    })());

    {
      let sited = 0;
      let cells = 0;
      let tooLow = 0;
      let tooHigh = 0;
      let nearOrigin = 0;
      let badRadius = 0;
      for (let cx = -60; cx < 60; cx++) {
        for (let cz = -60; cz < 60; cz++) {
          cells += 1;
          const island = islandInCell(cx, cz);
          if (!island) continue;
          sited += 1;
          if (island.y < 96) tooLow += 1;
          if (island.y > 210) tooHigh += 1;
          if (Math.hypot(island.x, island.z) < 900) nearOrigin += 1;
          if (!(island.radius >= 9 && island.radius <= 32)) badRadius += 1;
        }
      }
      const rate = sited / cells;
      check("islands are sited at roughly the intended rate",
        rate > 0.2 && rate < 0.4, `${(rate * 100).toFixed(1)}%`);
      check("no island sits below the band", tooLow === 0, `${tooLow} too low`);
      check("no island sits above the band", tooHigh === 0, `${tooHigh} too high`);
      // The main island, the pillars, the gateway and the arena all live here.
      check("no island generates near the origin", nearOrigin === 0, `${nearOrigin} inside`);
      check("island radii are sane", badRadius === 0, `${badRadius} out of range`);
      // The cubed roll is what makes most islands middling and a few enormous.
      // A flat distribution here would mean the sky is all landmasses.
      {
        let big = 0;
        for (let cx = -14; cx <= 14; cx++) {
          for (let cz = -14; cz <= 14; cz++) {
            const island = islandInCell(cx, cz);
            if (island && island.radius > 20) big += 1;
          }
        }
        check("large islands are the exception", big < sited * 0.25,
          `${big} of ${sited} over radius 20`);
      }
    }

    // The islands were asked to be bigger and deeper, and "deeper" is the half
    // that is easy to lose: a wider saucer is still a saucer. So the profile
    // itself is asserted, not just the radius that feeds it.
    {
      const rng = { next: () => 0.5, chance: () => false, int: (a) => a,
                    float: (a) => a };
      const island = { radius: 20, x: 0, y: 120, z: 0 };
      let low = 0;
      let high = 0;
      let count = 0;
      for (const cell of shape(island, rng)) {
        low = Math.min(low, cell.dy);
        high = Math.max(high, cell.dy);
        count += 1;
      }
      check("an island hangs well below its own surface", low <= -40, `${low}`);
      check("an island has a domed top", high >= 3, `+${high}`);
      // A solid island of this size is ~24k block writes and the runJob would
      // still be laying it down long after the player has flown past.
      check("a large island is built as a shell", count < 14000, `${count} blocks`);
    }

    check("islandsNear finds what islandInCell sites", (() => {
      const near = islandsNear(5000, 5000, 2);
      if (near.length === 0) return true; // A quiet patch is legitimate.
      return near.every((island) => Math.hypot(island.x - 5000, island.z - 5000) < 500);
    })());
  }

  // --- the painter only ever replaces worldgen ------------------------------
  // The painter is the one system that rewrites ground a player might care
  // about, so what it is willing to overwrite is worth asserting rather than
  // trusting. A biome surface appearing in NATURAL would mean a player's own
  // glowspore floor could be repainted out from under them.
  {
    const source = readFileSync(join(ROOT, "BP", "scripts", "world", "painter.js"), "utf8");
    const listed = new Set(
      [...source.matchAll(/const NATURAL = new Set\(\[([^\]]*)\]/gs)]
        .flatMap((match) => [...match[1].matchAll(/"([^"]+)"/g)].map((entry) => entry[1]))
    );
    check("painter has a NATURAL list", listed.size > 0);
    for (const id of listed) {
      check(`painter replaceable ${id} exists`, KNOWN_IDS.has(id));
    }
    const { BIOMES } = await load("world/biomes.js");
    for (const biome of Object.values(BIOMES)) {
      if (!biome.surface) continue;
      // verdant and mossy end stone predate the biomes and are placed by
      // worldgen features, so those two are legitimately in both lists.
      if (biome.surface === "voidbound:verdant_end_stone") continue;
      check(`painter will not overwrite ${biome.surface}`, !listed.has(biome.surface));
    }
    check("painter marks a patch only when it completed",
      /if \(report\.complete\) markPainted/.test(source));
  }

  // --- every system starts without throwing --------------------------------
  // A module that throws at import or at start takes the entire script pack
  // offline in game, with nothing in the content log pointing at the cause.
  const ENTRY_POINTS = [
    ["content/armorSet.js", "startArmorSet"],
    ["content/emotes.js", "startEmotes"],
    ["content/bloomstalk.js", "startBloomstalk"],
    ["content/enderSapling.js", "startEnderSapling"],
    ["content/mobActions.js", "startMobActions"],
    ["content/riftCompass.js", "startRiftCompass"],
    ["content/riftSovereign.js", "startRiftSovereign"],
    ["content/utilityItems.js", "startUtilityItems"],
    ["content/voidTitan.js", "startVoidTitan"],
    ["content/waystones.js", "startWaystones"],
    ["world/ambience.js", "startAmbience"],
    ["world/atmosphere.js", "startAtmosphere"],
    ["world/biomeLife.js", "startBiomeLife"],
    ["world/discovery.js", "startDiscovery"],
    ["world/flightControl.js", "startFlightControl"],
    ["world/generator.js", "startGenerator"],
    ["world/painter.js", "startPainter"],
    ["world/skyIslands.js", "startSkyIslands"],
  ];
  for (const [relPath, exportName] of ENTRY_POINTS) {
    let module;
    try {
      module = await load(relPath);
    } catch (error) {
      check(`${relPath} imports`, false, String(error));
      continue;
    }
    check(`${relPath} imports`, true);
    check(`${relPath} exports ${exportName}`, typeof module[exportName] === "function");
    if (typeof module[exportName] !== "function") continue;
    try {
      module[exportName]();
      check(`${exportName}() runs`, true);
    } catch (error) {
      check(`${exportName}() runs`, false, String(error));
    }
  }

  // main.js must list every one of them, or a system silently never starts.
  const mainSource = readFileSync(join(ROOT, "BP", "scripts", "main.js"), "utf8");
  for (const [, exportName] of ENTRY_POINTS) {
    check(`main.js imports ${exportName}`, mainSource.includes(`import { ${exportName} }`));
    check(`main.js calls ${exportName}`, mainSource.includes(`${exportName}();`));
  }

  // --- compass bearings ----------------------------------------------------
  check("north is -z", bearingFrom(0, -100) === "north");
  check("south is +z", bearingFrom(0, 100) === "south");
  check("east is +x", bearingFrom(100, 0) === "east");
  check("west is -x", bearingFrom(-100, 0) === "west");
  check("north-east is +x -z", bearingFrom(100, -100) === "north-east");
  check("south-west is -x +z", bearingFrom(-100, 100) === "south-west");
} finally {
  rmSync(workspace, { recursive: true, force: true });
}

const unique = [...new Set(failures)];
console.log(`ran ${checks} checks`);
if (unique.length === 0) {
  console.log("all script logic checks passed");
  process.exit(0);
}
for (const failure of unique.slice(0, 25)) console.log(`  FAIL ${failure}`);
if (unique.length > 25) console.log(`  ... and ${unique.length - 25} more`);
process.exit(1);
