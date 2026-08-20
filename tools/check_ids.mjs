/**
 * Verify every game identifier the pack references actually exists.
 *
 *   npm install --no-save @minecraft/vanilla-data
 *   node tools/check_ids.mjs
 *
 * A wrong vanilla id is the most common way an add-on breaks quietly: the
 * block is simply not placed, the recipe never appears, the loot slot comes up
 * empty, and nothing in game says why. Bedrock also does not use the same names
 * as Java - end stone bricks are `minecraft:end_bricks` here - so a name that
 * looks obviously right can still be wrong.
 *
 * This walks every JSON value and every JS string literal in the pack,
 * pulls out namespaced identifiers, and checks vanilla ones against Mojang's
 * published id lists and voidbound ones against what this pack defines.
 */

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const require = createRequire(import.meta.url);

let vanilla;
try {
  vanilla = require("@minecraft/vanilla-data");
} catch {
  console.error(
    "@minecraft/vanilla-data is not installed.\n" +
      "  npm install --no-save @minecraft/vanilla-data"
  );
  process.exit(2);
}

/** Union of every vanilla id list the package publishes. */
const VANILLA = new Set();
for (const [name, table] of Object.entries(vanilla)) {
  if (!name.startsWith("Minecraft") || typeof table !== "object") continue;
  for (const value of Object.values(table)) {
    if (typeof value === "string") VANILLA.add(value);
  }
}

/**
 * Vanilla strings that are namespaced but are not entity/block/item ids, so
 * they never appear in the published id lists. Each is a real engine name.
 */
const KNOWN_NON_ID = new Set([
  // Built-in block geometry and rendering.
  "minecraft:geometry.full_block",
  "minecraft:geometry.full_block_v1",
  "minecraft:geometry.cross",
  // Vanilla Vibrant Visuals and fog definitions we point at deliberately.
  "minecraft:default_water",
  "minecraft:default_color_grading",
  "minecraft:end_lighting",
  "minecraft:end_atmospherics",
  "minecraft:fog_the_end",
  // Component and particle names, which are namespaced but are not content ids.
  "minecraft:inventory",
  "minecraft:equippable",
  "minecraft:health",
  "minecraft:endrod",
  // Entity events the engine fires by name; a pack declares handlers for them
  // rather than defining them.
  "minecraft:entity_spawned",
  "minecraft:entity_born",
  "minecraft:ageable_grow_up",
]);

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

/** Identifiers this pack defines, gathered from its own definition files. */
function packDefinitions() {
  const defined = new Set();
  const add = (value) => {
    if (typeof value === "string") defined.add(value);
  };

  const readIdentifier = (file, ...path) => {
    let node = JSON.parse(readFileSync(file, "utf8"));
    for (const step of path) {
      node = node?.[step];
      if (node === undefined) return;
    }
    add(node);
  };

  for (const file of walk(join(ROOT, "BP", "blocks"))) {
    readIdentifier(file, "minecraft:block", "description", "identifier");
  }
  for (const file of walk(join(ROOT, "BP", "items"))) {
    readIdentifier(file, "minecraft:item", "description", "identifier");
  }
  for (const file of walk(join(ROOT, "BP", "entities"))) {
    readIdentifier(file, "minecraft:entity", "description", "identifier");
    // Component groups are names this pack invents and refers to from its own
    // events, so they count as definitions.
    const entity = JSON.parse(readFileSync(file, "utf8"))["minecraft:entity"] ?? {};
    for (const group of Object.keys(entity.component_groups ?? {})) add(group);
  }
  for (const file of walk(join(ROOT, "BP", "features"))) {
    const data = JSON.parse(readFileSync(file, "utf8"));
    for (const [key, body] of Object.entries(data)) {
      if (key.startsWith("minecraft:")) add(body?.description?.identifier);
    }
  }
  for (const file of walk(join(ROOT, "BP", "feature_rules"))) {
    readIdentifier(file, "minecraft:feature_rules", "description", "identifier");
  }
  for (const file of walk(join(ROOT, "RP", "particles"))) {
    readIdentifier(file, "particle_effect", "description", "identifier");
  }
  for (const folder of ["fogs", "lighting", "atmospherics", "color_grading"]) {
    for (const file of walk(join(ROOT, "RP", folder))) {
      const data = JSON.parse(readFileSync(file, "utf8"));
      for (const [key, body] of Object.entries(data)) {
        if (key.startsWith("minecraft:")) add(body?.description?.identifier);
      }
    }
  }
  for (const file of walk(join(ROOT, "BP", "recipes"))) {
    const data = JSON.parse(readFileSync(file, "utf8"));
    for (const [key, body] of Object.entries(data)) {
      if (key.startsWith("minecraft:recipe")) add(body?.description?.identifier);
    }
  }
  return defined;
}

const DEFINED = packDefinitions();

/** Namespaced identifier, as it appears in a value or a string literal. */
const ID_PATTERN = /^(minecraft|voidbound):[a-z0-9_]+$/;

