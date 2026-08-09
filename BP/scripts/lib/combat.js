/** Small combat helpers shared by mob abilities and boss AI. Knockback in
 * particular has changed shape across script API versions, so this tries
 * the current object-based signature first and falls back to the older
 * one rather than hard-failing an ability tick. */
export function knockback(entity, dx, dz, horizontal, vertical) {
  try {
    entity.applyKnockback({ x: dx, z: dz }, vertical);
    return;
  } catch {
    /* fall through */
  }
  try {
    entity.applyKnockback(dx, dz, horizontal, vertical);
  } catch {
    /* best effort only; never let a knockback failure break an ability tick */
  }
}

export function pushAwayFrom(entity, source, horizontal, vertical) {
  const dx = entity.location.x - source.location.x;
  const dz = entity.location.z - source.location.z;
  const len = Math.hypot(dx, dz) || 1;
  knockback(entity, (dx / len) * horizontal, (dz / len) * horizontal, horizontal, vertical);
}

export function getNearbyPlayers(dimension, center, radius) {
  return dimension.getPlayers({ location: center, maxDistance: radius });
}

export function getNearbyEntities(dimension, center, radius, families) {
  return dimension.getEntities({ location: center, maxDistance: radius, families });
}
