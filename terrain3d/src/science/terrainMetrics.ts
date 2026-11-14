import type { ValidatedTerrainData } from "../types/terrain";
import { spacingAxes } from "../validation/terrain";

/** Scientific display metrics; all calculations use source elevations in metres. */
export interface TerrainMetrics {
  min: number; max: number; relief: number; mean: number; standardDeviation: number;
  meanSlopeDegrees: number | null; roughnessMeters: number | null; validPercent: number;
  widthMeters: number; heightMeters: number; diagonalReliefRatio: number;
}

/** Roughness is the mean absolute elevation difference across valid 4-neighbour pairs. */
export function calculateTerrainMetrics(terrain: ValidatedTerrainData): TerrainMetrics {
  const values = terrain.heights.filter((value): value is number => value !== null);
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  const min = Math.min(...values), max = Math.max(...values);
  const { x: dx, y: dy } = spacingAxes(terrain.cellSizeMeters);
  let slopeSum = 0, slopeCount = 0, roughnessSum = 0, roughnessCount = 0;
  const sample = (row: number, column: number) => terrain.heights[row * terrain.width + column];
  for (let row = 0; row < terrain.height; row++) for (let column = 0; column < terrain.width; column++) {
    const center = sample(row, column); if (center === null) continue;
    const right = column + 1 < terrain.width ? sample(row, column + 1) : null;
    const down = row + 1 < terrain.height ? sample(row + 1, column) : null;
    if (right !== null) { roughnessSum += Math.abs(right - center); roughnessCount++; }
    if (down !== null) { roughnessSum += Math.abs(down - center); roughnessCount++; }
    const left = column > 0 ? sample(row, column - 1) : null;
    const up = row > 0 ? sample(row - 1, column) : null;
    if (right !== null && left !== null && down !== null && up !== null) {
      const dzdx = (right - left) / (2 * dx), dzdy = (down - up) / (2 * dy);
      slopeSum += Math.atan(Math.hypot(dzdx, dzdy)) * 180 / Math.PI; slopeCount++;
    }
  }
  const widthMeters = (terrain.width - 1) * dx, heightMeters = (terrain.height - 1) * dy;
  return { min, max, relief: max - min, mean, standardDeviation: Math.sqrt(variance),
    meanSlopeDegrees: slopeCount ? slopeSum / slopeCount : null,
    roughnessMeters: roughnessCount ? roughnessSum / roughnessCount : null,
    validPercent: 100 * values.length / terrain.heights.length, widthMeters, heightMeters,
    diagonalReliefRatio: (max - min) / Math.hypot(widthMeters, heightMeters) };
}
