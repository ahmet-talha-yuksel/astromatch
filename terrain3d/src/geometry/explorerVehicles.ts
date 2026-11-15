import type { ValidatedTerrainData } from "../types/terrain";
import { surfaceElevation, type ParcelPosition } from "./surfaceNavigation";

export type ExplorerVehicle = "astronaut" | "rover";
export const VEHICLE_RADIUS = 0.52;
export const LANDER_RADIUS = 0.85;
export const LANDING_FOOTPRINT = 0.46;
export interface SurfaceWorld { width: number; depth: number; at(u: number, v: number): number | null }
/** The entire vehicle footprint needs measured ground, even with visual gap fill. */
export function vehicleGround(terrain: ValidatedTerrainData, world: SurfaceWorld, position: ParcelPosition, radius = VEHICLE_RADIUS) {
  let low = Infinity, high = -Infinity, measured = true;
  for (const [x, z] of [[0, 0], [-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1], [0, 1], [-1, 0], [1, 0]]) {
    const u = position.u + x * radius / world.width, v = position.v + z * radius / world.depth;
    if (surfaceElevation(terrain, u, v) === null) measured = false;
    const ground = world.at(u, v);
    if (ground !== null) { low = Math.min(low, ground); high = Math.max(high, ground); }
  }
  if (measured) {
    // Nine probes alone can miss a small NoData island between the wheels.
    // Conservatively require every source cell under the square footprint.
    const left = Math.floor((position.u - radius / world.width) * (terrain.width - 1));
    const right = Math.min(terrain.width - 2, Math.floor((position.u + radius / world.width) * (terrain.width - 1)));
    const top = Math.floor((position.v - radius / world.depth) * (terrain.height - 1));
    const bottom = Math.min(terrain.height - 2, Math.floor((position.v + radius / world.depth) * (terrain.height - 1)));
    for (let row = top; row <= bottom + 1 && measured; row++) for (let col = left; col <= right + 1; col++) {
      if (terrain.heights[row * terrain.width + col] === null) { measured = false; break; }
    }
  }
  return { measured, height: Number.isFinite(high) ? high : null, spread: Number.isFinite(low) ? high - low : Infinity };
}

export interface LandingSite { u: number; v: number; x: number; y: number; z: number }
export function findRoverSpawn(terrain: ValidatedTerrainData, world: SurfaceWorld, origin: ParcelPosition, sceneScale: number): ParcelPosition | null {
  const radius=1.05*sceneScale;
  if (vehicleGround(terrain,world,origin,radius).measured) return origin;
  let best:ParcelPosition|null=null, distance=Infinity;
  for(let row=0;row<terrain.height-1;row++) for(let col=0;col<terrain.width-1;col++) {
    const u=(col+.5)/(terrain.width-1),v=(row+.5)/(terrain.height-1),next=(u-origin.u)**2+(v-origin.v)**2;
    if(next<distance&&vehicleGround(terrain,world,{u,v},radius).measured) { best={u,v};distance=next; }
  }
  return best;
}
export function findLandingSite(terrain: ValidatedTerrainData, world: SurfaceWorld, origin: ParcelPosition, yaw: number): LandingSite | null {
  const desiredU = origin.u + (0.7 * Math.cos(yaw) - 1.5 * Math.sin(yaw)) / world.width;
  const desiredV = origin.v + (-1.5 * Math.cos(yaw) - 0.7 * Math.sin(yaw)) / world.depth;
  let best: LandingSite | null = null, score = Infinity;
  // Search measured triangle centers and reject incomplete or very steep footprints.
  for (let row = 0; row < terrain.height - 1; row++) for (let col = 0; col < terrain.width - 1; col++) {
    const u = (col + 0.5) / (terrain.width - 1), v = (row + 0.5) / (terrain.height - 1);
    const x = (u - 0.5) * world.width, z = (v - 0.5) * world.depth;
    if (Math.abs(x) > world.width / 2 - LANDER_RADIUS || Math.abs(z) > world.depth / 2 - LANDER_RADIUS) continue;
    if (Math.hypot((u - origin.u) * world.width, (v - origin.v) * world.depth) < 0.9) continue;
    const ground = vehicleGround(terrain, world, { u, v }, 0.52);
    if (!ground.measured || ground.height === null || ground.spread > 0.2) continue;
    const distance = ((u - desiredU) * world.width) ** 2 + ((v - desiredV) * world.depth) ** 2 + ground.spread * 2;
    if (distance < score) { best = { u, v, x, y: ground.height, z }; score = distance; }
  }
  return best;
}
