import * as THREE from "three";
import type { TerrainData } from "../types/terrain";
import { spacingAxes, TerrainValidationError, validateTerrainData } from "../validation/terrain";

/** Retains valid samples and emits only triangles whose three samples are valid. */
export function createTerrainGeometry(input: TerrainData, options?: { verticalExaggeration?: number; colorMode?: "elevation" | "neutral"; elevationOffset?: number; colorRange?: { min: number; max: number }; worldSpanMeters?: number }): THREE.BufferGeometry {
  const terrain = validateTerrainData(input);
  const { width, height, heights } = terrain;
  const verticalExaggeration = options?.verticalExaggeration ?? terrain.verticalExaggeration;
  const colorMode = options?.colorMode ?? "elevation";
  const { x: spacingX, y: spacingY } = spacingAxes(terrain.cellSizeMeters);
  const span = Math.max((width - 1) * spacingX, (height - 1) * spacingY);
  const scale = 10 / (options?.worldSpanMeters ?? span);
  let min = Infinity, max = -Infinity;
  for (const h of heights) if (h !== null) { min = Math.min(min, h); max = Math.max(max, h); }
  const elevationOffset = options?.elevationOffset ?? 0;
  const colorMin = options?.colorRange?.min ?? min;
  const colorMax = options?.colorRange?.max ?? max;
  const vertices: number[] = [], colors: number[] = [], uvs: number[] = [], indices: number[] = [];
  const vertexIndex = new Int32Array(heights.length).fill(-1);
  const color = new THREE.Color();
  for (let row = 0; row < height; row++) {
    for (let column = 0; column < width; column++) {
      const index = row * width + column;
      const elevation = heights[index];
      if (elevation === null) continue;
      vertexIndex[index] = vertices.length / 3;
      const y = (elevation - min + elevationOffset) * scale * verticalExaggeration;
      if (!Number.isFinite(Math.fround(y))) throw new TerrainValidationError("elevation range / spacing / verticalExaggeration exceeds GPU float32 range");
      vertices.push((column - (width - 1) / 2) * spacingX * scale, y,
        (row - (height - 1) / 2) * spacingY * scale);
      const t = colorMax === colorMin ? 0.5 : Math.max(0, Math.min(1, (elevation + elevationOffset - colorMin) / (colorMax - colorMin)));
      if (colorMode === "neutral") color.setRGB(0.48 + 0.22 * t, 0.52 + 0.18 * t, 0.58 + 0.12 * t);
      else color.setHSL(0.6 - 0.5 * t, 0.45, 0.34 + t * 0.25);
      colors.push(color.r, color.g, color.b);
      uvs.push(column * spacingX / span, row * spacingY / span);
    }
  }
  function triangle(a: number, b: number, c: number) {
    const va = vertexIndex[a], vb = vertexIndex[b], vc = vertexIndex[c];
    if (va >= 0 && vb >= 0 && vc >= 0) indices.push(va, vb, vc);
  }
  for (let row = 0; row < height - 1; row++) {
    for (let column = 0; column < width - 1; column++) {
      const a = row * width + column, b = a + 1, c = a + width, d = c + 1;
      triangle(a, c, b);
      triangle(b, c, d);
    }
  }
  if (!indices.length) throw new TerrainValidationError("valid samples do not form any terrain triangles");
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}
