/**
 * The small amount of state that genuinely has to persist.
 *
 * Siting is derived from the seed and never stored. The only thing worth
 * remembering is which sites have already been built, so a player flying back
 * over a structure does not have it re-stamped over whatever they have since
 * done to it.
 *
 * Entries are kept in one string dynamic property with a FIFO cap. If a very
 * old entry is evicted and the player returns, the structure regenerates
 * identically - the cost of a bounded save file.
 */

import { world } from "@minecraft/server";

const PROPERTY = "voidbound.built_sites";
const MAX_ENTRIES = 1500;

let cache;

function load() {
  if (cache) return cache;
  let raw = "";
  try {
    const stored = world.getDynamicProperty(PROPERTY);
    if (typeof stored === "string") raw = stored;
  } catch {
    raw = "";
  }
  cache = raw ? raw.split(",") : [];
  return cache;
}

export function isBuilt(key) {
  return load().includes(key);
}

export function markBuilt(key) {
  const entries = load();
  if (entries.includes(key)) return;
  entries.push(key);
  while (entries.length > MAX_ENTRIES) entries.shift();
  try {
    world.setDynamicProperty(PROPERTY, entries.join(","));
  } catch (error) {
    console.warn(`[Riftborne] could not persist built sites: ${error}`);
  }
}

/** Used by the /voidbound regenerate flow and by tests. */
export function forgetAll() {
  cache = [];
  try {
    world.setDynamicProperty(PROPERTY, "");
  } catch {
    // Nothing to do; the in-memory cache is already cleared.
  }
}
