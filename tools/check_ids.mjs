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

/**
 * Blocks named by other blocks: placement filters, and the `name` of any
 * block_filter entry anywhere in a definition.
 *
 * A sapling whose placement_filter names a block that does not exist is a
 * sapling that cannot be placed on anything, and the game says nothing at all
 * about it - it simply refuses every block the player tries. This shipped
 * once, as `voidbound:aurora_end_stone` against a block actually called
 * `voidbound:aurora_stone`, and nothing in the harness saw it.
 */
for (const file of walk(join(ROOT, "BP", "blocks"))) {
  const rel = relative(ROOT, file).split("\\").join("/");
  let definition;
  try {
    definition = JSON.parse(readFileSync(file, "utf8"));
  } catch {
    continue;
  }
  const named = [];
  const visit = (node) => {
    if (Array.isArray(node)) {
      for (const item of node) visit(item);
      return;
    }
    if (!node || typeof node !== "object") return;
    for (const [key, value] of Object.entries(node)) {
      if (key === "block_filter" && Array.isArray(value)) {
        for (const entry of value) {
          const id = typeof entry === "string" ? entry : entry?.name;
          if (typeof id === "string") named.push(id);
        }
      } else {
        visit(value);
      }
    }
  };
  visit(definition);
  for (const id of named) {
    // A tag filter is a tag, not a block id.
    if (id.startsWith("#") || !id.includes(":")) continue;
    if (BLOCK_IDS.has(id)) continue;
    problems.push({
      id,
      files: new Set([rel]),
      why: "a block_filter names this block, and no such block exists",
    });
  }
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

/**
 * Client entities must resolve every name they mention.
 *
 * A client entity is four cross-references held together by string matching -
 * a geometry identifier, animation identifiers, a render controller and
 * texture paths. Get any one wrong and the mob renders as a blank white cube
 * or nothing at all, with no error anywhere in the content log. That is
 * exactly the failure this whole tool exists to catch, so it is checked here
 * rather than left to a play session.
 */
function collectIdentifiers(dir, topKey, listKey) {
  const found = new Set();
  if (!existsSync(dir)) return found;
  for (const file of walk(dir)) {
    if (!file.endsWith(".json")) continue;
    let data;
    try {
      data = JSON.parse(readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    if (listKey) {
      for (const key of Object.keys(data[listKey] ?? {})) found.add(key);
      continue;
    }
    for (const entry of Array.isArray(data[topKey]) ? data[topKey] : [data[topKey]]) {
      const id = entry?.description?.identifier;
      if (id) found.add(id);
    }
  }
  return found;
}

const GEOMETRIES = new Set();
for (const file of walk(join(ROOT, "RP", "models"))) {
  if (!file.endsWith(".json")) continue;
  let data;
  try {
    data = JSON.parse(readFileSync(file, "utf8"));
  } catch {
    continue;
  }
  for (const entry of data["minecraft:geometry"] ?? []) {
    const id = entry?.description?.identifier;
    if (id) GEOMETRIES.add(id);
  }
  // The 1.8 format keys geometry by identifier at the top level.
  for (const key of Object.keys(data)) if (key.startsWith("geometry.")) GEOMETRIES.add(key);
}

const ANIMATIONS = collectIdentifiers(join(ROOT, "RP", "animations"), null, "animations");
const CONTROLLERS = new Set([
  ...collectIdentifiers(join(ROOT, "RP", "render_controllers"), null, "render_controllers"),
  ...collectIdentifiers(join(ROOT, "RP", "animation_controllers"), null, "animation_controllers"),
]);

/**
 * Animation controllers name their clips by the *short* name the client entity
 * gives them, not by identifier. A typo there resolves to nothing and the state
 * silently plays no animation, which looks exactly like a controller that never
 * fires. So collect what each controller asks for, and check it below against
 * the entities that actually run that controller.
 */
const CONTROLLER_WANTS = new Map();
const AC_DIR = join(ROOT, "RP", "animation_controllers");
if (existsSync(AC_DIR)) {
  for (const file of walk(AC_DIR)) {
    if (!file.endsWith(".json")) continue;
    let data;
    try {
      data = JSON.parse(readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    for (const [id, controller] of Object.entries(data.animation_controllers ?? {})) {
      const wants = new Set();
      for (const state of Object.values(controller.states ?? {})) {
        for (const entry of state.animations ?? []) {
          wants.add(typeof entry === "string" ? entry : Object.keys(entry)[0]);
        }
      }
      CONTROLLER_WANTS.set(id, wants);
    }
  }
}

/**
 * Vanilla client assets a *custom* entity may legitimately point at.
 *
 * A reskinned enderman is built by naming Mojang's own skeleton and clips
 * rather than shipping copies of them, so these ids resolve at runtime out of
 * the vanilla resource pack and will never be found under RP/. The exemption
 * is deliberately a list rather than a prefix match: a typo in
 * `animation.humaniod.move` should still be an error, and it is, because it is
 * not on it.
 */
const VANILLA_CLIENT_ASSETS = new Set([
  "geometry.enderman.v1.8",
  "geometry.villager_v2",
  "geometry.humanoid.custom",
  "animation.humanoid.move",
  "animation.humanoid.riding.arms",
  "animation.humanoid.riding.legs",
  "animation.humanoid.attack.rotations",
  "animation.enderman.scary_face",
  "controller.animation.humanoid.look_at_target",
  "controller.animation.humanoid.move",
]);

const ENTITY_DIR = join(ROOT, "RP", "entity");
if (existsSync(ENTITY_DIR)) {
  for (const file of walk(ENTITY_DIR)) {
    if (!file.endsWith(".json")) continue;
    const rel = relative(ROOT, file).split("\\").join("/");
    let description;
    try {
      description = JSON.parse(readFileSync(file, "utf8"))["minecraft:client_entity"]?.description;
    } catch {
      continue;
    }
    if (!description) continue;

    // A `minecraft:*` client entity is an override of a vanilla one, so most of
    // what it names lives in the vanilla pack and cannot be resolved from here.
    // Only the identifiers this pack actually owns are checkable, which is
    // still the part that can be wrong: our own clips, controllers and art.
    const isOverride = String(description.identifier ?? "").startsWith("minecraft:");
    const ours = (id) => /(^|\.)(voidbound|voidbound)(\.|:)/.test(id) || id.includes("voidbound_");
    const skip = (id) => isOverride && !ours(id);

    const note = (what, why) => problems.push({ id: `${rel}: ${what}`, files: new Set([rel]), why });

    for (const geometry of Object.values(description.geometry ?? {})) {
      if (skip(geometry) || VANILLA_CLIENT_ASSETS.has(geometry)) continue;
      if (!GEOMETRIES.has(geometry)) note(geometry, "no such geometry in RP/models");
    }
    for (const animation of Object.values(description.animations ?? {})) {
      // A value that is not an identifier is a Molang expression, not a clip.
      if (!animation.startsWith("animation.") && !animation.startsWith("controller.")) continue;
      if (skip(animation) || VANILLA_CLIENT_ASSETS.has(animation)) continue;
      if (!ANIMATIONS.has(animation) && !CONTROLLERS.has(animation)) {
        note(animation, "no such animation in RP/animations");
      }
    }
    for (const controller of description.render_controllers ?? []) {
      const id = typeof controller === "string" ? controller : Object.keys(controller)[0];
      if (!id || skip(id)) continue;
      if (!CONTROLLERS.has(id)) note(id, "no such render controller in RP/render_controllers");
    }
    for (const texture of Object.values(description.textures ?? {})) {
      if (skip(texture)) continue;
      if (!existsSync(join(ROOT, "RP", `${texture}.png`))) {
        note(texture, "no such texture file under RP/");
      }
    }
    // Every short name our controllers ask for must exist in this entity's map.
    for (const target of Object.values(description.animations ?? {})) {
      const wants = CONTROLLER_WANTS.get(target);
      if (!wants) continue;
      for (const shortName of wants) {
        if (!(shortName in (description.animations ?? {}))) {
          note(`${target} plays "${shortName}"`, "that short name is not in this entity's animations map");
        }
      }
    }

    // A clip never plays unless something reaches it: either scripts.animate
    // lists it directly, or a controller that *is* listed asks for it by short
    // name. Both count as reachable - only a clip nothing reaches is a bug.
    const animated = new Set(
      (description.scripts?.animate ?? []).map((entry) =>
        typeof entry === "string" ? entry : Object.keys(entry)[0]
      )
    );
    for (const name of [...animated]) {
      const wants = CONTROLLER_WANTS.get(description.animations?.[name]);
      if (wants) for (const shortName of wants) animated.add(shortName);
    }
    if (!isOverride) {
      for (const name of Object.keys(description.animations ?? {})) {
        if (!animated.has(name)) note(`animations.${name}`, "declared but never listed in scripts.animate");
      }
    } else {
      // For an override, the equivalent check is that every controller we added
      // to scripts.animate resolves to a controller we actually ship.
      for (const name of animated) {
        const target = description.animations?.[name];
        if (!target || !ours(target)) continue;
        if (!CONTROLLERS.has(target) && !ANIMATIONS.has(target)) {
          note(`scripts.animate ${name} -> ${target}`, "no such animation or controller in this pack");
        }
      }
    }
  }
}

/**
 * Animation identifiers named from script.
 *
 * `/playanimation` takes a clip by identifier, and a typo there is a command
 * that fails quietly - no error, no pose, nothing to notice until somebody
 * wonders why the emote never fires. Any `animation.` or `controller.` literal
 * in this pack's namespaces has to resolve to something the pack ships.
 */
const SCRIPT_DIR = join(ROOT, "BP", "scripts");
if (existsSync(SCRIPT_DIR)) {
  const pattern = /\b((?:controller\.)?animation\.(?:voidbound|voidbound)[A-Za-z0-9_.]*)/g;
  for (const file of walk(SCRIPT_DIR)) {
    if (!file.endsWith(".js")) continue;
    const rel = relative(ROOT, file).split("\\").join("/");
    for (const match of readFileSync(file, "utf8").matchAll(pattern)) {
      const id = match[1];
      if (ANIMATIONS.has(id) || CONTROLLERS.has(id)) continue;
      problems.push({
        id: `${rel}: ${id}`,
        files: new Set([rel]),
        why: "no such animation or controller in the resource pack",
      });
    }
  }
}

/**
 * Animation files have no schema in the package, so nothing else looks at
 * them - and by now they are the largest hand-shaped part of the pack. These
 * rules cover the mistakes that are silent in game: a vector of the wrong
 * length, a keyframe time that is not a time, a non-looping clip with no
 * length (which holds its last pose for ever), and a script that stops a clip
 * before the clip is finished.
 */
const CHANNELS = new Set(["rotation", "position", "scale"]);
const CLIP_LENGTHS = new Map();

for (const file of walk(join(ROOT, "RP", "animations"))) {
  if (!file.endsWith(".json")) continue;
  const rel = relative(ROOT, file).split("\\").join("/");
  let data;
  try {
    data = JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    problems.push({ id: `${rel}`, files: new Set([rel]), why: `not valid JSON: ${error}` });
    continue;
  }
  const note = (what, why) => problems.push({ id: `${rel}: ${what}`, files: new Set([rel]), why });

  for (const [clipId, clip] of Object.entries(data.animations ?? {})) {
    const looping = clip.loop === true;
    if (!looping && typeof clip.animation_length !== "number") {
      note(clipId, "a non-looping clip needs animation_length, or its last pose holds for ever");
    }
    if (typeof clip.animation_length === "number") CLIP_LENGTHS.set(clipId, clip.animation_length);

    for (const [bone, channels] of Object.entries(clip.bones ?? {})) {
      for (const [channel, value] of Object.entries(channels)) {
        if (!CHANNELS.has(channel)) {
          note(`${clipId} ${bone}.${channel}`, "not a rotation, position or scale channel");
          continue;
        }
        // Either a single vector, or a map of time -> vector.
        const frames = Array.isArray(value) ? { "0.0": value } : value;
        if (typeof frames !== "object" || frames === null) {
          note(`${clipId} ${bone}.${channel}`, "expected a vector or a keyframe map");
          continue;
        }
        let last = -Infinity;
        for (const [time, vector] of Object.entries(frames)) {
          if (!Array.isArray(value)) {
            const t = Number(time);
            if (!Number.isFinite(t) || t < 0) {
              note(`${clipId} ${bone}.${channel} @${time}`, "keyframe key is not a time in seconds");
            } else {
              if (t < last) {
                note(`${clipId} ${bone}.${channel} @${time}`, "keyframes are out of order");
              }
              last = t;
              if (typeof clip.animation_length === "number" && t > clip.animation_length + 1e-6) {
                note(`${clipId} ${bone}.${channel} @${time}`,
                  `keyframe lands past animation_length ${clip.animation_length}, so it never plays`);
              }
            }
          }
          const vec = Array.isArray(vector) ? vector : vector?.post ?? vector?.pre;
          if (!Array.isArray(vec) || vec.length !== 3) {
            note(`${clipId} ${bone}.${channel} @${time}`, "expected a 3-component vector");
            continue;
          }
          for (const component of vec) {
            if (typeof component === "number") continue;
            if (typeof component === "string" && component.length > 0) continue;
            note(`${clipId} ${bone}.${channel} @${time}`, "component is neither a number nor a Molang string");
          }
        }
      }
    }
  }
}

/**
 * A script that plays a clip passes a stop time. Stopping early cuts the clip
 * off mid-pose and leaves the skeleton wherever it happened to be, so the stop
 * time has to be at least as long as the clip itself.
 */
for (const file of walk(join(ROOT, "BP", "scripts"))) {
  if (!file.endsWith(".js")) continue;
  const rel = relative(ROOT, file).split("\\").join("/");
  const text = readFileSync(file, "utf8");

  // The per-clip tables: { clip: "animation....", length: 1.8, ... }
  const tabled = /clip:\s*"((?:controller\.)?animation\.[A-Za-z0-9_.]+)"\s*,\s*length:\s*([0-9.]+)/g;
  for (const match of text.matchAll(tabled)) {
    const declared = CLIP_LENGTHS.get(match[1]);
    if (declared === undefined) continue;
    if (Number(match[2]) + 1e-6 < declared) {
      problems.push({
        id: `${rel}: ${match[1]} stopped at ${match[2]}s`,
        files: new Set([rel]),
        why: `the clip runs ${declared}s, so this cuts it off mid-pose`,
      });
    }
  }

  // The shared-constant form: one stop time covering a family of clips.
  for (const [constant, prefix] of [["ATTACK_SECONDS", ".attack"], ["HURT_SECONDS", ".hurt"]]) {
    const declared = new RegExp(`const ${constant} = ([0-9.]+)`).exec(text);
    if (!declared) continue;
    const stop = Number(declared[1]);
    for (const [clipId, length] of CLIP_LENGTHS) {
      if (!clipId.endsWith(prefix)) continue;
      if (!text.includes(clipId)) continue;
      if (stop + 1e-6 < length) {
        problems.push({
          id: `${rel}: ${constant} = ${stop}`,
          files: new Set([rel]),
          why: `${clipId} runs ${length}s, so this cuts it off mid-pose`,
        });
      }
    }
  }
}

/**
 * The player entity override must only ever *add*.
 *
 * RP/entity/player.entity.json is Mojang's file from the 26.4 samples with
 * this pack's controllers appended. Every vanilla clip it drops is a piece of
 * the player that stops animating, and there is nothing in a content log to
 * say so. tools/vanilla_refs/player.entity.json is the cached original, so the
 * two can simply be compared: additions are fine, removals and edits are not.
 */
const OVERRIDE = join(ROOT, "RP", "entity", "player.entity.json");
const REFERENCE = join(ROOT, "tools", "vanilla_refs", "player.entity.json");
if (existsSync(OVERRIDE) && existsSync(REFERENCE)) {
  const rel = "RP/entity/player.entity.json";
  let ours;
  let theirs;
  try {
    ours = JSON.parse(readFileSync(OVERRIDE, "utf8"))["minecraft:client_entity"].description;
    theirs = JSON.parse(readFileSync(REFERENCE, "utf8"))["minecraft:client_entity"].description;
  } catch (error) {
    problems.push({ id: rel, files: new Set([rel]), why: `could not compare with the cached original: ${error}` });
    ours = theirs = undefined;
  }
  if (ours && theirs) {
    for (const [name, target] of Object.entries(theirs.animations ?? {})) {
      if (!(name in (ours.animations ?? {}))) {
        problems.push({ id: `${rel}: ${name}`, files: new Set([rel]),
          why: "a vanilla animation the override drops - that part of the player stops animating" });
      } else if (ours.animations[name] !== target) {
        problems.push({ id: `${rel}: ${name}`, files: new Set([rel]),
          why: `repointed from ${target} - the override is meant to add, not replace` });
      }
    }
    // Everything outside `animations` and `scripts.animate` should be identical.
    for (const key of Object.keys(theirs)) {
      if (key === "animations" || key === "scripts") continue;
      if (JSON.stringify(theirs[key]) !== JSON.stringify(ours[key])) {
        problems.push({ id: `${rel}: ${key}`, files: new Set([rel]),
          why: "differs from the cached vanilla file; the override should only add animations" });
      }
    }
    const vanillaAnimate = theirs.scripts?.animate ?? [];
    const ourAnimate = ours.scripts?.animate ?? [];
    for (const entry of vanillaAnimate) {
      if (!ourAnimate.includes(entry)) {
        problems.push({ id: `${rel}: scripts.animate ${entry}`, files: new Set([rel]),
          why: "a vanilla entry the override drops" });
      }
    }
    for (const key of Object.keys(theirs.scripts ?? {})) {
      if (key === "animate") continue;
      if (JSON.stringify(theirs.scripts[key]) !== JSON.stringify(ours.scripts?.[key])) {
        problems.push({ id: `${rel}: scripts.${key}`, files: new Set([rel]),
          why: "differs from the cached vanilla file; only scripts.animate should gain entries" });
      }
    }
  }
}

/**
 * Texture atlases: the gap that shipped four invisible items.
 *
 * `minecraft:icon` and a block's `material_instances` do not name a file. They
 * name a *key* in item_texture.json or terrain_texture.json, and that key is
 * what points at the file. Generate the art, register the block, forget the
 * atlas entry, and the item exists, crafts, and renders as nothing - with the
 * reason sitting in a content log as "Missing referenced asset".
 *
 * Three ways that goes wrong, all checked here: a key with no atlas entry, an
 * atlas entry pointing at a file that is not there, and an atlas entry nothing
 * refers to (harmless, but always a sign something was renamed by halves).
 */
function readAtlas(file) {
  const entries = new Map();
  const full = join(ROOT, "RP", "textures", file);
  if (!existsSync(full)) return entries;
  let data;
  try {
    data = JSON.parse(readFileSync(full, "utf8"));
  } catch {
    return entries;
  }
  for (const [key, value] of Object.entries(data.texture_data ?? {})) {
    // Single-variant entries use a bare string; multi-variant use a list.
    const raw = value?.textures ?? value;
    const paths = Array.isArray(raw)
      ? raw.map((entry) => (typeof entry === "string" ? entry : entry?.path))
      : [typeof raw === "string" ? raw : raw?.path];
    entries.set(key, paths.filter(Boolean));
  }
  return entries;
}

const ITEM_ATLAS = readAtlas("item_texture.json");
const TERRAIN_ATLAS = readAtlas("terrain_texture.json");
const usedAtlasKeys = new Set();

for (const [atlas, file] of [[ITEM_ATLAS, "item_texture.json"], [TERRAIN_ATLAS, "terrain_texture.json"]]) {
  for (const [key, paths] of atlas) {
    for (const path of paths) {
      if (existsSync(join(ROOT, "RP", `${path}.png`))) continue;
      if (existsSync(join(ROOT, "RP", path))) continue;
      problems.push({
        id: `RP/textures/${file}: ${key} -> ${path}`,
        files: new Set([`RP/textures/${file}`]),
        why: "the atlas points at a texture file that is not in the pack",
      });
    }
  }
}

for (const [folder, atlas, atlasName] of [
  ["items", ITEM_ATLAS, "item_texture.json"],
  ["blocks", TERRAIN_ATLAS, "terrain_texture.json"],
]) {
  const dir = join(ROOT, "BP", folder);
  if (!existsSync(dir)) continue;
  for (const file of walk(dir)) {
    if (!file.endsWith(".json")) continue;
    const rel = relative(ROOT, file).split("\\").join("/");
    let definition;
    try {
      const data = JSON.parse(readFileSync(file, "utf8"));
      definition = data["minecraft:item"] ?? data["minecraft:block"];
    } catch {
      continue;
    }
    if (!definition?.components) continue;

    const keys = [];
    // A block with states carries most of its art in `permutations`, not in
    // the top-level components - a crop's four growth stages live nowhere
    // else. Scanning only the top level would call three of those four
    // textures orphaned and miss a real missing one entirely.
    const blocks = [definition.components, ...(definition.permutations ?? []).map((p) => p.components)];
    for (const components of blocks) {
      if (!components) continue;
      const icon = components["minecraft:icon"];
      if (typeof icon === "string") keys.push(icon);
      else for (const value of Object.values(icon?.textures ?? {})) keys.push(value);
      for (const instance of Object.values(components["minecraft:material_instances"] ?? {})) {
        if (typeof instance?.texture === "string") keys.push(instance.texture);
      }
    }

    for (const key of keys) {
      usedAtlasKeys.add(key);
      if (atlas.has(key)) continue;
      problems.push({
        id: `${rel}: ${key}`,
        files: new Set([rel]),
        why: `not registered in RP/textures/${atlasName}, so the game renders nothing for it`,
      });
    }
  }
}

for (const [atlas, file] of [[ITEM_ATLAS, "item_texture.json"], [TERRAIN_ATLAS, "terrain_texture.json"]]) {
  for (const key of atlas.keys()) {
    if (usedAtlasKeys.has(key)) continue;
    problems.push({
      id: `RP/textures/${file}: ${key}`,
      files: new Set([`RP/textures/${file}`]),
      why: "registered in the atlas but named by no block or item - a rename finished by halves",
    });
  }
}

/**
 * Recipes that can collide with a vanilla one.
 *
 * Bedrock resolves a duplicate crafting shape by picking one and logging a
 * warning, which is how `polished_end_stone` - four end stone in a square -
 * quietly fought `minecraft:end_bricks` for the same grid. The vanilla recipe
 * set is not available to check against here, but the rule that matters is
 * simple: a recipe made *entirely* of vanilla ingredients is a recipe that can
 * collide with one, and a recipe that uses anything from this pack cannot.
 *
 * Anything genuinely checked against vanilla by hand goes in the allowlist,
 * with the reason, the same way tools/validate.mjs records schema defects.
 */
const VANILLA_INGREDIENT_ALLOWLIST = new Map([
  // ["voidbound:something", "why this shape is known not to collide"],
]);

const RECIPE_DIR = join(ROOT, "BP", "recipes");
if (existsSync(RECIPE_DIR)) {
  for (const file of walk(RECIPE_DIR)) {
    if (!file.endsWith(".json")) continue;
    const rel = relative(ROOT, file).split("\\").join("/");
    let data;
    try {
      data = JSON.parse(readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    for (const [kind, recipe] of Object.entries(data)) {
      if (!kind.startsWith("minecraft:recipe")) continue;
      // Furnace recipes take one input and cannot share a grid with anything.
      if (kind === "minecraft:recipe_furnace") continue;

      const ingredients = new Set();
      for (const value of Object.values(recipe.key ?? {})) {
        if (typeof value?.item === "string") ingredients.add(value.item);
      }
      for (const value of recipe.ingredients ?? []) {
        if (typeof value?.item === "string") ingredients.add(value.item);
      }
      if (ingredients.size === 0) continue;

      const id = recipe.description?.identifier ?? rel;
      if (VANILLA_INGREDIENT_ALLOWLIST.has(id)) continue;
      if ([...ingredients].every((item) => item.startsWith("minecraft:"))) {
        problems.push({
          id: `${rel}: ${id}`,
          files: new Set([rel]),
          why: "every ingredient is vanilla, so this shape can collide with a vanilla recipe - "
            + "use a pack material, or add it to VANILLA_INGREDIENT_ALLOWLIST with the reason",
        });
      }
    }
  }
}

/**
 * MER maps must be bound by a texture set, or they are files nobody opens.
 *
 * This shipped wrong for five versions: 102 metalness/emissive/roughness maps
 * were being generated and only 17 had a `.texture_set.json` beside them. The
 * pack rendered, nothing errored, and 85 textures were simply flat - no
 * metalness, no roughness, and no glow, which is the one a player notices.
 * Nothing in the game or the schemas says a word about it.
 */
for (const folder of ["blocks", "items", "entity", "environment", "particle"]) {
  const dir = join(ROOT, "RP", "textures", folder);
  if (!existsSync(dir)) continue;
  const rel = `RP/textures/${folder}`;

  const names = readdirSync(dir);
  const mers = names.filter((n) => n.endsWith("_mer.png"));
  const sets = new Set(names.filter((n) => n.endsWith(".texture_set.json")));

  for (const mer of mers) {
    const base = mer.slice(0, -"_mer.png".length);
    if (sets.has(`${base}.texture_set.json`)) continue;
    problems.push({
      id: `${rel}/${mer}`,
      files: new Set([rel]),
      why: "no .texture_set.json binds this MER map, so the game never loads it - "
        + "the texture renders flat with no glow",
    });
  }

  for (const setName of sets) {
    let data;
    try {
      data = JSON.parse(readFileSync(join(dir, setName), "utf8"))["minecraft:texture_set"];
    } catch (error) {
      problems.push({ id: `${rel}/${setName}`, files: new Set([rel]),
        why: `not valid JSON: ${error}` });
      continue;
    }
    for (const [field, value] of Object.entries(data ?? {})) {
      if (typeof value !== "string") continue;
      if (names.includes(`${value}.png`)) continue;
      problems.push({
        id: `${rel}/${setName}: ${field} -> ${value}`,
        files: new Set([rel]),
        why: "the texture set points at a file that is not in this folder",
      });
    }
  }
}

console.log(
  `checked ${references.size} distinct identifier(s) ` +
    `against ${VANILLA.size} vanilla ids and ${DEFINED.size} pack definitions, ` +
    `plus block-reference, client-entity, animation, script-animation, override-drift, texture-atlas, recipe-collision, texture-set and integer-field rules`
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
