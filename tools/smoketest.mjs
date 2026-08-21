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

  // --- every system starts without throwing --------------------------------
  // A module that throws at import or at start takes the entire script pack
  // offline in game, with nothing in the content log pointing at the cause.
  const ENTRY_POINTS = [
    ["content/armorSet.js", "startArmorSet"],
    ["content/emotes.js", "startEmotes"],
    ["content/enderSapling.js", "startEnderSapling"],
    ["content/mobActions.js", "startMobActions"],
    ["content/riftCompass.js", "startRiftCompass"],
    ["content/riftSovereign.js", "startRiftSovereign"],
    ["content/utilityItems.js", "startUtilityItems"],
    ["content/voidTitan.js", "startVoidTitan"],
    ["content/waystones.js", "startWaystones"],
    ["world/ambience.js", "startAmbience"],
    ["world/atmosphere.js", "startAtmosphere"],
    ["world/discovery.js", "startDiscovery"],
    ["world/flightControl.js", "startFlightControl"],
    ["world/generator.js", "startGenerator"],
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
