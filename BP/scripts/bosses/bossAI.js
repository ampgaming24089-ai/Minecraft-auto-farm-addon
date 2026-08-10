import { world, system } from "@minecraft/server";
import { knockback, getNearbyPlayers } from "../lib/combat.js";
import { markBossDefeated, getWorldJson, KEYS } from "../lib/state.js";

const ABILITY_INTERVAL_TICKS = { hollow_king: 100, weeping_widow: 90, malacoda: 80 };
const SHORT_ID = {
  "hollowveil:hollow_king": "hollow_king",
  "hollowveil:weeping_widow": "weeping_widow",
  "hollowveil:malacoda": "malacoda",
};

export function startBossAI() {
  system.runInterval(() => tickAllBosses(), 10);
  world.afterEvents.entityDie.subscribe((ev) => {
    const shortId = SHORT_ID[ev.deadEntity.typeId];
    if (!shortId) return;
    markBossDefeated(shortId);
    celebrateAtShrine(ev.deadEntity.dimension);
  });
}

function tickAllBosses() {
  let dim;
  try {
    dim = world.getDimension("hollowveil:hollow_veil");
  } catch {
    return;
  }
  const bosses = dim.getEntities({ families: ["hollow_veil_boss"] });
  for (const boss of bosses) tickBoss(boss);
}

function tickBoss(boss) {
  const shortId = SHORT_ID[boss.typeId];
  if (!shortId) return;
  const health = boss.getComponent("minecraft:health");
  if (!health) return;
  const ratio = health.currentValue / health.effectiveMax;
  const phase = boss.getDynamicProperty("hollowveil:phase") ?? 1;

  if (ratio <= 0.66 && phase < 2) {
    boss.setDynamicProperty("hollowveil:phase", 2);
    safeTrigger(boss, "hollowveil:to_phase2");
    announce(boss, `§d${displayName(boss)} shudders with renewed fury!`);
    phaseShockwave(boss, 1.0);
    summonAdds(boss, shortId, 2);
  }
  if (ratio <= 0.3 && phase < 3) {
    boss.setDynamicProperty("hollowveil:phase", 3);
    safeTrigger(boss, "hollowveil:to_phase3");
    announce(boss, `§4${displayName(boss)} enters a desperate rage!`);
    phaseShockwave(boss, 1.6);
    summonAdds(boss, shortId, 3);
    enrage(boss);
  }

  const now = system.currentTick;
  const nextAbility = boss.getDynamicProperty("hollowveil:next_ability") ?? 0;
  if (now >= nextAbility) {
    doAbility(boss, shortId);
    // each phase tightens the cadence, so the fight visibly escalates
    const base = ABILITY_INTERVAL_TICKS[shortId] ?? 100;
    const cur = boss.getDynamicProperty("hollowveil:phase") ?? 1;
    const scaled = Math.max(28, Math.round(base * (cur === 3 ? 0.45 : cur === 2 ? 0.7 : 1)));
    boss.setDynamicProperty("hollowveil:next_ability", now + scaled);
  }
}

/** A ring of force + light on every phase change: knocks the arena back,
 * telegraphs that the fight just changed gear, and gives the player a
 * reason to reposition instead of standing still trading hits. */
function phaseShockwave(boss, power) {
  const dim = boss.dimension;
  for (const p of getNearbyPlayers(dim, boss.location, 14)) {
    knockback(p, p.location.x - boss.location.x, p.location.z - boss.location.z, 1.4 * power, 0.55 * power);
    try {
      p.addEffect("slowness", 60, { amplifier: 1, showParticles: true });
    } catch {
      /* effect ids vary by version - the knockback still lands */
    }
  }
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    const r = 5 * power;
    try {
      dim.spawnParticle("hollowveil:hollow_king_pulse_particle", {
        x: boss.location.x + Math.cos(a) * r,
        y: boss.location.y + 1,
        z: boss.location.z + Math.sin(a) * r,
      });
    } catch {
      /* cosmetic */
    }
  }
  try {
    dim.playSound("hollowveil.hollow_king.pulse", boss.location);
  } catch {
    /* cosmetic */
  }
}

