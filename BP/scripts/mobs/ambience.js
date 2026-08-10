import { world, system } from "@minecraft/server";

// Idle atmosphere: periodic, low-chance particle puffs on mobs that otherwise
// only show any visual feedback when they're mid-ability. This is what was
// missing from the "everything is kind of bland, no effects" complaint -
// combat abilities already had particles (see abilities.js/bossAI.js), idle
// standing-around didn't.
const AMBIENT_TICKS = 24; // ~1.2s between passes

const WISP_TYPES = [
  "hollowveil:wraith",
  "hollowveil:banshee",
  "hollowveil:poltergeist",
  "hollowveil:shade",
  "hollowveil:weeping_widow",
  "hollowveil:hollow_king",
  "hollowveil:soul_wisp",
];
const EMBER_TYPES = ["hollowveil:hellhound", "hollowveil:imp", "hollowveil:malacoda", "hollowveil:ashen_whelp"];
const WARD_TYPES = ["hollowveil:bastion_sentinel", "hollowveil:city_wraithguard", "hollowveil:fallen_knight"];
const CRAWL_TYPES = ["hollowveil:marrow_crawler"];
// bioluminescent fauna get a faint glow-mote instead of nothing at all
const GLOW_TYPES = ["hollowveil:glimmershroom_toad"];

export function startAmbience() {
  system.runInterval(() => {
    const dim = hollowVeil();
    if (!dim) return;
    ambientPass(dim, WISP_TYPES, "hollowveil:soul_wisp_particle", 0.35, 0.6);
    ambientPass(dim, EMBER_TYPES, "hollowveil:ember_particle", 0.3, 0.3);
    ambientPass(dim, WARD_TYPES, "hollowveil:hollow_king_pulse_particle", 0.15, 0.9);
    ambientPass(dim, CRAWL_TYPES, "hollowveil:shade_teleport_particle", 0.2, 0.15);
    ambientPass(dim, GLOW_TYPES, "hollowveil:soul_wisp_particle", 0.12, 0.3);
    dragonTrail(dim);
  }, AMBIENT_TICKS);
}

function hollowVeil() {
  try {
    return world.getDimension("hollowveil:hollow_veil");
  } catch {
    return null;
  }
}

function ambientPass(dim, types, particle, chance, offsetY) {
  for (const typeId of types) {
    let entities;
    try {
      entities = dim.getEntities({ type: typeId });
    } catch {
      continue;
    }
    for (const entity of entities) {
      if (Math.random() > chance) continue;
      try {
        dim.spawnParticle(particle, { x: entity.location.x, y: entity.location.y + offsetY, z: entity.location.z });
      } catch {
        /* unloaded chunk or entity mid-despawn; just skip this pass */
      }
    }
  }
}

// Tamed dragons get a trailing sparkle while airborne so flight actually
// reads as flight, not just a big mob standing in the sky.
function dragonTrail(dim) {
  let dragons;
  try {
    dragons = dim.getEntities({ type: "hollowveil:veil_dragon" });
  } catch {
    return;
  }
  for (const dragon of dragons) {
    let airborne = true;
    try {
      airborne = dragon.isOnGround === false;
    } catch {
      /* if the property is unavailable just assume airborne so the trail still shows */
    }
    if (!airborne) continue;
    if (Math.random() > 0.6) continue;
    try {
      dim.spawnParticle("hollowveil:portal_particle", dragon.location);
    } catch {
      /* unloaded chunk; skip this pass */
    }
  }
}
