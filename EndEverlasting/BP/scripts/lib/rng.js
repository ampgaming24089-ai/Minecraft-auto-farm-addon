/**
 * Deterministic pseudo-randomness.
 *
 * Every decision about the End - where a structure sits, which variant it is,
 * how its rubble scatters - is derived from the world seed plus the site's
 * coordinates. Nothing is stored to disk and nothing depends on visit order,
 * so two players exploring the same seed independently find the same world,
 * and a structure rebuilt after a cache prune comes out identical.
 */

/** Mix an unsigned 32-bit value. Cheap, well-distributed avalanche. */
function mix(value) {
  let x = value >>> 0;
  x = Math.imul(x ^ (x >>> 16), 0x7feb352d) >>> 0;
  x = Math.imul(x ^ (x >>> 15), 0x846ca68b) >>> 0;
  return (x ^ (x >>> 16)) >>> 0;
}

/** Combine any number of integers into one 32-bit hash. */
export function hash(...values) {
  let acc = 0x9e3779b9;
  for (const value of values) {
    acc = mix((acc ^ Math.imul(value | 0, 0x85ebca6b)) >>> 0);
  }
  return acc >>> 0;
}

/** World seeds arrive as strings and can exceed 32 bits, so fold them down. */
export function hashString(text) {
  let acc = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    acc = Math.imul(acc ^ text.charCodeAt(i), 0x01000193) >>> 0;
  }
  return mix(acc);
}

export class Rng {
  constructor(seed) {
    this.state = (seed >>> 0) || 0x9e3779b9;
  }

  /** xorshift32: small, fast, and identical on every device. */
  next() {
    let x = this.state;
    x ^= (x << 13) >>> 0;
    x ^= x >>> 17;
    x ^= (x << 5) >>> 0;
    this.state = x >>> 0;
    return this.state / 0x100000000;
  }

  float(min, max) {
    return min + (max - min) * this.next();
  }

  /** Inclusive on both ends. */
  int(min, max) {
    return min + Math.floor(this.next() * (max - min + 1));
  }

  chance(probability) {
    return this.next() < probability;
  }

  pick(items) {
    return items[Math.floor(this.next() * items.length)];
  }

  /** Fisher-Yates, in place, so callers can shuffle decoration order. */
  shuffle(items) {
    for (let i = items.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      const swap = items[i];
      items[i] = items[j];
      items[j] = swap;
    }
    return items;
  }
}
