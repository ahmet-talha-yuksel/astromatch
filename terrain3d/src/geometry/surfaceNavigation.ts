import type { ValidatedTerrainData } from "../types/terrain";

/** Sample the exact same triangles as the rendered mesh, including NoData holes. */
export function surfaceElevation(terrain: ValidatedTerrainData, u: number, v: number): number | null {
  if (!Number.isFinite(u) || !Number.isFinite(v) || u < 0 || v < 0 || u > 1 || v > 1) return null;
  const x = u * (terrain.width - 1), z = v * (terrain.height - 1);
  const col = Math.min(Math.floor(x), terrain.width - 2), row = Math.min(Math.floor(z), terrain.height - 2);
  const fx = x - col, fz = z - row, i = row * terrain.width + col;
  const a = terrain.heights[i], b = terrain.heights[i + 1], c = terrain.heights[i + terrain.width], d = terrain.heights[i + terrain.width + 1];
  if (fx + fz <= 1) return a === null || b === null || c === null ? null : a * (1 - fx - fz) + b * fx + c * fz;
  return b === null || c === null || d === null ? null : b * (1 - fz) + c * (1 - fx) + d * (fx + fz - 1);
}

export function findSurfaceSpawn(terrain: ValidatedTerrainData): { u: number; v: number } {
  // Triangle centroids guarantee a valid landing, even for sparse masked data.
  let best = { u: 0, v: 0 }, score = Infinity;
  for (let row = 0; row < terrain.height - 1; row++) for (let col = 0; col < terrain.width - 1; col++) {
    for (const offset of [1 / 3, 2 / 3]) {
      const u = (col + offset) / (terrain.width - 1), v = (row + offset) / (terrain.height - 1);
      const next = (u - 0.5) ** 2 + (v - 0.68) ** 2;
      if (next < score && surfaceElevation(terrain, u, v) !== null) { best = { u, v }; score = next; }
    }
  }
  return best;
}

export type ParcelPosition = { u: number; v: number };
/** Reject every NoData triangle crossed by a segment, including narrow corner slivers. */
export function parcelSegmentIsValid(terrain: ValidatedTerrainData, from: ParcelPosition, to: ParcelPosition): boolean {
  if (surfaceElevation(terrain, from.u, from.v) === null || surfaceElevation(terrain, to.u, to.v) === null) return false;
  const x0 = from.u * (terrain.width - 1), z0 = from.v * (terrain.height - 1);
  const x1 = to.u * (terrain.width - 1), z1 = to.v * (terrain.height - 1);
  const times = [0, 1];
  // Raster triangles meet at integer column, row, or column+row coordinates.
  for (const [start, end] of [[x0, x1], [z0, z1], [x0 + z0, x1 + z1]]) {
    if (start === end) continue;
    for (let line = Math.floor(Math.min(start, end)) + 1; line < Math.max(start, end); line++) {
      const t = (line - start) / (end - start);
      if (t > 0 && t < 1) times.push(t);
    }
  }
  times.sort((a, b) => a - b);
  for (let i = 1; i < times.length; i++) {
    if (times[i] - times[i - 1] < 1e-12) continue;
    const t = (times[i] + times[i - 1]) / 2;
    if (surfaceElevation(terrain, from.u + (to.u - from.u) * t, from.v + (to.v - from.v) * t) === null) return false;
  }
  return true;
}

/** Clip horizontal movement to the selected parcel and never enter generated scenery. */
export function moveWithinParcel(terrain: ValidatedTerrainData, from: ParcelPosition, du: number, dv: number, inset: ParcelPosition = { u: 0, v: 0 }): ParcelPosition | null {
  const to = {
    u: Math.max(inset.u, Math.min(1 - inset.u, from.u + du)),
    v: Math.max(inset.v, Math.min(1 - inset.v, from.v + dv)),
  };
  return parcelSegmentIsValid(terrain, from, to) ? to : null;
}
