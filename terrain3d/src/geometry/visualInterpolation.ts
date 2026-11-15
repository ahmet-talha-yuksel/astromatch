import * as THREE from "three";
import type { TerrainData, ValidatedTerrainData } from "../types/terrain";
import { spacingAxes, validateTerrainData } from "../validation/terrain";
import { createTerrainGeometry } from "./terrainGeometry";

export interface VisualInterpolation {
  /** Private display product: explicitly synthetic when any sample is estimated. */
  terrain: ValidatedTerrainData;
  estimatedMask: boolean[];
  missingCount: number;
}
const cache = new WeakMap<TerrainData, VisualInterpolation>();

/** Bounded, neighbor-based harmonic interpolation. Never mutates the source DEM. */
export function interpolateTerrainForDisplay(input: TerrainData): VisualInterpolation {
  const cached = cache.get(input);
  if (cached) return cached;
  const source = validateTerrainData(input);
  const { width, height, heights } = source;
  const estimatedMask = heights.map(h => h === null);
  const missing: number[] = [];
  let min = Infinity, max = -Infinity;
  for (let i = 0; i < heights.length; i++) {
    const h = heights[i];
    if (h === null) missing.push(i);
    else { min = Math.min(min, h); max = Math.max(max, h); }
  }
  if (!missing.length) {
    const result = { terrain: source, estimatedMask, missingCount: 0 };
    cache.set(input, result); return result;
  }
  // Work relative to the minimum so large absolute datums cannot overflow averages.
  const values = new Float64Array(heights.length);
  const initialized = new Uint8Array(heights.length);
  const queue = new Int32Array(heights.length);
  let head = 0, tail = 0;
  for (let i = 0; i < heights.length; i++) if (heights[i] !== null) {
    values[i] = heights[i]! - min; initialized[i] = 1; queue[tail++] = i;
  }
  // Seed missing samples from the nearest reachable observed sample, including edges.
  while (head < tail) {
    const i = queue[head++], col = i % width, row = Math.floor(i / width);
    const seed = (next: number) => {
      if (initialized[next]) return;
      values[next] = values[i]; initialized[next] = 1; queue[tail++] = next;
    };
    if (col > 0) seed(i - 1);
    if (col < width - 1) seed(i + 1);
    if (row > 0) seed(i - width);
    if (row < height - 1) seed(i + width);
  }
  const spacing = spacingAxes(source.cellSizeMeters);
  const reference = Math.min(spacing.x, spacing.y);
  const wx = (reference / spacing.x) ** 2, wy = (reference / spacing.y) ** 2;
  const range = max - min, tolerance = Math.max(0.0001, range * 0.000001);
  // Bound CPU work for unusually large masks; the result is an artistic estimate.
  const sweeps = Math.min(400, Math.max(1, Math.floor(4_000_000 / missing.length)));
  for (let sweep = 0; sweep < sweeps; sweep++) {
    let change = 0;
    for (const i of missing) {
      const col = i % width, row = Math.floor(i / width);
      const weight = (col > 0 ? wx : 0) + (col < width - 1 ? wx : 0) + (row > 0 ? wy : 0) + (row < height - 1 ? wy : 0);
      let next = 0;
      if (col > 0) next += values[i - 1] * (wx / weight);
      if (col < width - 1) next += values[i + 1] * (wx / weight);
      if (row > 0) next += values[i - width] * (wy / weight);
      if (row < height - 1) next += values[i + width] * (wy / weight);
      next = Math.max(0, Math.min(range, next));
      change = Math.max(change, Math.abs(next - values[i])); values[i] = next;
    }
    if (change <= tolerance) break;
  }
  const result: VisualInterpolation = {
    terrain: { ...source, heights: heights.map((h, i) => h ?? Math.max(min, Math.min(max, min + values[i]))), validMask: heights.map(() => true),
      dataType: "synthetic", source: `Visualization-only interpolated display of ${source.source}` },
    estimatedMask, missingCount: missing.length,
  };
  cache.set(input, result); return result;
}

export function createVisualFillGeometry(input: TerrainData, options?: Parameters<typeof createTerrainGeometry>[1]): THREE.BufferGeometry {
  const display = interpolateTerrainForDisplay(input);
  const geometry = createTerrainGeometry(display.terrain, options);
  geometry.setAttribute("visualEstimate", new THREE.Float32BufferAttribute(display.estimatedMask.map(Number), 1));
  return geometry;
}
