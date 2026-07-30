/**
 * Dev-only command emitter (repo tooling, never shipped in the addon).
 *
 * Farms are authored as a fixed-orientation layout: the structure always
 * extends the same way (+x/+z) from wherever the player is standing when
 * they use the beacon item. All positions are tilde-relative to the
 * executor, so no rotation math or Script API is needed at all — every
 * farm compiles down to a flat list of vanilla /fill, /setblock and
 * /summon commands in a .mcfunction file.
 *
 * Ordering matters: later fill()/set() calls at the same coordinate are
 * meant to overwrite earlier ones (e.g. punching a hole in a wall, or
 * embedding a hopper in a floor) — command execution order gives us that
 * "last write wins" behavior for free, same as the old merge() helper did.
 */

function fmtCoord(n) {
  return `~${n}`;
}

function fmtPos([x, y, z]) {
  return `${fmtCoord(x)} ${fmtCoord(y)} ${fmtCoord(z)}`;
}

function fmtStateValue(v) {
  if (typeof v === "boolean") return String(v);
  if (typeof v === "number") return String(v);
  return `"${v}"`;
}

function blockSpec(id, states) {
  if (!states || Object.keys(states).length === 0) return id;
  const stateStr = Object.entries(states)
    .map(([k, v]) => `"${k}"=${fmtStateValue(v)}`)
    .join(",");
  return `${id}[${stateStr}]`;
}

/**
 * One /fill command for a local-space box (inclusive corners, [x,y,z] arrays).
 * `mode` can be "hollow" (shell only, interior becomes air — one command
 * instead of a shell fill + separate interior clear), "replace" (default),
 * "keep", "destroy", or "outline".
 */
export function fill(from, to, id, states, mode) {
  const base = `fill ${fmtPos(from)} ${fmtPos(to)} ${blockSpec(id, states)}`;
  return mode ? `${base} ${mode}` : base;
}

/** One /setblock command for a single local-space position. */
export function set(x, y, z, id, states) {
  return `setblock ${fmtPos([x, y, z])} ${blockSpec(id, states)}`;
}

/** One /summon command for a single local-space position. */
export function summon(x, y, z, typeId) {
  return `summon ${typeId} ${fmtPos([x, y, z])}`;
}
