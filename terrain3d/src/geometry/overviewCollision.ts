import type { Vector3 } from "three";
import type { explorationWorld } from "./explorationWorld";

/** Sample the rendered 40-cell context triangles, rather than the curved generating function. */
export function renderedWorldHeight(world: ReturnType<typeof explorationWorld>, u: number, v: number): number | null {
  if (u >= 0 && u <= 1 && v >= 0 && v <= 1) return world.at(u, v);
  if (u < -2 || u > 3 || v < -2 || v > 3 || !Number.isFinite(u + v)) return null;
  const tx = Math.min(2, Math.floor(u)), tz = Math.min(2, Math.floor(v));
  const x = (u - tx) * 40, z = (v - tz) * 40;
  const col = Math.min(39, Math.floor(x)), row = Math.min(39, Math.floor(z));
  const fx = x - col, fz = z - row;
  const h = (dx: number, dz: number) => world.at(tx + (col + dx) / 40, tz + (row + dz) / 40) ?? 0;
  return fx + fz <= 1 ? h(0, 0) * (1 - fx - fz) + h(1, 0) * fx + h(0, 1) * fz
    : h(1, 0) * (1 - fz) + h(0, 1) * (1 - fx) + h(1, 1) * (fx + fz - 1);
}

export function keepOverviewAboveGround(position: Vector3, world: ReturnType<typeof explorationWorld>, clearance: number) {
  const floor = renderedWorldHeight(world, position.x / world.width + 0.5, position.z / world.depth + 0.5);
  if (floor !== null) position.y = Math.max(position.y, floor + clearance);
}
