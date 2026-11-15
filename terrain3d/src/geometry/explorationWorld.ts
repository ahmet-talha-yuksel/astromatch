import * as THREE from "three";
import type { ValidatedTerrainData } from "../types/terrain";
import { surfaceElevation } from "./surfaceNavigation";

/** Decorative context only. Source samples and NoData inside the selected parcel stay intact. */
export function explorationWorld(terrain: ValidatedTerrainData, exaggeration: number, options?: { worldSpanMeters?: number; elevationOffset?: number }) {
  let min = Infinity;
  for (const h of terrain.heights) if (h !== null) min = Math.min(min, h);
  const scale = 10 / (options?.worldSpanMeters ?? Math.max(terrain.horizontalWindowMeters.width, terrain.horizontalWindowMeters.height));
  const offset = (options?.elevationOffset ?? 0) * scale * exaggeration;
  const width = terrain.horizontalWindowMeters.width * scale, depth = terrain.horizontalWindowMeters.height * scale;
  const at = (u: number, v: number): number | null => {
    if (u < -2 || u > 3 || v < -2 || v > 3 || !Number.isFinite(u + v)) return null;
    if (u >= 0 && u <= 1 && v >= 0 && v <= 1) {
      const h = surfaceElevation(terrain, u, v);
      return h === null ? null : (h - min) * scale * exaggeration + offset;
    }
    const cu = THREE.MathUtils.clamp(u, 0, 1), cv = THREE.MathUtils.clamp(v, 0, 1);
    const edge = surfaceElevation(terrain, cu, cv);
    const distance = Math.hypot((u - cu) * width, (v - cv) * depth);
    const blend = THREE.MathUtils.smoothstep(distance, 0, 3);
    const x = (u - 0.5) * width, z = (v - 0.5) * depth;
    const seed = terrain.body === "Mars" ? 4 : terrain.body === "Moon" ? 9 : 1;
    let hills = Math.sin(x * 0.7 + seed + Math.sin(z * 0.4)) * Math.cos(z * 0.55) * 0.6
      + Math.sin(x * 2.2 + seed) * Math.cos(z * 1.9) * 0.15;
    if (terrain.body === "Moon") hills = Math.abs(Math.sin(x * 0.8) * Math.cos(z * 0.7)) * 0.5 + hills * 0.4;
    // A gentle decorative falloff makes the extended horizon read as a planet.
    return THREE.MathUtils.lerp(edge === null ? 0 : (edge - min) * scale * exaggeration,
      hills - (x * x + z * z) / 110, blend) + offset;
  };
  return { at, width, depth, scale };
}

export function createContextGeometry(world: ReturnType<typeof explorationWorld>) {
  const positions: number[] = [], uv: number[] = [], indices: number[] = [];
  const n = 40;
  for (let tz = -2; tz <= 2; tz++) for (let tx = -2; tx <= 2; tx++) {
    if (tx === 0 && tz === 0) continue;
    const base = positions.length / 3;
    for (let z = 0; z <= n; z++) for (let x = 0; x <= n; x++) {
      const u = tx + x / n, v = tz + z / n;
      positions.push((u - 0.5) * world.width, world.at(u, v) ?? 0, (v - 0.5) * world.depth);
      uv.push(u * world.width / 10, v * world.depth / 10);
    }
    for (let z = 0; z < n; z++) for (let x = 0; x < n; x++) {
      const a = base + z * (n + 1) + x, b = a + 1, c = a + n + 1;
      indices.push(a, c, b, b, c, c + 1);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices); geometry.computeVertexNormals();
  return geometry;
}
