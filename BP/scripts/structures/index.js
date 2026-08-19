/** The structure catalogue, with the relative odds of each kind appearing. */

import { LuminousGrove } from "./luminousGrove.js";
import { RiftAnchor } from "./riftAnchor.js";
import { ShatteredSanctum } from "./shatteredSanctum.js";
import { VoidSpire } from "./voidSpire.js";

export const STRUCTURES = [
  { blueprint: VoidSpire, weight: 32 },
  { blueprint: ShatteredSanctum, weight: 26 },
  { blueprint: LuminousGrove, weight: 24 },
  { blueprint: RiftAnchor, weight: 18 },
];

export const BY_ID = new Map(STRUCTURES.map((entry) => [entry.blueprint.id, entry.blueprint]));

/** Pick a structure kind from a seeded generator. */
export function pickStructure(rng) {
  const total = STRUCTURES.reduce((sum, entry) => sum + entry.weight, 0);
  let roll = rng.float(0, total);
  for (const entry of STRUCTURES) {
    roll -= entry.weight;
    if (roll <= 0) return entry.blueprint;
  }
  return STRUCTURES[0].blueprint;
}