/** Final phase: the boss itself gets faster and hits harder. */
function enrage(boss) {
  try {
    boss.addEffect("speed", 20 * 600, { amplifier: 1, showParticles: false });
    boss.addEffect("strength", 20 * 600, { amplifier: 1, showParticles: false });
    boss.addEffect("resistance", 20 * 600, { amplifier: 0, showParticles: false });
  } catch {
    /* if any effect id is unavailable the phase still escalates via cadence */
  }
}

function safeTrigger(entity, event) {
  try {
    entity.triggerEvent(event);
  } catch {
    /* event always defined on boss entities; ignore if the runtime disagrees */
  }
}

function displayName(boss) {
  try {
    return boss.nameTag || boss.typeId;
  } catch {
    return boss.typeId;
  }
}

function announce(boss, message) {
  for (const p of getNearbyPlayers(boss.dimension, boss.location, 40)) {
    try {
      p.onScreenDisplay.setActionBar(message);
    } catch {
      /* non-critical UI feedback */
    }
  }
}

function doAbility(boss, shortId) {
  const dim = boss.dimension;
  switch (shortId) {
    case "hollow_king": {
      for (const p of getNearbyPlayers(dim, boss.location, 8)) {
        try {
          p.addEffect("darkness", 60, { amplifier: 0, showParticles: false });
        } catch {
          /* darkness effect id may vary by version; skip gracefully */
        }
        knockback(p, p.location.x - boss.location.x, p.location.z - boss.location.z, 0.7, 0.3);
      }
      spawnFx(dim, boss.location, "hollowveil:hollow_king_pulse_particle", "hollowveil.hollow_king.pulse");
      break;
    }
    case "weeping_widow": {
      for (const p of getNearbyPlayers(dim, boss.location, 10)) {
        try {
          p.addEffect("nausea", 80, { amplifier: 1, showParticles: false });
        } catch {
          /* ignore */
        }
        knockback(p, p.location.x - boss.location.x, p.location.z - boss.location.z, 0.9, 0.35);
      }
      spawnFx(dim, boss.location, "hollowveil:banshee_scream_particle", "hollowveil.widow.wail");
      break;
    }
    case "malacoda": {
      for (const p of getNearbyPlayers(dim, boss.location, 6)) {
        knockback(p, p.location.x - boss.location.x, p.location.z - boss.location.z, 1.3, 0.5);
        try {
          p.setOnFire(3, true);
        } catch {
          /* ignore */
        }
      }
      spawnFx(dim, boss.location, "hollowveil:ember_particle", "hollowveil.malacoda.buffet");
      break;
    }
    default:
      break;
  }
}

function spawnFx(dim, loc, particle, sound) {
  try {
    dim.spawnParticle(particle, loc);
  } catch {
    /* cosmetic only */
  }
  try {
    dim.playSound(sound, loc);
  } catch {
    /* cosmetic only */
  }
}

const ADD_TABLE = {
  hollow_king: { entity: "hollowveil:shade", count: 2 },
  weeping_widow: { entity: "hollowveil:banshee", count: 2 },
  malacoda: { entity: "hollowveil:imp", count: 2, extra: "hollowveil:hellhound" },
};

function summonAdds(boss, shortId, phase) {
  const cfg = ADD_TABLE[shortId];
  if (!cfg) return;
  const dim = boss.dimension;
  // later phases summon a bigger ring, not just the same wave again
  const count = cfg.count + (phase >= 3 ? 3 : phase >= 2 ? 1 : 0);
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count;
    const pos = {
      x: boss.location.x + Math.cos(angle) * 3,
      y: boss.location.y,
      z: boss.location.z + Math.sin(angle) * 3,
    };
    try {
      dim.spawnEntity(cfg.entity, pos);
    } catch {
      /* if the spot is obstructed just skip this add */
    }
  }
  if (phase >= 3 && cfg.extra) {
    try {
      dim.spawnEntity(cfg.extra, { x: boss.location.x, y: boss.location.y, z: boss.location.z + 3 });
    } catch {
      /* ignore */
    }
  }
}

function celebrateAtShrine(dim) {
  const shrine = getWorldJson(KEYS.VILLAGE_SHRINE_POS, null);
  if (!shrine) return;
  try {
    dim.spawnParticle("hollowveil:soul_wisp_particle", shrine);
    dim.playSound("hollowveil.village.restore", shrine);
  } catch {
    /* cosmetic only */
  }
}
