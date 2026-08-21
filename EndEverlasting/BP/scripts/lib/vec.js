/** Vector helpers. Bedrock's Vector3 is a plain {x, y, z}, so these stay tiny. */

export function add(a, b) {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function floor(v) {
  return { x: Math.floor(v.x), y: Math.floor(v.y), z: Math.floor(v.z) };
}

export function distance(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const dz = a.z - b.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

/** Horizontal distance - the End is mostly a flat scatter of islands. */
export function distanceXZ(a, b) {
  const dx = a.x - b.x;
  const dz = a.z - b.z;
  return Math.sqrt(dx * dx + dz * dz);
}

const CARDINALS = ["north", "east", "south", "west"];

/**
 * Rotate a local-space offset onto one of the four cardinal facings, so a
 * single blueprint can be placed in four orientations.
 */
export function rotate(local, facing) {
  switch (facing) {
    case "east":
      return { x: -local.z, y: local.y, z: local.x };
    case "south":
      return { x: -local.x, y: local.y, z: -local.z };
    case "west":
      return { x: local.z, y: local.y, z: -local.x };
    default:
      return { x: local.x, y: local.y, z: local.z };
  }
}

export function cardinal(index) {
  return CARDINALS[((index % 4) + 4) % 4];
}
