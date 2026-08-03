import { planLevel, planShaft, SIZE, LEVEL_SPACING } from "./ironFarm.js";

/**
 * Iron Golem Farm (Single Tier)
 * =============================
 * Exactly what was asked for as its own menu entry: one tier, 20 beds, 20
 * workstations (composters), auto water-push to a kill chamber, and a
 * hopper collection system — no stacking, no menu slider. This reuses the
 * exact same single-level layout as the "Stackable Iron Farm" module
 * (ironFarm.js) — see that file's header for the full research/mechanics
 * writeup (20 beds/10+ villagers/75% workstation use for golem spawning,
 * the population cap, the water convergence fix, magma over lava, etc.) —
 * it's just fixed to build 1 level instead of offering 1-4.
 *
 * If you also want the option to stack multiple tiers into one bigger
 * merged village later, "Stackable Iron Farm" in the menu is the same
 * design with that slider exposed.
 */
export const IronGolemFarm = {
  id: "iron_golem_farm",
  name: "Iron Golem Farm (Single Tier)",
  shortDescription: "One tier: 20 beds, 20 workstations, water push, magma kill chamber, hopper collection.",
  size: SIZE,
  levelSpacing: LEVEL_SPACING,
  maxLevels: 1,
  fixedLevels: 1,

  /**
   * @param {{levels:number, facing: keyof import("../lib/geometry.js").FACINGS}} opts
   */
  plan({ facing }) {
    const { placements, spawns } = planLevel(0, facing);
    placements.push(...planShaft(1, facing));
    return { placements, spawns };
  },
};