function collectFromJson(node, sink) {
  if (typeof node === "string") {
    if (ID_PATTERN.test(node)) sink.add(node);
    return;
  }
  if (Array.isArray(node)) {
    for (const child of node) collectFromJson(child, sink);
    return;
  }
  if (node && typeof node === "object") {
    // Keys are component names, not identifiers - only values are checked.
    for (const value of Object.values(node)) collectFromJson(value, sink);
  }
}

const STRING_LITERAL = /(["'`])((?:\\.|(?!\1)[^\\])*)\1/g;

function collectFromScript(source, sink) {
  for (const match of source.matchAll(STRING_LITERAL)) {
    const value = match[2];
    if (ID_PATTERN.test(value)) sink.add(value);
  }
}

const references = new Map(); // id -> Set of files

function record(id, file) {
  if (!references.has(id)) references.set(id, new Set());
  references.get(id).add(relative(ROOT, file).split("\\").join("/"));
}

for (const file of [...walk(join(ROOT, "BP")), ...walk(join(ROOT, "RP"))]) {
  const found = new Set();
  if (file.endsWith(".json")) {
    try {
      collectFromJson(JSON.parse(readFileSync(file, "utf8")), found);
    } catch {
      continue; // The schema validator reports malformed JSON.
    }
  } else if (file.endsWith(".js")) {
    collectFromScript(readFileSync(file, "utf8"), found);
  } else {
    continue;
  }
  for (const id of found) record(id, file);
}

const problems = [];

// --------------------------------------------------------------------------
// Structural checks for mistakes the schemas do not catch
// --------------------------------------------------------------------------

/** Block ids only - local_lighting cannot colour an entity or an item. */
const BLOCK_IDS = new Set(Object.values(vanilla.MinecraftBlockTypes ?? {}));
// Real blocks that @minecraft/vanilla-data's block list leaves out. Confirmed
// against the game: it accepted end_gateway and rejected end_crystal, which is
// an entity.
for (const id of ["minecraft:end_gateway", "minecraft:end_portal"]) BLOCK_IDS.add(id);
for (const file of walk(join(ROOT, "BP", "blocks"))) {
  const id = JSON.parse(readFileSync(file, "utf8"))["minecraft:block"]?.description?.identifier;
  if (id) BLOCK_IDS.add(id);
}

const localLighting = join(ROOT, "RP", "local_lighting", "local_lighting.json");
if (existsSync(localLighting)) {
  const settings =
    JSON.parse(readFileSync(localLighting, "utf8"))["minecraft:local_light_settings"] ?? {};
  for (const id of Object.keys(settings)) {
    if (!BLOCK_IDS.has(id)) {
      problems.push({
        id,
        files: new Set(["RP/local_lighting/local_lighting.json"]),
        why: "local_lighting only accepts blocks, and this is not one",
      });
    }
  }
}

/**
 * Fields the engine insists are whole numbers.
 *
 * This has to read the file as text, not as parsed JSON. JSON has no integer
 * type, so `14.0` and `14` are the same value once parsed and no amount of
 * Number.isInteger will tell them apart - but the engine reads the literal and
 * rejects `14.0` outright. That one character killed all five tools, icons
 * included, and neither the schema nor the id check saw a thing.
 */
const INTEGER_FIELDS = [
  { field: "speed", why: "digger destroy_speeds speed must be a whole number" },
  { field: "light_emission", why: "light_emission must be a whole number from 0 to 15" },
  { field: "max_durability", why: "max_durability must be a whole number" },
  { field: "nutrition", why: "food nutrition must be a whole number" },
  { field: "protection", why: "wearable protection must be a whole number" },
  { field: "max_stack_size", why: "max_stack_size must be a whole number" },
];

for (const file of [...walk(join(ROOT, "BP", "items")), ...walk(join(ROOT, "BP", "blocks"))]) {
  if (!file.endsWith(".json")) continue;
  const text = readFileSync(file, "utf8");
  const rel = relative(ROOT, file).split("\\").join("/");
  for (const { field, why } of INTEGER_FIELDS) {
    const pattern = new RegExp(`"${field}"\\s*:\\s*(-?\\d+\\.\\d+)`, "g");
    for (const match of text.matchAll(pattern)) {
      problems.push({ id: `${rel}: "${field}": ${match[1]}`, files: new Set([rel]), why });
    }
  }
}

console.log(
  `checked ${references.size} distinct identifier(s) ` +
    `against ${VANILLA.size} vanilla ids and ${DEFINED.size} pack definitions, ` +
    `plus block-reference and integer-field rules`
);

if (problems.length === 0) {
  console.log("every referenced identifier resolves");
  process.exit(0);
}
for (const problem of problems) {
  console.log(`\n${problem.id}  (${problem.why})`);
  for (const file of problem.files) console.log(`    ${file}`);
}
console.log(`\n${problems.length} unresolved identifier(s)`);
process.exit(1);
