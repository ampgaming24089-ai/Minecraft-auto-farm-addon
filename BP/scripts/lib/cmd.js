/**
 * One place that runs a slash command, because the whole pack was calling a
 * method that does not exist.
 *
 * `Dimension.runCommandAsync` is a @minecraft/server **1.x** API. It was
 * removed in 2.x - the 2.9.0 bindings list exactly one command entry point on
 * Dimension, `runCommand`, and nothing named `runCommandAsync`. Every call
 * site in this pack used the 1.x name, so every one of them threw
 * `TypeError: <name> is not a function`:
 *
 *   portal/portal.js   lighting a portal, and building the return frame
 *   world/build.js     raising the hub, placing the three Warden altars
 *   world/terrain.js   every streamed terrain sector
 *   world/sites.js     every landmark
 *   village/village.js Hollow Hamlet
 *   bosses/chambers.js every boss arena
 *
 * That is the whole reason the portal "did nothing": frame detection had been
 * working all along and the very last step - filling the doorway - threw. The
 * same throw took the hub, the terrain, the village and the boss chambers with
 * it, so nobody could have reached the dimension by any route.
 *
 * tools/validate.py now resolves every method called on a dimension/entity/
 * player against the bindings for the declared @minecraft/server version, so a
 * dead API cannot come back in silently.
 */

let lastError = null;
let errorCount = 0;

/**
 * Runs one command. Returns true if it succeeded.
 *
 * Commands fail for ordinary, expected reasons out here - an unloaded chunk, a
 * fill that reaches past the build height - and a world builder that stops at
 * the first of those would leave half a sector standing. So a failure is
 * recorded and skipped rather than thrown, exactly like the fire-and-forget
 * promise this replaced. `lastCommandError()` surfaces the most recent one to
 * `/scriptevent hollowveil:check`.
 */
export function runCommand(dimension, cmd) {
  try {
    dimension.runCommand(cmd);
    return true;
  } catch (err) {
    errorCount += 1;
    lastError = `${err}`.slice(0, 200);
    return false;
  }
}

/** A bound `run(cmd)` for builders that issue many commands on one dimension. */
export function commandRunner(dimension) {
  return (cmd) => runCommand(dimension, cmd);
}

export function lastCommandError() {
  return errorCount ? `${errorCount} command failure(s), last: ${lastError}` : null;
}
