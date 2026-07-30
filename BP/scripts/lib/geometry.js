/**
 * Geometry helpers: cardinal facing + rotating relative offsets into world space.
 * Every farm is authored once in "local space" (+x = right, +z = forward, +y = up,
 * facing = north/+z) and rotated onto the world based on the player's facing when
 * they confirm a build.
 */

/** @typedef {{x:number,y:number,z:number}} Vec3 */

/** Four cardinal directions as unit vectors on the XZ plane. */
export const FACINGS = {
  north: { x: 0, z: -1 },
  south: { x: 0, z: 1 },
  east: { x: 1, z: 0 },
  west: { x: -1, z: 0 },
};

/**
 * Snap a player's view direction to the nearest of the 4 cardinal directions.
 * @param {import("@minecraft/server").Vector3} viewDirection
 * @returns {keyof typeof FACINGS}
 */
export function get4DirFacing(viewDirection) {
  if (Math.abs(viewDirection.x) > Math.abs(viewDirection.z)) {
    return viewDirection.x > 0 ? "east" : "west";
  }
  return viewDirection.z > 0 ? "south" : "north";
}

/**
 * Rotate a local-space offset (authored assuming "north" facing, i.e. +z is
 * the direction the structure extends away from the player) into world space
 * for the given facing.
 * @param {Vec3} local
 * @param {keyof typeof FACINGS} facing
 * @returns {Vec3}
 */
export function rotateLocal(local, facing) {
  switch (facing) {
    case "north":
      return { x: local.x, y: local.y, z: -local.z };
    case "south":
      return { x: -local.x, y: local.y, z: local.z };
    case "east":
      return { x: local.z, y: local.y, z: local.x };
    case "west":
      return { x: -local.z, y: local.y, z: -local.x };
    default:
      return local;
  }
}

/**
 * Convert a local offset + facing into an absolute world block location
 * relative to an origin.
 * @param {Vec3} origin
 * @param {Vec3} local
 * @param {keyof typeof FACINGS} facing
 * @returns {Vec3}
 */
export function toWorld(origin, local, facing) {
  const r = rotateLocal(local, facing);
  return { x: origin.x + r.x, y: origin.y + r.y, z: origin.z + r.z };
}

/**
 * Rotate a horizontal cardinal direction string together with the structure.
 * Used for block states like "direction"/"facing_direction" on doors, beds, etc.
 * @param {keyof typeof FACINGS} localDir direction authored in local space
 * @param {keyof typeof FACINGS} facing
 */
export function rotateDirection(localDir, facing) {
  const order = ["north", "east", "south", "west"];
  const rotationSteps = { north: 0, east: 1, south: 2, west: 3 };
  const idx = (rotationSteps[localDir] + rotationSteps[facing]) % 4;
  return order[idx];
}

/**
 * Compute the axis-aligned min/max corners (inclusive) of a structure given
 * its local-space size and level count, in world space. Most farms stack
 * levels vertically (stackAxis "y", the default), but a farm can instead
 * repeat its unit sideways in local space by setting stackAxis "x" (used by
 * the crop farm, which places separate ground-level units side by side
 * instead of stacking them).
 * @param {Vec3} origin
 * @param {{x:number,y:number,z:number}} size local footprint size (per level/unit)
 * @param {number} levels
 * @param {number} levelSpacing distance between level/unit origins along stackAxis
 * @param {keyof typeof FACINGS} facing
 * @param {"x"|"y"|"z"} [stackAxis]
 */
export function computeBounds(origin, size, levels, levelSpacing, facing, stackAxis = "y") {
  const extra = levelSpacing * (levels - 1);
  const effSize = {
    x: size.x + (stackAxis === "x" ? extra : 0),
    y: size.y + (stackAxis === "y" ? extra : 0),
    z: size.z + (stackAxis === "z" ? extra : 0),
  };
  const corners = [
    { x: 0, y: 0, z: 0 },
    { x: effSize.x - 1, y: 0, z: 0 },
    { x: 0, y: 0, z: effSize.z - 1 },
    { x: effSize.x - 1, y: 0, z: effSize.z - 1 },
  ].map((c) => toWorld(origin, c, facing));

  const minX = Math.min(...corners.map((c) => c.x));
  const maxX = Math.max(...corners.map((c) => c.x));
  const minZ = Math.min(...corners.map((c) => c.z));
  const maxZ = Math.max(...corners.map((c) => c.z));

  return {
    min: { x: minX, y: origin.y, z: minZ },
    max: { x: maxX, y: origin.y + effSize.y - 1, z: maxZ },
  };
}
