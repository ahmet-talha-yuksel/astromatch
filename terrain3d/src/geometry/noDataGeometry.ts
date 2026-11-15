import * as THREE from "three";
import type { TerrainData } from "../types/terrain";
import { spacingAxes, TerrainValidationError, validateTerrainData } from "../validation/terrain";

/** Diagnostic footprint of omitted triangles, on a reference plane, never estimated terrain. */
export function createNoDataGeometry(input: TerrainData, options?: { verticalExaggeration?: number; elevationOffset?: number; worldSpanMeters?: number }): THREE.BufferGeometry | null {
  const terrain = validateTerrainData(input);
  if (!terrain.heights.includes(null)) return null;
  const { width, height, heights } = terrain;
  const spacing = spacingAxes(terrain.cellSizeMeters);
  const span = Math.max((width - 1) * spacing.x, (height - 1) * spacing.y);
  const scale = 10 / (options?.worldSpanMeters ?? span);
  // Below the minimum valid elevation after the renderer's datum translation.
  // This is a labelled reference plane, not an interpolation or a zero-meter sample.
  const y = (options?.elevationOffset ?? 0) * scale * (options?.verticalExaggeration ?? terrain.verticalExaggeration) - 0.005;
  if (!Number.isFinite(Math.fround(y))) throw new TerrainValidationError("NoData reference plane exceeds GPU float32 range");
  const vertices: number[] = [], indices: number[] = [];
  const lookup = new Int32Array(heights.length).fill(-1);
  const vertex = (sample: number) => {
    if (lookup[sample] >= 0) return lookup[sample];
    lookup[sample] = vertices.length / 3;
    const col = sample % width, row = Math.floor(sample / width);
    vertices.push((col - (width - 1) / 2) * spacing.x * scale, y, (row - (height - 1) / 2) * spacing.y * scale);
    return lookup[sample];
  };
  const triangle = (a: number, b: number, c: number) => {
    if (heights[a] !== null && heights[b] !== null && heights[c] !== null) return;
    indices.push(vertex(a), vertex(b), vertex(c));
  };
  for (let row = 0; row < height - 1; row++) for (let col = 0; col < width - 1; col++) {
    const a = row * width + col, b = a + 1, c = a + width;
    triangle(a, c, b); triangle(b, c, c + 1);
  }
  if (!indices.length) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  return geometry;
}
