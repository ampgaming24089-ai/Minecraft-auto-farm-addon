/**
 * Where structures are.
 *
 * The End is divided into a fixed grid of cells. Whether a cell holds a
 * structure, which kind, where inside the cell it sits and which way it faces
 * are all derived from the world seed and the cell's coordinates. No siting
 * data is ever written to disk: the same seed always produces the same map,
 * which is what makes the rift compass able to point at a structure that has
 * not been generated yet.
 */

import { world } from "@minecraft/server";
import { Rng, hash, hashString } from "../lib/rng.js";
import { cardinal } from "../lib/vec.js";
import { pickStructure } from "../structures/index.js";

/** Grid pitch in blocks. One structure per cell at most. */
export const CELL_SIZE = 272;

/** Cells closer than this to the origin stay empty - that is vanilla's island. */
const INNER_CLEARANCE = 1100;

/** Fraction of eligible cells that hold a structure. */
const SITE_CHANCE = 0.58;

let seedHash;

/** The world seed is not readable during early execution, so resolve it late. */
export function worldSeedHash() {
  if (seedHash === undefined) {
    let raw = "voidbound";
    try {
      raw = world.seed ?? raw;
    } catch {
      // Fall back to the constant; siting stays self-consistent either way.
    }
    seedHash = hashString(String(raw));
  }
  return seedHash;
}

/** @typedef {{key:string, cellX:number, cellZ:number, x:number, z:number, facing:string, blueprint:object, seed:number}} Site */

/**
 * The site in a given cell, or undefined if that cell is empty.
 * Pure function of (seed, cellX, cellZ).
 *
 * @returns {Site | undefined}
 */
export function siteInCell(cellX, cellZ) {
  const seed = hash(worldSeedHash(), cellX, cellZ);
  const rng = new Rng(seed);

  if (!rng.chance(SITE_CHANCE)) return undefined;

  // Inset from the cell edges so neighbouring structures cannot touch.
  const margin = 48;
  const x = cellX * CELL_SIZE + rng.int(margin, CELL_SIZE - margin);
  const z = cellZ * CELL_SIZE + rng.int(margin, CELL_SIZE - margin);

  if (Math.sqrt(x * x + z * z) < INNER_CLEARANCE) return undefined;

  return {
    key: `${cellX}.${cellZ}`,
    cellX,
    cellZ,
    x,
    z,
    facing: cardinal(rng.int(0, 3)),
    blueprint: pickStructure(rng),
    seed,
  };
}

/**
 * Every site whose cell is within `cellRadius` cells of a world position,
 * nearest first.
 *
 * @returns {Site[]}
 */
export function sitesNear(x, z, cellRadius = 2) {
  const centerX = Math.floor(x / CELL_SIZE);
  const centerZ = Math.floor(z / CELL_SIZE);
  const found = [];
  for (let dz = -cellRadius; dz <= cellRadius; dz++) {
    for (let dx = -cellRadius; dx <= cellRadius; dx++) {
      const site = siteInCell(centerX + dx, centerZ + dz);
      if (site) found.push(site);
    }
  }
  found.sort(
    (a, b) => (a.x - x) ** 2 + (a.z - z) ** 2 - ((b.x - x) ** 2 + (b.z - z) ** 2)
  );
  return found;
}

/** Horizontal distance from a position to a site. */
export function distanceTo(site, position) {
  return Math.sqrt((site.x - position.x) ** 2 + (site.z - position.z) ** 2);
}
